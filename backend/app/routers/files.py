"""
Serve generated SAR PDFs.

GET /files/sar/{sar_id}.pdf  -> the rendered SAR PDF for that draft.

NOTE: for the local demo this is OPEN (looked up by the draft's UUID, which is
unguessable enough locally). In production, replace with a signed, time-limited URL.
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sar import SARDraft
from app.utils.deps import parse_uuid_or_404

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/sar/{sar_id}.pdf")
def get_sar_pdf(sar_id: str, db: Session = Depends(get_db)):
    # A non-UUID sar_id would hit a Postgres UUID cast error (500); normalize to 404.
    parse_uuid_or_404(sar_id, "SAR PDF")
    draft = db.query(SARDraft).filter(SARDraft.id == sar_id).first()
    if not draft or not draft.pdf_path or not os.path.isfile(draft.pdf_path):
        raise HTTPException(status_code=404, detail="SAR PDF not found")
    return FileResponse(draft.pdf_path, media_type="application/pdf",
                        filename=f"SAR-{sar_id}.pdf")
