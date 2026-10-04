import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from jose import jwt, JWTError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User, RefreshSession
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

def _start_session(user: User, db: Session) -> tuple[str, str]:
    """Open a new refresh session for this login and mint its token pair. Each login
    (tab/device) gets its own row, so logging in elsewhere never kills this one."""
    now = datetime.now(timezone.utc)
    # Housekeeping: expired sessions can no longer be refreshed (the JWT exp has passed)
    db.query(RefreshSession).filter(
        RefreshSession.user_id == user.id, RefreshSession.expires_at < now
    ).delete(synchronize_session=False)

    session_id = uuid.uuid4()
    refresh_token = create_refresh_token(data={"sub": str(user.id), "sid": str(session_id)})
    db.add(RefreshSession(
        id=session_id,
        user_id=user.id,
        token_hash=hash_password(refresh_token),
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    return create_access_token(data={"sub": str(user.id)}), refresh_token

def signup_tenant_admin(data: UserSignup, db: Session):
    # Pre-check for a friendly error; the unique constraint below remains the
    # authoritative guard against two concurrent signups racing past this
    # (new emails are always stored lowercase). lower() also catches accounts
    # created with mixed case before emails were normalized.
    existing_user = db.query(User).filter(func.lower(User.email) == data.email).first()
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

    access_token, refresh_token = _start_session(user, db)

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
    # data.email is already lowercase; lower() on the column also matches accounts stored
    # with mixed case before normalization. Such legacy rows can collide on lower(email),
    # so try the exact match first and accept whichever account the password opens.
    candidates = db.query(User).filter(func.lower(User.email) == data.email).order_by(
        (User.email == data.email).desc(), User.created_at
    ).all()
    if not candidates:
        # Burn a bcrypt round so unknown emails take as long as wrong passwords
        dummy_verify(data.password)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = next((u for u in candidates if verify_password(data.password, u.password_hash)), None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is inactive")
        
    access_token, refresh_token = _start_session(user, db)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": serialize_user(user, db)
    }

def _decode_refresh_token(refresh_token: str):
    """(user_id, session_id) of a validly signed, unexpired refresh token, else None.
    Tokens minted before per-session refresh (no "sid") are rejected: sign in again."""
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh" or not payload.get("sub") or not payload.get("sid"):
            return None
        return uuid.UUID(str(payload["sub"])), uuid.UUID(str(payload["sid"]))
    except (JWTError, ValueError):
        return None

def refresh_tokens(refresh_token: str, db: Session):
    invalid = HTTPException(status_code=401, detail="Invalid refresh token")
    claims = _decode_refresh_token(refresh_token)
    if not claims:
        raise invalid
    user_id, session_id = claims

    # Row lock: two refreshes presenting the same token serialize here, so exactly one
    # rotates it and the other is treated as a replay below.
    session = db.query(RefreshSession).filter(
        RefreshSession.id == session_id, RefreshSession.user_id == user_id
    ).with_for_update().first()
    user = db.query(User).filter(User.id == user_id).first()
    if (not session or session.revoked_at is not None
            or session.expires_at <= datetime.now(timezone.utc)
            or not user or not user.is_active):
        dummy_verify(refresh_token)
        raise invalid

    # The stored hash is this session's CURRENT token. Anything else carrying this
    # session's id was signed by us and has already been rotated away, i.e. it is being
    # replayed (stolen or copied): revoke the session so neither holder can keep it.
    if not verify_password(refresh_token, session.token_hash):
        session.revoked_at = func.now()
        session.revoked_reason = "TOKEN_REUSE"
        db.add(AuditLog(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="REFRESH_TOKEN_REUSE",
            entity_type="refresh_session",
            entity_id=session.id,
        ))
        db.commit()
        raise invalid

    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh = create_refresh_token(data={"sub": str(user.id), "sid": str(session.id)})
    now = datetime.now(timezone.utc)
    session.token_hash = hash_password(new_refresh)
    session.last_used_at = now
    session.expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }

def logout(refresh_token: str, db: Session):
    """Revoke the refresh session this token belongs to. Always succeeds: logging out
    with an unknown/expired token leaves nothing to revoke and reveals nothing."""
    claims = _decode_refresh_token(refresh_token)
    if claims:
        user_id, session_id = claims
        session = db.query(RefreshSession).filter(
            RefreshSession.id == session_id, RefreshSession.user_id == user_id
        ).first()
        if session and session.revoked_at is None:
            session.revoked_at = func.now()
            session.revoked_reason = "LOGOUT"
            db.commit()
    return {"status": "ok"}
