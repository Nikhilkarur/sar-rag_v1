from datetime import datetime
from typing import Optional
from sqlalchemy import String, text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TEXT, JSONB
from sqlalchemy import DateTime
from app.database import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    company_type: Mapped[str] = mapped_column(String(50), nullable=False)
    cin: Mapped[Optional[str]] = mapped_column(String(50))
    sebi_reg_no: Mapped[Optional[str]] = mapped_column(String(50))
    website: Mapped[Optional[str]] = mapped_column(String(255))
    
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default='PENDING_VERIFICATION')
    rejection_reason: Mapped[Optional[str]] = mapped_column(TEXT)
    
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255))
    api_key_prefix: Mapped[Optional[str]] = mapped_column(String(12))
    tenant_id_public: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    suspended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    suspended_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
