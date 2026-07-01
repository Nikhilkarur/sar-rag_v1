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
"""
import os
import shutil

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


def _client_id(db: Session, user: User) -> str:
    # A SUPER_ADMIN has no tenant_id; without a tenant we'd write to clients/None/ and a
    # tenant_None_docs collection. Policy upload must be scoped to a real tenant.
    if not user.tenant_id:
        raise HTTPException(status_code=400,
                            detail="Document actions must be performed by a tenant user (no tenant context).")
    t = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    return (t.tenant_id_public if t else None) or str(user.tenant_id)


@router.post("/upload")
async def upload_policy(file: UploadFile = File(...), db: Session = Depends(get_db),
                        current_user: User = Depends(get_compliance_user)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the maximum allowed size")

    cid = _client_id(db, current_user)
    tid = str(current_user.tenant_id)               # Chroma is keyed by the tenant UUID
    dest = client_storage.policy_path(cid)          # storage/clients/<cid>/policy.pdf
    with open(dest, "wb") as f:                     # 1. store the RAW pdf
        f.write(data)

    # 2. re-index this client's policy into Chroma (reset first so re-upload replaces)
    from app.services.chroma_client import reset_tenant_collection
    reset_tenant_collection(tid)
    chunks = dis.build_chunks(dest, doc_title=f"{cid} AML Policy",
                              filename="policy.pdf", doc_id="policy.pdf")
    n = dis.index_document(tid, chunks)

    return {"status": "ok", "client_id": cid, "stored_path": dest,
            "original_filename": os.path.basename(file.filename), "chunks_indexed": n}


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
    return {"client_id": cid, "policy_present": os.path.isfile(path),
            "policy_path": path if os.path.isfile(path) else None,
            "chunks_indexed": total}


@router.delete("/")
def delete_policy(db: Session = Depends(get_db),
                  current_user: User = Depends(get_compliance_user)):
    cid = _client_id(db, current_user)
    tid = str(current_user.tenant_id)
    path = client_storage.policy_path(cid)
    existed = os.path.isfile(path)
    if existed:
        os.remove(path)
    from app.services.chroma_client import reset_tenant_collection
    try:
        reset_tenant_collection(tid)  # drop this client's chunks
    except Exception:
        pass
    if not existed:
        raise HTTPException(status_code=404, detail="No policy on file")
    return {"status": "ok", "deleted_client": cid}
