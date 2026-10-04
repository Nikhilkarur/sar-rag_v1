"""
Document ingestion — PDF -> heading-aware sections -> token-bounded chunks ->
contextualized -> embedded -> stored in the tenant's Chroma collection.

Pipeline (Phase 1 of RAG):
  1. parse_pdf      : PyMuPDF, keep font size (heading detection) + page number
  2. split_sections : break into sections by detected heading
  3. chunk_section  : ~CHUNK_TARGET tokens, ~CHUNK_OVERLAP overlap, sentence-aligned,
                      counted with the encoder's own tokenizer (stay < 512)
  4. contextualize  : prepend "[Context: <doc> - Section: <heading>]" to every chunk
  5. index_document : embed + add to Chroma with metadata

The contextual prefix is deterministic (doc title + section). An optional LLM
doc-summary can be layered in later; not required for retrieval to work.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.services import embeddings
from app.services.chroma_client import get_tenant_collection, replace_tenant_collection

CHUNK_TARGET = 350      # token target for a chunk body (leaves room for context line under 512)
CHUNK_OVERLAP = 60      # token overlap between consecutive chunks
MAX_CHUNK_HARD = 480    # never emit a chunk whose body exceeds this many tokens

# Numbered headings like "4.1 Structuring", "5. Suspicious...", or short ALL-CAPS lines
_NUM_HEADING = re.compile(r"^\s*\d+(\.\d+)*\.?\s+\S")
_SENTENCE_SPLIT = re.compile(r"(?<=[.;:])\s+(?=[A-Z(])")


class PolicyDocumentError(ValueError):
    """The uploaded file can't be turned into a policy index (a client error, not a crash)."""


class UnreadablePdfError(PolicyDocumentError):
    """Corrupt / not a PDF / password-protected."""


class PolicyTooLargeError(PolicyDocumentError):
    """Over the page or extracted-text cap."""


@dataclass
class Section:
    heading: str
    page: int
    text: str = ""


@dataclass
class Chunk:
    document: str          # the contextualized text that gets embedded
    body: str              # raw chunk body (no context line)
    metadata: dict = field(default_factory=dict)


# --- 1. parse ---------------------------------------------------------------
def parse_pdf(path: str, max_pages: Optional[int] = None, max_chars: Optional[int] = None):
    """Return (lines, body_font_size). Each line: {text, size, page, bold}.

    Raises UnreadablePdfError for a corrupt/encrypted file and PolicyTooLargeError when
    the document exceeds max_pages or its text exceeds max_chars (checked as we go, so
    an oversize file is rejected without parsing all of it)."""
    import fitz
    try:
        doc = fitz.open(path, filetype="pdf")
    except Exception as e:  # FileDataError / EmptyFileError: garbage or truncated bytes
        raise UnreadablePdfError("Not a readable PDF file") from e
    try:
        try:  # a cut-off page tree opens fine and only fails here ("Invalid number of pages")
            encrypted, page_count = doc.needs_pass, doc.page_count
        except Exception as e:
            raise UnreadablePdfError("Not a readable PDF file") from e
        if encrypted:
            raise UnreadablePdfError("PDF is password-protected; upload an unencrypted copy")
        if max_pages is not None and page_count > max_pages:
            raise PolicyTooLargeError(
                f"PDF has {page_count} pages; the maximum is {max_pages}")
        lines = []
        size_counts: dict = {}
        total_chars = 0
        for pno in range(page_count):
            try:
                data = doc[pno].get_text("dict")
            except Exception as e:
                raise UnreadablePdfError(f"Not a readable PDF file (page {pno + 1})") from e
            for block in data.get("blocks", []):
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    txt = "".join(s.get("text", "") for s in spans).strip()
                    if not txt:
                        continue
                    total_chars += len(txt)
                    if max_chars is not None and total_chars > max_chars:
                        raise PolicyTooLargeError(
                            f"PDF text exceeds the maximum of {max_chars:,} characters")
                    max_size = max((s.get("size", 0) for s in spans), default=0)
                    bold = any("bold" in (s.get("font", "").lower()) for s in spans)
                    lines.append({"text": txt, "size": round(max_size, 1),
                                  "page": pno + 1, "bold": bold})
                    # tally rounded sizes weighted by text length to find body size
                    key = round(max_size)
                    size_counts[key] = size_counts.get(key, 0) + len(txt)
    finally:
        doc.close()
    body_size = max(size_counts, key=size_counts.get) if size_counts else 10
    return lines, body_size


# --- 2. split into sections -------------------------------------------------
def _is_heading(line: dict, body_size: float) -> bool:
    txt = line["text"]
    if len(txt) > 140:
        return False
    bigger = line["size"] >= body_size + 1.0
    numbered = bool(_NUM_HEADING.match(txt))
    allcaps = txt.isupper() and len(txt) > 3
    # Numbered headings ("4.1 ...") are the reliable signal — accept regardless of length.
    if numbered and (bigger or line["bold"]):
        return True
    # Non-numbered: only treat as a heading if it's SHORT. This keeps real
    # headings but rejects the long document TITLE on the cover page (which is
    # merely big), so it doesn't become a junk "section".
    if bigger and len(txt) <= 60:
        return True
    if allcaps and bigger and len(txt) <= 60:
        return True
    return False


