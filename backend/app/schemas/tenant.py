from pydantic import BaseModel, StringConstraints
from typing import Annotated, Optional, List
from datetime import datetime
from uuid import UUID

class TenantResponse(BaseModel):
    # tenants.id is a UUID column; pydantic v2 does not coerce UUID -> str, so a
    # `str` here failed response validation (500 on every GET /tenant/profile).
    id: UUID
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
    # The PUBLIC id (TEN-XXXX): the value integrations send as X-Tenant-Id. The internal
    # UUID is under `id`, as on the other admin tenant payloads.
    tenant_id: str
    id: UUID
    status: str
    api_key: str # THIS IS THE ONLY TIME IT IS RETURNED IN PLAINTEXT

class TenantRejectRequest(BaseModel):
    # Shown to the applicant on their status page: an empty/blank reason is a 422
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2000)]
