from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy import String, Boolean, text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import DateTime
from app.database import Base

class WebhookConfig(Base):
    __tablename__ = "webhook_configs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    callback_url: Mapped[Optional[str]] = mapped_column(String(500))
    use_internal_sink: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    
    secret_hash: Mapped[Optional[str]] = mapped_column(String(255))
    secret_prefix: Mapped[Optional[str]] = mapped_column(String(12))
    # Fernet-encrypted secret — required to actually sign outbound HMAC payloads
    secret_encrypted: Mapped[Optional[str]] = mapped_column(String(500))
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_test_status: Mapped[Optional[str]] = mapped_column(String(20))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

class WebhookSinkEvent(Base):
    __tablename__ = "webhook_sink_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    headers: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    
    hmac_valid: Mapped[Optional[bool]] = mapped_column(Boolean)
    
    source_ip: Mapped[Optional[str]] = mapped_column(String(50))
    delivery_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("webhook_deliveries.id"))
    
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
