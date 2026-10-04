"""
Render an approved SAR to a human-readable PDF (the bank-facing report).

The PDF carries REHYDRATED (real) PII — it is the actual FIU filing — so we deliberately do NOT
persist it to Aegis's disk. It is rendered in memory: the bytes are base64'd into the approval
webhook (the bank keeps its own copy) and re-rendered on demand for the officer's own download.
Cells are wrapped in Paragraph so long text wraps instead of clipping.

Customer data is not always Latin script. Helvetica (a PDF base-14 font) only covers WinAnsi,
so Devanagari/Arabic names printed as black boxes. When the Noto TTFs are installed (the Docker
image ships them in /usr/share/fonts/truetype/noto) they are embedded and the font is picked per
script run; Devanagari is shaped (harfbuzz), Arabic is reshaped + bidi-reordered with mirrored
brackets. Missing fonts fall back to Helvetica.
"""
import logging
import os
import re
import threading
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from itertools import groupby
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable)
from reportlab.lib import colors

try:  # reportlab draws codepoints as-is in logical order, so Arabic must be joined
    import arabic_reshaper  # (reshaped) and reordered right-to-left (bidi) before rendering.
    from bidi import get_display as _bidi_display
except ImportError:  # pragma: no cover - optional; Arabic then renders unjoined
    arabic_reshaper = None
    _bidi_display = None

try:  # reportlab 4.1 draws one cmap glyph per codepoint: no Devanagari conjuncts/reph and the
    import uharfbuzz  # pre-base vowel sign i after its consonant. harfbuzz does the shaping.
except ImportError:  # pragma: no cover - optional; see _reorder_i_matra
    uharfbuzz = None

logger = logging.getLogger(__name__)

# SAR_PDF_FONT_DIR lets a deployment (or a test) point at another font directory.
_FONT_DIRS = [d for d in (os.environ.get("SAR_PDF_FONT_DIR"), "/usr/share/fonts/truetype/noto") if d]
# script -> (regular, bold) TTF file names
_FONT_FILES = {
    "latin": ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf"),
    "deva": ("NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari-Bold.ttf"),
    "arab": ("NotoSansArabic-Regular.ttf", "NotoSansArabic-Bold.ttf"),
}
_FALLBACK_FONTS = ("Helvetica", "Helvetica-Bold")


@lru_cache(maxsize=1)
def _fonts() -> Dict[str, Tuple[str, str]]:
    """Register the Noto TTFs once. Returns script -> (regular, bold) font names for the
    scripts whose fonts were found. Never raises: a missing/broken font only loses coverage."""
    out: Dict[str, Tuple[str, str]] = {}
    for script, files in _FONT_FILES.items():
        names = []
        for fname in files:
            path = next((os.path.join(d, fname) for d in _FONT_DIRS
                         if os.path.isfile(os.path.join(d, fname))), None)
            if not path:
                continue
            name = os.path.splitext(fname)[0]
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                names.append(name)
            except Exception:
                logger.exception("SAR PDF: could not register font %s", path)
        if names:
            out[script] = (names[0], names[-1])  # bold falls back to regular if absent
        else:
            logger.warning("SAR PDF: no %s font found in %s; falling back to Helvetica",
                           script, _FONT_DIRS)
    return out


def _script_of(ch: str) -> Optional[str]:
    o = ord(ch)
    if 0x0900 <= o <= 0x097F or 0xA8E0 <= o <= 0xA8FF:
        return "deva"
    if (0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F or 0x08A0 <= o <= 0x08FF
            or 0xFB50 <= o <= 0xFDFF or 0xFE70 <= o <= 0xFEFF):  # incl. presentation forms
        return "arab"
    return None


# Paired brackets (BidiBrackets.txt) that stand in, one per pair, for the text's own brackets
# while it is reordered; see _bidi_mirrored.
_BRACKETS = {"(": ")", "[": "]", "{": "}"}
_OPENER_OF = {c: o for o, c in _BRACKETS.items()}
_STAND_INS = ["⁅⁆", "⁽⁾", "₍₎", "⌈⌉", "⌊⌋", "❨❩", "❪❫", "❬❭", "❮❯", "❰❱", "❲❳", "❴❵",
              "⟅⟆", "⟦⟧", "⟪⟫", "⟬⟭", "⟮⟯", "⦃⦄", "⦅⦆", "⦇⦈", "⦉⦊", "⦋⦌"]
_STAND_IN_CHARS = set("".join(_STAND_INS))


