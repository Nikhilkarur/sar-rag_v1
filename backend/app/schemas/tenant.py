from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    company_type: str
    status: str
    tenant_id_public: Optional[str] = None
    
    class Config:
        from_attributes = True

class TenantApproveRequest(BaseModel):
    pass # No body required, but can extend later

class TenantApproveResponse(BaseModel):
    tenant_id: str
    status: str
    api_key: str # THIS IS THE ONLY TIME IT IS RETURNED IN PLAINTEXT

class TenantRejectRequest(BaseModel):
    reason: str
