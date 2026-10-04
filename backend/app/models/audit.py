from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import String, text, ForeignKey, event
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import DateTime
from app.database import Base
from app.utils import request_context

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"))
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    
    details: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    
    actor_ip: Mapped[Optional[str]] = mapped_column(String(50))
    actor_user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


@event.listens_for(AuditLog, "before_insert")
def _fill_actor_ip(mapper, connection, target):
    # Call sites don't pass the caller's IP; take it from the request being served
    # (set by APILoggingMiddleware). Stays None outside a request (scripts, seeding).
    if target.actor_ip is None:
        ip = request_context.client_ip.get()
        target.actor_ip = ip[:50] if ip else None