def _bidi_mirrored(text: str) -> str:
    """bidi display order (base LTR) with bracket pairs mirrored when they sit in a
    right-to-left run. python-bidi 0.6 resolves and reorders bracket pairs but does not mirror
    their glyphs (rule L4), so '(ش.م.ع)' printed as ')ع.م.ش('. Each pair is swapped for a
    unique stand-in pair (same pairing, same resolution); a pair whose closer then comes first
    on the display line is right-to-left and gets its glyphs swapped back mirrored."""
    pairs, stack = [], []
    for i, ch in enumerate(text):  # BD16 bracket pairing
        if ch in _BRACKETS:
            stack.append(i)
        elif ch in _OPENER_OF:
            for depth in range(len(stack) - 1, -1, -1):
                if text[stack[depth]] == _OPENER_OF[ch]:
                    pairs.append((stack[depth], i))
                    del stack[depth:]
                    break
    if not pairs or len(pairs) > len(_STAND_INS) or _STAND_IN_CHARS.intersection(text):
        return _bidi_display(text, base_dir="L")
    chars = list(text)
    for (o, c), (so, sc) in zip(pairs, _STAND_INS):
        chars[o], chars[c] = so, sc
    display = list(_bidi_display("".join(chars), base_dir="L"))
    for (o, c), (so, sc) in zip(pairs, _STAND_INS):
        try:
            po, pc = display.index(so), display.index(sc)
        except ValueError:  # pragma: no cover - reordering keeps every character
            return _bidi_display(text, base_dir="L")
        left, right = (po, pc) if po < pc else (pc, po)
        display[left], display[right] = text[o], text[c]
    return "".join(display)


def _shape_arabic(text: str) -> str:
    """Join Arabic letters and reorder the line for display (base direction LTR)."""
    if arabic_reshaper is None or _bidi_display is None:
        return text
    try:
        return _bidi_mirrored(arabic_reshaper.reshape(text))
    except Exception:
        logger.exception("SAR PDF: Arabic shaping failed; rendering unshaped")
        return text


# consonant cluster ((consonant [nukta] virama)* consonant [nukta]) followed by vowel sign i
_DEVA_CONSONANT = "[\u0915-\u0939\u0958-\u095F\u0978-\u097F]\u093C?"
_DEVA_I_MATRA = re.compile(f"((?:{_DEVA_CONSONANT}\u094D)*{_DEVA_CONSONANT})\u093F")


def _reorder_i_matra(text: str) -> str:
    """Fallback without harfbuzz: draw the vowel sign i (ि) before its consonant cluster, where
    it is written. Unshaped, 'किशोर' otherwise reads 'कशिोर' (conjuncts still show a virama)."""
    return _DEVA_I_MATRA.sub("\u093F\\1", text)


# Shaped glyphs with no cmap codepoint (conjuncts, half forms, reph, matra variants) are drawn
# through a private-use codepoint U+E000+glyph id registered on the reportlab font face. It is
# a function of the glyph id only, so a re-render is byte-identical to the delivered PDF. (Text
# copied out of the PDF yields those private-use codepoints for such glyphs.)
_PUA_FIRST, _PUA_LAST = 0xE000, 0xF8FF
_hb_faces: Dict[str, Tuple[Any, Dict[int, int]]] = {}
_hb_lock = threading.Lock()


def _hb_face(font_name: str) -> Tuple[Any, Dict[int, int]]:
    """(harfbuzz face, glyph id -> lowest codepoint) for a registered TTF, built once."""
    with _hb_lock:
        if font_name not in _hb_faces:
            face = pdfmetrics.getFont(font_name).face
            with open(face.filename, "rb") as fh:
                hb_face = uharfbuzz.Face(uharfbuzz.Blob(fh.read()))
            codepoint_of: Dict[int, int] = {}
            for code, gid in sorted(face.charToGlyph.items(), reverse=True):
                codepoint_of[gid] = code
            _hb_faces[font_name] = (hb_face, codepoint_of)
        return _hb_faces[font_name]


def _shape_devanagari(text: str, font_name: str) -> str:
    """Shape a Devanagari run with harfbuzz and return it as codepoints that reportlab draws
    as the shaped glyphs, in display order. Falls back to _reorder_i_matra."""
    if uharfbuzz is None:
        return _reorder_i_matra(text)
    try:
        hb_face, codepoint_of = _hb_face(font_name)
        buf = uharfbuzz.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        buf.flags = uharfbuzz.BufferFlags.REMOVE_DEFAULT_IGNORABLES  # ZWJ/ZWNJ: no glyph
        uharfbuzz.shape(uharfbuzz.Font(hb_face), buf, {})
        face = pdfmetrics.getFont(font_name).face
        out = []
        for info in buf.glyph_infos:
            gid = info.codepoint
            code = codepoint_of.get(gid)
            if code is None:
                code = _PUA_FIRST + gid
                if code > _PUA_LAST or face.charToGlyph.get(code, gid) != gid:
                    return _reorder_i_matra(text)
                face.charToGlyph[code] = gid
                face.charWidths[code] = face.hmetrics[gid][0] * 1000.0 / face.unitsPerEm
            out.append(chr(code))
        return "".join(out)
    except Exception:
        logger.exception("SAR PDF: Devanagari shaping failed; rendering unshaped")
        return _reorder_i_matra(text)


