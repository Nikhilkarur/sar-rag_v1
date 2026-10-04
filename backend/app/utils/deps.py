from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.tenant import Tenant
from app.utils.security import verify_api_key, dummy_verify

# Plain bearer scheme: Swagger's "Authorize" takes a pasted access token. (The old
# OAuth2PasswordBearer advertised a form-encoded password flow against /auth/login,
# which only accepts JSON, so Authorize always failed with 422.) auto_error=False so a
# missing token stays a 401, which the SPA's refresh interceptor relies on; HTTPBearer
# itself would answer 403.
bearer_scheme = HTTPBearer(auto_error=False)

def parse_uuid_or_404(value: str, what: str = "Resource") -> UUID:
    """Path params compared against Postgres UUID columns must be valid UUIDs,
    or psycopg2 raises a DataError that surfaces as a 500. Garbage in → 404."""
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail=f"{what} not found")

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
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
    """Base guard for every tenant-scoped endpoint (/tenant/*, /alerts/*, /documents/*):
    the caller must belong to an ACTIVE tenant."""
    if not user.tenant_id:
        # Super admins have no tenant: handlers would dereference a missing tenant (500)
        # or silently show empty data. Platform-wide data lives under /api/v1/admin.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required")
    
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

def get_compliance_user_or_super_admin(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """For the few non-tenant-scoped reads a super admin may also make (e.g. any SAR PDF);
    everyone else goes through the regular tenant guards."""
    if user.role == "SUPER_ADMIN":
        return user
    return get_compliance_user(get_current_active_tenant_user(user, db))

def authenticate_api_key(
    x_api_key: str = Header(...), 
    x_tenant_id: str = Header(...),
    db: Session = Depends(get_db)
) -> Tenant:
    invalid_credentials = HTTPException(
        status_code=401, detail="Invalid API Key or Tenant ID"
    )

    tenant = db.query(Tenant).filter(Tenant.tenant_id_public == x_tenant_id).first()
    # Hand the pooled connection back before the slow bcrypt check (the row is
    # fully loaded; detach it so ending the transaction doesn't expire it). Held
    # through bcrypt and the dependency chain, a burst of ingests drained the pool.
    if tenant is not None:
        db.expunge(tenant)
    db.rollback()

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
