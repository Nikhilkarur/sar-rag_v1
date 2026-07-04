from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import DateTime
from app.database import Base
# EncryptedJSONB moved to a shared module so alerts/webhook events can reuse it.
from app.models.encrypted_types import EncryptedJSONB

class PIIMap(Base):
    __tablename__ = "pii_maps"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    alert_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), unique=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    token_map: Mapped[Dict[str, Any]] = mapped_column(EncryptedJSONB, nullable=False)
    
    masked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    rehydrated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
