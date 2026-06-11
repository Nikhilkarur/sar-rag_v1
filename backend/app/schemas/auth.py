from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserSignup(BaseModel):
    # Length caps prevent multi-megabyte strings reaching bcrypt/DB;
    # min password length enforces a baseline policy.
    # Aliases match the portal signup form's field names.
    tenant_name: str = Field(min_length=2, max_length=120, alias="company_name")
    company_type: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(alias="admin_email")
    password: str = Field(min_length=10, max_length=128, alias="admin_password")
    full_name: str = Field(min_length=1, max_length=120, alias="admin_name")
    designation: Optional[str] = Field(None, max_length=80, alias="admin_designation")
    phone: Optional[str] = Field(None, max_length=20, alias="admin_phone")
    cin: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)

    model_config = {"populate_by_name": True}

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

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
