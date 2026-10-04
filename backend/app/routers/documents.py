"""
Document (AML policy) management — P3.

A tenant uploads their AML policy PDF here. We:
  1. store the RAW PDF at backend/storage/clients/<client_id>/policy.pdf
     (the per-client folder that also holds the logged alerts + generated SARs),
  2. chunk + embed it into the tenant's Chroma collection (tenant_{uuid}_docs),
     which is what live alerts retrieve from.

  POST   /api/v1/documents/upload   (multipart 'file')  -> store + index
  GET    /api/v1/documents/                              -> info on this client's policy
  DELETE /api/v1/documents/                              -> remove policy file + chunks

A re-upload replaces the policy only once the new file has been parsed, chunked and
embedded; a corrupt, encrypted, blank or oversize PDF is rejected (422/413) and the
previous policy + index stay as they were.
"""
import os
import tempfile
import threading

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.utils.deps import get_compliance_user
from app.models.user import User
from app.models.tenant import Tenant
from app.services import document_ingestion_service as dis
from app.services.chroma_client import get_tenant_collection
from app.services import client_storage

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

POLICY_FILENAME = "policy.pdf"
_COPY_BLOCK = 1024 * 1024

# One policy upload/delete at a time per tenant (in-process), so two overlapping
# re-uploads can't interleave their index swaps.
_tenant_locks: dict = {}
_tenant_locks_guard = threading.Lock()


def _tenant_lock(tid: str) -> threading.Lock:
    with _tenant_locks_guard:
        return _tenant_locks.setdefault(tid, threading.Lock())


def _busy() -> HTTPException:
    return HTTPException(status_code=409,
                         detail="A policy upload for this client is already in progress")


def _client_id(db: Session, user: User) -> str:
    # A SUPER_ADMIN has no tenant_id; without a tenant we'd write to clients/None/ and a
    # tenant_None_docs collection. Policy upload must be scoped to a real tenant.
    if not user.tenant_id:
        raise HTTPException(status_code=400,
                            detail="Document actions must be performed by a tenant user (no tenant context).")
    t = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    return (t.tenant_id_public if t else None) or str(user.tenant_id)


@router.post("/upload")
def upload_policy(file: UploadFile = File(...), db: Session = Depends(get_db),
                  current_user: User = Depends(get_compliance_user)):
    # Plain `def` on purpose: FastAPI runs it in the threadpool. Parsing, tokenizing and
    # embedding a policy is seconds-to-minutes of CPU; as `async def` it ran on the event
    # loop and froze every other request (incl. /health) until it finished.
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    cid = _client_id(db, current_user)
    tid = str(current_user.tenant_id)               # Chroma is keyed by the tenant UUID
    db.close()                                      # don't pin a pooled connection while indexing

    lock = _tenant_lock(tid)
    if not lock.acquire(blocking=False):
        raise _busy()
    try:
        n = _store_and_index(file, cid, tid)
    finally:
        lock.release()

    return {"status": "ok", "client_id": cid, "stored_filename": POLICY_FILENAME,
            "original_filename": os.path.basename(file.filename), "chunks_indexed": n}


def _store_and_index(file: UploadFile, cid: str, tid: str) -> int:
    """Validate + parse + chunk + embed the upload from a temp file, and only then
    replace the tenant's index and stored policy.pdf. Any failure leaves both as they were."""
    dest = client_storage.policy_path(cid)          # storage/clients/<cid>/policy.pdf
    max_bytes = settings.MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), prefix=".policy-", suffix=".pdf.part")
    try:
        with os.fdopen(fd, "wb") as out:            # 1. spool the upload next to policy.pdf
            size = 0
            while block := file.file.read(_COPY_BLOCK):
                size += len(block)
                if size > max_bytes:
                    raise HTTPException(status_code=413, detail="File exceeds the maximum allowed size")
                out.write(block)

        try:                                        # 2. parse + chunk (capped)
            chunks = dis.build_chunks(tmp, doc_title=f"{cid} AML Policy",
                                      filename=POLICY_FILENAME, doc_id=POLICY_FILENAME,
                                      max_pages=settings.MAX_POLICY_PAGES,
                                      max_chars=settings.MAX_POLICY_TEXT_CHARS)
        except dis.PolicyTooLargeError as e:
            raise HTTPException(status_code=413, detail=str(e))
        except dis.UnreadablePdfError as e:
            raise HTTPException(status_code=422, detail=str(e))
        if not chunks:
            raise HTTPException(status_code=422,
                                detail="PDF contains no extractable text (scanned? run OCR first)")

        n = dis.replace_index(tid, chunks)          # 3. embed, then swap the index
        os.replace(tmp, dest)                       # 4. swap the stored file
        return n
    finally:
        try:
            os.remove(tmp)                          # gone already after a successful replace
        except FileNotFoundError:
            pass


@router.get("/")
def get_policy_info(db: Session = Depends(get_db),
                    current_user: User = Depends(get_compliance_user)):
    cid = _client_id(db, current_user)
    tid = str(current_user.tenant_id)
    path = client_storage.policy_path(cid)
    try:
        total = get_tenant_collection(tid).count()
    except Exception:
        total = None
    present = os.path.isfile(path)
    # Filename only: the server-side storage path is an internal detail.
    return {"client_id": cid, "policy_present": present,
            "policy_filename": POLICY_FILENAME if present else None,
            "chunks_indexed": total}


@router.delete("/")
def delete_policy(db: Session = Depends(get_db),
                  current_user: User = Depends(get_compliance_user)):
    cid = _client_id(db, current_user)
    tid = str(current_user.tenant_id)
    path = client_storage.policy_path(cid)
    lock = _tenant_lock(tid)
    if not lock.acquire(blocking=False):
        raise _busy()
    try:
        existed = os.path.isfile(path)
        if existed:
            os.remove(path)
        from app.services.chroma_client import reset_tenant_collection
        try:
            reset_tenant_collection(tid)  # drop this client's chunks
        except Exception:
            pass
    finally:
        lock.release()
    if not existed:
        raise HTTPException(status_code=404, detail="No policy on file")
    return {"status": "ok", "deleted_client": cid}