def _esc(value: Any) -> str:
    """XML-escape dynamic (LLM/user-derived) text before it enters a reportlab Paragraph.
    Paragraph parses its content as markup, so a bare '&', '<' or '>' in an LLM narrative
    (e.g. 'PMLA & Rules', 'amount < 10,00,000') would raise and abort the PDF render."""
    return _xml_escape("" if value is None else str(value))


def _rich(value: Any, bold: bool = False) -> str:
    """_esc() plus per-script fonts: each Devanagari/Arabic run is wrapped in its Noto font
    (other text keeps the paragraph's font). Spaces/ZWJ/ZWNJ stay in the run they sit in."""
    text = "" if value is None else str(value)
    fonts = _fonts()
    if any(_script_of(c) == "arab" for c in text):
        text = _shape_arabic(text)
    tagged, current = [], None
    for ch in text:
        script = _script_of(ch)
        if script is None and (ch.isspace() or ch in "\u200c\u200d"):
            script = current
        tagged.append((script, ch))
        current = script
    out = []
    for script, run in groupby(tagged, key=lambda t: t[0]):
        chunk = "".join(ch for _, ch in run)
        if script in fonts:
            font = fonts[script][1 if bold else 0]
            if script == "deva":
                chunk = _shape_devanagari(chunk, font)
            out.append(f'<font name="{font}">{_esc(chunk)}</font>')
        else:
            out.append(_esc(chunk))
    return "".join(out)


