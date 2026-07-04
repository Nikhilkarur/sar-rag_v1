from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import String, Boolean, text, ForeignKey, Numeric, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import DateTime, TEXT
from app.database import Base
# raw_payload / normalized_payload carry real, un-masked PII. Encrypt them at rest;
# masked_payload stays plaintext JSONB (tokenized, no PII, and read by the pipeline).
from app.models.encrypted_types import EncryptedJSONB

class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        # Replay protection: one alert per (tenant, idempotency key).
        # Postgres treats NULLs as distinct, so legacy/simulator rows are unaffected.
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_alerts_tenant_idempotency"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    schema_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_schemas.id", ondelete="SET NULL"))
    
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'PENDING_INGESTION'"))
    
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(EncryptedJSONB, nullable=False)
    normalized_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(EncryptedJSONB)
    masked_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    
    # Client-supplied Idempotency-Key header, or SHA-256 of the raw body when absent
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255))

    transaction_id: Mapped[Optional[str]] = mapped_column(String(255))
    transaction_amount: Mapped[Optional[float]] = mapped_column(Numeric(20, 4))
    transaction_currency: Mapped[Optional[str]] = mapped_column(String(10), server_default=text("'INR'"))
    transaction_type: Mapped[Optional[str]] = mapped_column(String(50))
    transaction_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    risk_score: Mapped[Optional[int]] = mapped_column(Integer)
    
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    processing_error: Mapped[Optional[str]] = mapped_column(TEXT)
    
    reviewed_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[Optional[str]] = mapped_column(TEXT)
    
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    source: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'API'"))
    ingested_from_ip: Mapped[Optional[str]] = mapped_column(String(50))
    # Test alerts injected from the portal simulator. Must be excluded from
    # compliance metrics/aggregations — filter with Alert.is_synthetic == False.
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
