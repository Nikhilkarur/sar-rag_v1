from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, text, ForeignKey, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import DateTime
from app.database import Base

class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    provider: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'GROQ'"))
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, server_default=text("'llama-3.3-70b-versatile'"))
    sar_template_style: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'BOTH'"))
    
    private_base_url: Mapped[Optional[str]] = mapped_column(String(500))
    private_token_hash: Mapped[Optional[str]] = mapped_column(String(255))
    
    total_tokens_used: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    total_requests: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

