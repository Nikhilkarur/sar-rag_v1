"""
Policy upload (/api/v1/documents): runs off the event loop, is capped, and replaces the
previous policy + index only once the new file has produced chunks — a corrupt, blank,
encrypted or oversize PDF (or a failure while embedding) leaves the old ones serving.

DB-free: the auth/DB dependencies are overridden, storage and Chroma point at temp dirs,
and the embedding model is replaced by a deterministic stub.
"""
import asyncio
import hashlib
import inspect
import os
import threading
import uuid
from types import SimpleNamespace

import pytest

fitz = pytest.importorskip("fitz")
pytest.importorskip("chromadb")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import get_db  # noqa: E402
from app.routers import documents  # noqa: E402
from app.services import chroma_client, client_storage, embeddings  # noqa: E402
from app.services import document_ingestion_service as dis  # noqa: E402
from app.utils.deps import get_compliance_user  # noqa: E402

UPLOAD = "/api/v1/documents/upload"
INFO = "/api/v1/documents/"


def _fake_embed(texts):
    out = []
    for t in texts:
        h = hashlib.sha256(t.encode()).digest()
        out.append([b / 255.0 + 0.01 for b in h[:8]])
    return out


def _policy_pdf(pages: int = 6) -> bytes:
    doc = fitz.open()
    for i in range(1, pages + 1):
        page = doc.new_page()
        page.insert_text((72, 72), f"{i}. Section {i} controls", fontsize=16)
        y = 110
        for j in range(10):
            page.insert_text((72, y), f"Rule {i}-{j}: customers are screened against "
                                      f"sanctions lists before onboarding.", fontsize=10)
            y += 16
    return doc.tobytes()


def _blank_pdf() -> bytes:
    doc = fitz.open()
    doc.new_page()
    return doc.tobytes()


def _encrypted_pdf() -> bytes:
    doc = fitz.open(stream=_policy_pdf(2), filetype="pdf")
    return doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="u", owner_pw="o")


def _truncated_page_tree_pdf() -> bytes:
    # Catalog + page tree survive, the page objects it points to are cut off: MuPDF
    # opens this, then page_count raises a bare RuntimeError ("Invalid number of pages")
    data = _policy_pdf()
    return data[:data.index(b"4 0 obj")]


class _NoTenantRowSession:
    """Stands in for the DB session: no Tenant row, so client id = tenant UUID."""
    def query(self, *a, **k):
        return self

    def filter(self, *a, **k):
        return self

    def first(self):
        return None

    def close(self):
        pass


@pytest.fixture(scope="module")
def chroma_dir(tmp_path_factory):
    # One Chroma store for the module (each test uses its own tenant UUID)
    d = str(tmp_path_factory.mktemp("chroma"))
    mp = pytest.MonkeyPatch()
    mp.setattr(chroma_client, "_PERSIST_DIR", d)
    chroma_client.get_chroma_client.cache_clear()
    yield d
    mp.undo()
    chroma_client.get_chroma_client.cache_clear()


@pytest.fixture
def env(tmp_path, monkeypatch, chroma_dir):
    monkeypatch.setattr(client_storage, "CLIENTS_ROOT", str(tmp_path / "clients"))
    monkeypatch.setattr(embeddings, "count_tokens", lambda t: len(t.split()))
    monkeypatch.setattr(embeddings, "embed_documents", _fake_embed)
    user = SimpleNamespace(tenant_id=uuid.uuid4())
    app = FastAPI()
    app.include_router(documents.router)
    app.dependency_overrides[get_db] = lambda: _NoTenantRowSession()
    app.dependency_overrides[get_compliance_user] = lambda: user
    tid = str(user.tenant_id)
    return SimpleNamespace(app=app, client=TestClient(app, raise_server_exceptions=False),
                           tid=tid, tmp=str(tmp_path),
                           policy=os.path.join(str(tmp_path), "clients", tid, "policy.pdf"))


def _upload(env, data: bytes, name: str = "policy.pdf"):
    return env.client.post(UPLOAD, files={"file": (name, data, "application/pdf")})


def _state(env):
    """(chunks in the tenant's live collection, stored policy bytes, stray files)."""
    count = chroma_client.get_tenant_collection(env.tid).count()
    stored = open(env.policy, "rb").read() if os.path.isfile(env.policy) else None
    d = os.path.dirname(env.policy)
    stray = sorted(f for f in os.listdir(d) if f != "policy.pdf") if os.path.isdir(d) else []
    return count, stored, stray


def test_upload_handler_is_not_a_coroutine():
    # An `async def` handler runs the CPU-bound parse/embed on the event loop
    assert not inspect.iscoroutinefunction(documents.upload_policy)


