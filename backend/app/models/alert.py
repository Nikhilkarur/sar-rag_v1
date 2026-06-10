from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import String, Boolean, text, ForeignKey, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import DateTime, TEXT
from app.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    schema_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("ingestion_schemas.id"))
    
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'PENDING_INGESTION'"))
    
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    normalized_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    masked_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    
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