def _running_lines(lines) -> set:
    """Detect running headers/footers GENERICALLY (client-agnostic): a line whose
    text (with any 'Page N' stripped) repeats on most pages is page furniture, not
    content. Avoids hardcoding any one client's footer text."""
    from collections import defaultdict
    pages_of = defaultdict(set)
    total_pages = len({ln["page"] for ln in lines})
    for ln in lines:
        norm = re.sub(r"\bPage\s+\d+\b", "", ln["text"]).strip()
        if norm:
            pages_of[norm].add(ln["page"])
    if total_pages < 3:
        return set()
    return {norm for norm, pgs in pages_of.items() if len(pgs) >= max(2, total_pages / 2)}


def split_sections(lines, body_size) -> List[Section]:
    sections: List[Section] = []
    running = _running_lines(lines)
    current = Section(heading="Preamble", page=lines[0]["page"] if lines else 1)
    for line in lines:
        # skip page numbers and any running header/footer (detected generically)
        norm = re.sub(r"\bPage\s+\d+\b", "", line["text"]).strip()
        if re.match(r"^Page \d+$", line["text"]) or not norm or norm in running:
            continue
        if _is_heading(line, body_size):
            if current.text.strip():
                sections.append(current)
            current = Section(heading=line["text"].strip(), page=line["page"])
        else:
            current.text += (" " if current.text else "") + line["text"]
    if current.text.strip():
        sections.append(current)
    # Drop front matter: if the doc uses numbered headings, real policy content
    # starts at the first numbered one. Anything before it (cover bank name,
    # title, doc-control table, table of contents) is not content. Generic — no
    # client-specific text. Docs without numbered headings keep everything.
    first_numbered = next((i for i, s in enumerate(sections)
                           if _NUM_HEADING.match(s.heading)), None)
    if first_numbered:
        sections = sections[first_numbered:]
    return sections


# --- 3. chunk a section -----------------------------------------------------
def _split_sentences(text: str) -> List[str]:
    parts = _SENTENCE_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]


def _enforce_max_len(sentences: List[str]) -> List[str]:
    """Hard-split any single sentence that exceeds MAX_CHUNK_HARD tokens, so no
    chunk can overflow the encoder's 512-token window (which silently truncates).
    Splits on word boundaries into ~CHUNK_TARGET-token pieces."""
    out: List[str] = []
    for s in sentences:
        if embeddings.count_tokens(s) <= MAX_CHUNK_HARD:
            out.append(s)
            continue
        # Running per-word total instead of re-tokenizing the growing piece after every
        # word (which made one long run-on "sentence" cost minutes). Same split for bge's
        # WordPiece tokenizer, where a text's token count is the sum of its words'.
        cur, cur_tokens = [], 0
        for w in s.split():
            cur.append(w)
            cur_tokens += embeddings.count_tokens(w)
            if cur_tokens >= CHUNK_TARGET:
                out.append(" ".join(cur))
                cur, cur_tokens = [], 0
        if cur:
            out.append(" ".join(cur))
    return out


def chunk_section(section: Section) -> List[str]:
    sentences = _enforce_max_len(_split_sentences(section.text))
    chunks: List[str] = []
    cur: List[str] = []
    cur_tokens = 0
    for sent in sentences:
        st = embeddings.count_tokens(sent)
        if cur and cur_tokens + st > CHUNK_TARGET:
            chunks.append(" ".join(cur))
            # build overlap tail from the end of the just-emitted chunk
            tail: List[str] = []
            tail_tokens = 0
            for s in reversed(cur):
                t = embeddings.count_tokens(s)
                if tail_tokens + t > CHUNK_OVERLAP:
                    break
                tail.insert(0, s)
                tail_tokens += t
            cur = tail[:]
            cur_tokens = tail_tokens
        cur.append(sent)
        cur_tokens += st
    if cur:
        chunks.append(" ".join(cur))
    return chunks


# --- 4 + 5. build + index ---------------------------------------------------
def build_chunks(path: str, doc_title: str, filename: str, doc_id: str,
                 max_pages: Optional[int] = None, max_chars: Optional[int] = None) -> List[Chunk]:
    lines, body_size = parse_pdf(path, max_pages=max_pages, max_chars=max_chars)
    sections = split_sections(lines, body_size)
    out: List[Chunk] = []
    idx = 0
    for sec in sections:
        for body in chunk_section(sec):
            context_line = f"[Context: {doc_title} - Section: \"{sec.heading}\"]"
            document = f"{context_line}\n{body}"
            out.append(Chunk(
                document=document,
                body=body,
                metadata={
                    "doc_id": doc_id,
                    "filename": filename,
                    "section_heading": sec.heading,
                    "chunk_index": idx,
                    "page_number": sec.page,
                },
            ))
            idx += 1
    return out


def _records(chunks: List[Chunk]):
    docs = [c.document for c in chunks]
    metas = [c.metadata for c in chunks]
    ids = [f"{c.metadata['doc_id']}_{c.metadata['chunk_index']}" for c in chunks]
    return docs, metas, ids


def index_document(tenant_id: str, chunks: List[Chunk]) -> int:
    if not chunks:
        return 0
    collection = get_tenant_collection(tenant_id)
    docs, metas, ids = _records(chunks)
    vectors = embeddings.embed_documents(docs)
    collection.add(documents=docs, embeddings=vectors, metadatas=metas, ids=ids)
    return len(chunks)


def replace_index(tenant_id: str, chunks: List[Chunk]) -> int:
    """Make `chunks` the tenant's entire index. Everything that can fail (embedding,
    writing the vectors) happens before the live collection is touched, so on error the
    previous index keeps serving."""
    if not chunks:
        raise ValueError("refusing to replace a tenant index with no chunks")
    docs, metas, ids = _records(chunks)
    vectors = embeddings.embed_documents(docs)
    return replace_tenant_collection(tenant_id, ids=ids, documents=docs,
                                     embeddings=vectors, metadatas=metas)
