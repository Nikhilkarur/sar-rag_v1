"""
Serve generated SAR PDFs.

GET /files/sar/{sar_id}.pdf  -> the SAR PDF for that draft, RE-RENDERED in memory on demand.

The PDF carries a customer-PII regulatory filing, so it is (a) never persisted to Aegis's disk
and (b) NOT open: a caller must present a valid tenant JWT and may only fetch SARs belonging to
their own tenant (a super-admin may fetch any). The bank does not depend on this endpoint — the
PDF bytes are pushed to it in the approval webhook (pdf_base64); it stores + serves its own copy.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sar import SARDraft
from app.models.user import User
from app.services.sar_delivery import build_draft_pdf_bytes
from app.utils.deps import parse_uuid_or_404, get_compliance_user

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/sar/{sar_id}.pdf")
def get_sar_pdf(sar_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_compliance_user)):
    # A non-UUID sar_id would hit a Postgres UUID cast error (500); normalize to 404.
    parse_uuid_or_404(sar_id, "SAR PDF")
    draft = db.query(SARDraft).filter(SARDraft.id == sar_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="SAR PDF not found")
    # Tenant isolation: don't reveal (even by 403 vs 404) another tenant's SAR.
    if user.role != "SUPER_ADMIN" and draft.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="SAR PDF not found")
    pdf_bytes = build_draft_pdf_bytes(db, draft)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="SAR PDF not found")
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="SAR-{sar_id}.pdf"'})
