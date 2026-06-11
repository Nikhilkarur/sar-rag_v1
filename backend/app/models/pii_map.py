from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import text, ForeignKey, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import DateTime
from app.database import Base
from app.utils.security import encrypt_json, decrypt_json

class EncryptedJSONB(TypeDecorator):
    """Fernet-encrypts the JSON value before it reaches the database, so a
    stolen DB dump exposes only ciphertext. Stored as {"__enc__": "<token>"}
    inside the existing JSONB column — no column type migration needed.
    Plaintext rows written before this change are still readable (decrypt is
    skipped when the marker key is absent)."""
    impl = JSONB
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return {"__enc__": encrypt_json(value)}

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, dict) and "__enc__" in value:
            return decrypt_json(value["__enc__"])
        return value  # legacy plaintext row

class PIIMap(Base):
    __tablename__ = "pii_maps"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    alert_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), unique=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    token_map: Mapped[Dict[str, Any]] = mapped_column(EncryptedJSONB, nullable=False)
    
    masked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    rehydrated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