def test_good_upload_indexes_and_hides_server_paths(env):
    good = _policy_pdf()
    r = _upload(env, good, name="Our AML Policy.pdf")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chunks_indexed"] > 0
    assert body["stored_filename"] == "policy.pdf"
    assert body["original_filename"] == "Our AML Policy.pdf"
    assert "stored_path" not in body and env.tmp not in r.text

    info = env.client.get(INFO)
    assert info.status_code == 200
    data = info.json()
    assert data["policy_present"] is True
    assert data["policy_filename"] == "policy.pdf"
    assert data["chunks_indexed"] == body["chunks_indexed"]
    assert "policy_path" not in data and env.tmp not in info.text

    assert _state(env) == (body["chunks_indexed"], good, [])


@pytest.mark.parametrize("payload, status, needle", [
    (os.urandom(2048), 422, "readable"),                  # random bytes named .pdf
    (b"", 422, "readable"),                               # empty file
    (b"%PDF-1.4\n" + os.urandom(2048), 422, "readable"),  # PDF header, garbage body
    (_truncated_page_tree_pdf(), 422, "readable"),
    (_encrypted_pdf(), 422, "password"),
    (_blank_pdf(), 422, "no extractable text"),
], ids=["random-bytes", "empty", "pdf-header-garbage", "truncated-page-tree", "encrypted",
        "blank"])
def test_bad_upload_keeps_previous_policy_and_index(env, payload, status, needle):
    good = _policy_pdf()
    first = _upload(env, good)
    assert first.status_code == 200
    before = _state(env)
    assert before[0] > 0

    r = _upload(env, payload, name="fake.pdf")
    assert r.status_code == status, r.text
    assert needle in r.json()["detail"]
    assert _state(env) == before          # same chunks, same file, no temp files left

    info = env.client.get(INFO).json()
    assert info["policy_present"] is True and info["chunks_indexed"] == before[0]


def test_bad_first_upload_stores_nothing(env):
    r = _upload(env, _blank_pdf())
    assert r.status_code == 422
    assert _state(env) == (0, None, [])
    assert env.client.get(INFO).json()["policy_present"] is False


def test_every_truncation_is_a_client_error(tmp_path):
    """Whatever byte a policy is cut off at, parsing either works or raises
    UnreadablePdfError (-> 422); a raw MuPDF/RuntimeError would escape as a 500."""
    data = _policy_pdf()
    path = str(tmp_path / "cut.pdf")
    unreadable = 0
    # every byte through the header/catalog/page tree/first pages, then a sample (MuPDF
    # tries to repair each prefix, so sweeping all ~17 KB byte by byte takes over a minute)
    for n in [*range(1024), *range(1024, len(data), 61)]:
        with open(path, "wb") as f:
            f.write(data[:n])
        try:
            dis.parse_pdf(path, max_pages=500, max_chars=10 ** 6)
        except dis.UnreadablePdfError:
            unreadable += 1
    assert unreadable > 0


def test_page_cap(env, monkeypatch):
    good = _policy_pdf(2)
    assert _upload(env, good).status_code == 200
    before = _state(env)
    monkeypatch.setattr(settings, "MAX_POLICY_PAGES", 3)
    r = _upload(env, _policy_pdf(6))
    assert r.status_code == 413
    assert "6 pages" in r.json()["detail"]
    assert _state(env) == before


def test_text_cap(env, monkeypatch):
    good = _policy_pdf(2)
    assert _upload(env, good).status_code == 200
    before = _state(env)
    monkeypatch.setattr(settings, "MAX_POLICY_TEXT_CHARS", 500)
    r = _upload(env, _policy_pdf(6))
    assert r.status_code == 413
    assert "characters" in r.json()["detail"]
    assert _state(env) == before


