from pydantic import BaseModel, EmailStr
from typing import Optional

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserSignup(BaseModel):
    tenant_name: str
    company_type: str
    email: EmailStr
    password: str
    full_name: str
    designation: Optional[str] = None
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

from uuid import UUID

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    tenant_id: Optional[UUID]
    is_active: bool

    class Config:
        from_attributes = True
