from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import DateTime, TEXT
from app.database import Base

class SARDraft(Base):
    __tablename__ = "sar_drafts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    alert_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), unique=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    draft_text: Mapped[str] = mapped_column(TEXT, nullable=False)
    draft_structured: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    
    officer_edit_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_edited_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    last_edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    approved_text: Mapped[Optional[str]] = mapped_column(TEXT)
    rehydrated_text: Mapped[Optional[str]] = mapped_column(TEXT)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500))
    pdf_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    llm_provider: Mapped[Optional[str]] = mapped_column(String(30))
    llm_model: Mapped[Optional[str]] = mapped_column(String(100))
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    generation_latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    prompt_used: Mapped[Optional[str]] = mapped_column(TEXT)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