def test_byte_cap(env, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_FILE_SIZE_MB", 0)
    r = _upload(env, _policy_pdf(1))
    assert r.status_code == 413
    assert _state(env) == (0, None, [])


def test_embedding_failure_keeps_previous_index(env, monkeypatch):
    good = _policy_pdf()
    assert _upload(env, good).status_code == 200
    before = _state(env)

    def boom(texts):
        raise RuntimeError("embedding backend down")
    monkeypatch.setattr(embeddings, "embed_documents", boom)
    r = _upload(env, _policy_pdf(3))
    assert r.status_code == 500
    assert _state(env) == before


def test_vector_store_write_failure_keeps_previous_index(env, monkeypatch):
    good = _policy_pdf()
    assert _upload(env, good).status_code == 200
    before = _state(env)

    def ragged(texts):
        # inconsistent dimensions -> Chroma rejects the staging write
        return [[0.1] * (8 if i % 2 else 4) for i, _ in enumerate(texts)]
    monkeypatch.setattr(embeddings, "embed_documents", ragged)
    r = _upload(env, _policy_pdf(3))
    assert r.status_code == 500
    assert _state(env) == before
    names = [getattr(c, "name", c) for c in chroma_client.get_chroma_client().list_collections()]
    assert chroma_client.collection_name(env.tid) + "_staging" not in names


def test_reupload_replaces_index(env):
    assert _upload(env, _policy_pdf(6)).status_code == 200
    six = _state(env)[0]
    r = _upload(env, _policy_pdf(2))
    assert r.status_code == 200
    assert 0 < r.json()["chunks_indexed"] < six
    assert _state(env)[0] == r.json()["chunks_indexed"]
    hits = chroma_client.get_tenant_collection(env.tid).get()["documents"]
    assert not any("Section 6" in h for h in hits)


def test_concurrent_upload_for_same_tenant_is_rejected(env):
    lock = documents._tenant_lock(env.tid)
    assert lock.acquire(blocking=False)
    try:
        r = _upload(env, _policy_pdf(1))
        assert r.status_code == 409
        assert env.client.delete(INFO).status_code == 409
    finally:
        lock.release()
    assert _state(env) == (0, None, [])


def test_upload_does_not_block_event_loop(env, monkeypatch):
    """While one upload is parsing/embedding, other requests on the same loop are served."""
    entered, release = threading.Event(), threading.Event()
    real_build = dis.build_chunks

    def slow_build(*a, **k):
        entered.set()
        release.wait(10)          # stands in for minutes of parse/tokenize/embed CPU work
        return real_build(*a, **k)
    monkeypatch.setattr(dis, "build_chunks", slow_build)

    @env.app.get("/ping")
    async def ping():
        return {"ok": True}

    async def scenario():
        transport = httpx.ASGITransport(app=env.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            upload = asyncio.create_task(ac.post(
                UPLOAD, files={"file": ("policy.pdf", _policy_pdf(2), "application/pdf")}))
            try:
                for _ in range(500):
                    if entered.is_set():
                        break
                    await asyncio.sleep(0.01)
                assert entered.is_set()
                ping_resp = await asyncio.wait_for(ac.get("/ping"), timeout=5)
                assert ping_resp.status_code == 200
                assert not upload.done()      # answered while the upload was still working
            finally:
                release.set()
            resp = await upload
            assert resp.status_code == 200, resp.text

    asyncio.run(scenario())


def test_replace_survives_reader_recreating_live_collection(chroma_dir):
    """A retrieval's get_or_create between the swap's delete and rename must not wedge it."""
    tid = str(uuid.uuid4())
    live = chroma_client.collection_name(tid)
    real = chroma_client.get_chroma_client()
    chroma_client.get_tenant_collection(tid).add(ids=["old"], documents=["old"],
                                                 embeddings=[[0.5] * 8])

    class Racy:
        raced = False

        def __getattr__(self, name):
            return getattr(real, name)

        def delete_collection(self, name):
            real.delete_collection(name)
            if name == live and not Racy.raced:
                Racy.raced = True
                real.get_or_create_collection(name=live, metadata={"hnsw:space": "cosine"})

    mp = pytest.MonkeyPatch()
    mp.setattr(chroma_client, "get_chroma_client", lambda: Racy())
    try:
        n = chroma_client.replace_tenant_collection(
            tid, ids=["a", "b"], documents=["new a", "new b"],
            embeddings=_fake_embed(["new a", "new b"]), metadatas=[{"k": 1}, {"k": 2}])
    finally:
        mp.undo()
    assert Racy.raced and n == 2
    col = chroma_client.get_tenant_collection(tid)
    assert sorted(col.get()["ids"]) == ["a", "b"]
    assert col.metadata.get("hnsw:space") == "cosine"


def test_run_on_sentence_is_hard_split_without_retokenizing(monkeypatch):
    """A punctuation-free "sentence" far over the encoder window is split into
    ~CHUNK_TARGET pieces, tokenizing word by word (not the growing piece each time)."""
    seen = []

    def count(text):
        seen.append(len(text))
        return len(text.split())
    monkeypatch.setattr(embeddings, "count_tokens", count)
    words = [f"w{i}" for i in range(2000)]
    pieces = dis._enforce_max_len([" ".join(words)])
    assert [len(p.split()) for p in pieces] == [dis.CHUNK_TARGET] * 5 + [250]
    assert " ".join(pieces).split() == words
    assert sorted(seen)[-2] <= len("w1999")   # only the one up-front whole-sentence count is long