def _normalize_indicators(structured: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for ind in (structured or {}).get("key_indicators", []) or []:
        if isinstance(ind, dict):
            out.append({"indicator": str(ind.get("indicator", "")),
                        "regulation": str(ind.get("regulation", "")),
                        "description": str(ind.get("description", ""))})
        else:
            out.append({"indicator": str(ind), "regulation": "", "description": ""})
    return out


def _pdf_date_formatter(approved_at: Optional[str]):
    """PDF CreationDate/ModDate = the approval time, not the render time, so the officer's
    re-rendered download is byte-identical to the copy delivered to the bank."""
    try:
        dt = datetime.fromisoformat(str(approved_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    stamp = dt.astimezone(timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")
    return lambda *_: stamp


def render_sar_pdf(sar_id: str, alert, draft, goaml: Dict[str, Any],
                   officer_name: Optional[str], approved_at: Optional[str]) -> bytes:
    """Render the SAR to PDF and return the bytes. Never touches disk (real-PII filing).
    Status and test marking come from the alert; "Approved By" is printed only for an
    APPROVED alert. Deterministic for the same inputs (no render-time timestamp)."""
    buffer = BytesIO()

    base, base_bold = _fonts().get("latin", _FALLBACK_FONTS)
    s = getSampleStyleSheet()
    H = ParagraphStyle("H", parent=s["Heading2"], fontName=base_bold, fontSize=12,
                       textColor=colors.HexColor("#0B2E4F"), spaceBefore=12, spaceAfter=6)
    normal = ParagraphStyle("N", parent=s["Normal"], fontName=base)
    body = ParagraphStyle("B", parent=s["BodyText"], fontName=base, fontSize=10, leading=15,
                          alignment=TA_JUSTIFY)
    cell = ParagraphStyle("C", parent=s["BodyText"], fontName=base, fontSize=8.5, leading=11)
    cellh = ParagraphStyle("CH", parent=cell, fontName=base_bold, textColor=colors.white)
    meta_v = ParagraphStyle("MV", parent=cell, fontSize=9.5, leading=12)
    tx_v = ParagraphStyle("TV", parent=cell, fontSize=9, leading=12)

    structured = draft.draft_structured if isinstance(draft.draft_structured, dict) else {}
    narrative = draft.approved_text or draft.rehydrated_text or draft.draft_text or ""
    report = goaml.get("report", {})
    tx = report.get("transaction", {})
    status = str(alert.status or "")
    approved = status == "APPROVED"
    is_test = bool(getattr(alert, "is_synthetic", False))

    story = [
        Paragraph("SUSPICIOUS TRANSACTION REPORT (STR)",
                  ParagraphStyle("T", parent=s["Title"], fontName=base_bold, fontSize=18,
                                 textColor=colors.HexColor("#0B2E4F"))),
        Paragraph(f"{_rich(report.get('rentity_name') or 'Aegis tenant')} &nbsp;|&nbsp; goAML filing", normal),
    ]
    if is_test:
        story.append(Paragraph("TEST ALERT - synthetic data from the portal simulator. Not a real filing.",
                               ParagraphStyle("TEST", parent=normal, fontName=base_bold,
                                              textColor=colors.HexColor("#B42318"), spaceBefore=4)))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#14507F"),
                            spaceBefore=6, spaceAfter=8))

    meta_rows = [
        ["SAR ID", str(sar_id)], ["Report Code", "STR (goAML)"],
        ["Reporting Entity", str(report.get("rentity_id"))],
        ["Transaction ID", str(tx.get("transactionnumber"))],
        ["Risk Score", str(alert.risk_score)],
        ["Status", status + (" (TEST)" if is_test else "")],
    ]
    if approved:
        meta_rows.append(["Approved By", f"{officer_name} - {approved_at}"])
    meta = Table([[label, Paragraph(_rich(value), meta_v)] for label, value in meta_rows],
                 colWidths=[42 * mm, 128 * mm])
    meta.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), base, 9.5), ("FONT", (0, 0), (0, -1), base_bold, 9.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#F4F7FA"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta)

    story.append(Paragraph("1. Ground of Suspicion (Narrative)", H))
    for para in narrative.split("\n"):
        if para.strip():
            story.append(Paragraph(_rich(para.strip()), body)); story.append(Spacer(1, 4))

    indicators = _normalize_indicators(structured)
    if indicators:
        story.append(Paragraph("2. Suspicion Indicators &amp; Regulatory Basis", H))
        # cells wrapped in Paragraph -> text wraps instead of clipping
        rows = [[Paragraph("Indicator", cellh), Paragraph("Regulation", cellh), Paragraph("Description", cellh)]]
        for ind in indicators:
            rows.append([Paragraph(_rich(ind["indicator"]), cell), Paragraph(_rich(ind["regulation"]), cell),
                         Paragraph(_rich(ind["description"]), cell)])
        t = Table(rows, colWidths=[42 * mm, 38 * mm, 90 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B2E4F")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

    action = structured.get("recommended_action") if isinstance(structured, dict) else None
    if action:
        story.append(Paragraph("3. Recommended Action", H))
        story.append(Paragraph(_rich(action), body))

    story.append(Paragraph("4. Transaction (goAML bi-party)", H))
    frm = tx.get("t_from_my_client", {}); to = tx.get("t_to", {})
    tx_rows = [
        ["Amount (local)", f"{report.get('currency_code_local','INR')} {tx.get('value_local')}"],
        ["Mode (transmode_code)", str(tx.get("transmode_code"))],
        ["From (my client)", f"{(frm.get('from_person') or {}).get('name')} / {(frm.get('from_account') or {}).get('account')}"],
        ["To (receiver)", f"{(to.get('to_person') or {}).get('name')} @ {(to.get('to_account') or {}).get('institution_name')}"],
        ["Indicators", ", ".join(report.get("report_indicators", []))],
    ]
    # Values wrapped in Paragraph: a plain-string cell is clipped at the column edge (the
    # Indicators row was cut off mid-code) and cannot switch fonts per script.
    pt = Table([[label, Paragraph(_rich(value), tx_v)] for label, value in tx_rows],
               colWidths=[42 * mm, 128 * mm])
    pt.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), base, 9), ("FONT", (0, 0), (0, -1), base_bold, 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(pt)

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D6DEE6")))
    # Aegis delivers the approved STR to the reporting entity, which submits it to FIU-IND —
    # the footer must not claim a filing Aegis did not make.
    if approved:
        footer = (f"Approved by {_rich(officer_name)} on {_esc(approved_at)}. goAML STR prepared "
                  f"for submission to FIU-IND by the reporting entity.")
    else:
        footer = f"DRAFT - status {_esc(status)}. Not approved; not for filing."
    story.append(Paragraph(footer, ParagraphStyle("F", parent=normal, fontSize=8, textColor=colors.grey)))

    # invariant=1 drops reportlab's render-time timestamp and random document ID.
    date_formatter = _pdf_date_formatter(approved_at) if approved else None

    def _stamp(canv, _doc):
        if date_formatter:
            canv.setDateFormatter(date_formatter)

    SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=16 * mm, bottomMargin=16 * mm, invariant=1).build(
        story, onFirstPage=_stamp, onLaterPages=_stamp)
    return buffer.getvalue()
