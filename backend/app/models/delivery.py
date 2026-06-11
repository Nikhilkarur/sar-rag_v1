from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Boolean, text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import DateTime, TEXT
from app.database import Base

class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    sar_draft_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("sar_drafts.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    destination_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_internal_sink: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'PENDING'"))
    
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    
    http_status_code: Mapped[Optional[int]] = mapped_column(Integer)
    response_body: Mapped[Optional[str]] = mapped_column(TEXT)
    request_headers: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    request_body_hash: Mapped[Optional[str]] = mapped_column(String(64))
    
    hmac_signature: Mapped[Optional[str]] = mapped_column(String(128))
    
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    error_message: Mapped[Optional[str]] = mapped_column(TEXT)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
