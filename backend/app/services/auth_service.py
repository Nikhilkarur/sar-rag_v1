import re
import secrets
from fastapi import HTTPException
from jose import jwt, JWTError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User
from app.models.tenant import Tenant
from app.models.audit import AuditLog
from app.schemas.auth import UserSignup, UserLogin
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token, dummy_verify

def generate_slug(name: str) -> str:
    # Very basic slugification
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug

def serialize_user(user: User, db: Session) -> dict:
    """Shape the portal's auth store expects (camelCase user + nested tenant)."""
    tenant = None
    if user.tenant_id:
        t = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if t:
            tenant = {
                "id": str(t.id),
                "name": t.name,
                "status": t.status,
                "tenantIdPublic": t.tenant_id_public,
                "companyType": t.company_type,
                "rejectionReason": t.rejection_reason,
            }
    return {
        "id": str(user.id),
        "email": user.email,
        "fullName": user.full_name,
        "role": user.role,
        "tenant": tenant,
    }

def signup_tenant_admin(data: UserSignup, db: Session):
    # Pre-check for a friendly error; the unique constraint below remains the
    # authoritative guard against two concurrent signups racing past this.
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    slug = generate_slug(data.tenant_name) or "tenant"
    if db.query(Tenant).filter(Tenant.slug == slug).first():
        # Random suffix instead of a count: counts collide under concurrency
        # and after deletions
        slug = f"{slug}-{secrets.token_hex(3)}"

    # Tenant + user + audit log are one atomic unit: a failure mid-way must
    # not leave an orphaned tenant without an admin user.
    tenant = Tenant(
        name=data.tenant_name,
        slug=slug,
        company_type=data.company_type,
        cin=data.cin,
        website=data.website,
        status="PENDING_VERIFICATION"
    )
    db.add(tenant)
    db.flush()  # assigns tenant.id without committing

    user = User(
        tenant_id=tenant.id,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        designation=data.designation,
        phone=data.phone,
        role="TENANT_ADMIN"
    )
    db.add(user)
    db.flush()

    db.add(AuditLog(
        tenant_id=tenant.id,
        user_id=user.id,
        action="TENANT_SIGNUP",
        entity_type="tenant",
        entity_id=tenant.id,
        details={"tenant_name": tenant.name}
    ))

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    user.refresh_token_hash = hash_password(refresh_token)

    try:
        db.commit()
    except IntegrityError:
        # Lost a race on users.email or tenants.slug — clean 400, never a 500
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    db.refresh(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": serialize_user(user, db)
    }

def login_user(data: UserLogin, db: Session):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # Burn a bcrypt round so unknown emails take as long as wrong passwords
        dummy_verify(data.password)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is inactive")
        
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    user.refresh_token_hash = hash_password(refresh_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": serialize_user(user, db)
    }

def refresh_tokens(refresh_token: str, db: Session):
    invalid = HTTPException(status_code=401, detail="Invalid refresh token")
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise invalid
    if payload.get("type") != "refresh" or not payload.get("sub"):
        raise invalid

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active or not user.refresh_token_hash:
        dummy_verify(refresh_token)
        raise invalid
    # The stored hash binds the token to this user; a revoked/rotated token fails here
    if not verify_password(refresh_token, user.refresh_token_hash):
        raise invalid

    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh = create_refresh_token(data={"sub": str(user.id)})
    user.refresh_token_hash = hash_password(new_refresh)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }
