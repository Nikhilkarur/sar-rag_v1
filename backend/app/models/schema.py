from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import String, Boolean, text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import DateTime
from app.database import Base

class IngestionSchema(Base):
    __tablename__ = "ingestion_schemas"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_key: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    
    field_map: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    pii_fields: Mapped[List[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
