from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.tenant import Tenant
from app.utils.security import verify_api_key, dummy_verify

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def parse_uuid_or_404(value: str, what: str = "Resource") -> UUID:
    """Path params compared against Postgres UUID columns must be valid UUIDs,
    or psycopg2 raises a DataError that surfaces as a 500. Garbage in → 404."""
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail=f"{what} not found")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            # Refresh tokens live 7 days; never accept one in place of a
            # 15-minute access token (token-type confusion)
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

def get_current_active_tenant_user(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if not user.tenant_id:
        return user # Super admins have no tenant_id but are considered active
    
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if tenant.status != 'ACTIVE':
        raise HTTPException(status_code=403, detail="Tenant is not active")
        
    return user

def get_super_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return user

def get_tenant_admin(user: User = Depends(get_current_active_tenant_user)) -> User:
    if user.role not in ["SUPER_ADMIN", "TENANT_ADMIN"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return user

def get_compliance_user(user: User = Depends(get_current_active_tenant_user)) -> User:
    if user.role not in ["SUPER_ADMIN", "TENANT_ADMIN", "COMPLIANCE_OFFICER"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return user

def authenticate_api_key(
    x_api_key: str = Header(...), 
    x_tenant_id: str = Header(...),
    db: Session = Depends(get_db)
) -> Tenant:
    invalid_credentials = HTTPException(
        status_code=401, detail="Invalid API Key or Tenant ID"
    )

    tenant = db.query(Tenant).filter(Tenant.tenant_id_public == x_tenant_id).first()

    # Equalize timing: every failure path pays exactly one bcrypt round, so
    # response latency cannot be used to enumerate valid tenant IDs.
    if not tenant or not tenant.api_key_hash:
        dummy_verify(x_api_key)
        raise invalid_credentials

    if not verify_api_key(x_api_key, tenant.api_key_hash):
        raise invalid_credentials

    # Status is only disclosed after the caller has proven key possession
    if tenant.status != 'ACTIVE':
        raise HTTPException(status_code=403, detail="Tenant is not active")

    return tenant
