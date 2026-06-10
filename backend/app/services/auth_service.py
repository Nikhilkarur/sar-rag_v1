import re
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.tenant import Tenant
from app.models.audit import AuditLog
from app.schemas.auth import UserSignup, UserLogin
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token

def generate_slug(name: str) -> str:
    # Very basic slugification
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug

def signup_tenant_admin(data: UserSignup, db: Session):
    # 1. Check email
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    slug = generate_slug(data.tenant_name)
    existing_tenant = db.query(Tenant).filter(Tenant.slug == slug).first()
    if existing_tenant:
        slug = f"{slug}-{User.query.count()}" # just a simple deduplication
        
    # 2. Create Tenant
    tenant = Tenant(
        name=data.tenant_name,
        slug=slug,
        company_type=data.company_type,
        status="PENDING_VERIFICATION"
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    # 3. Create User
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
    db.commit()
    db.refresh(user)
    
    # 4. Audit Log
    audit = AuditLog(
        tenant_id=tenant.id,
        user_id=user.id,
        action="TENANT_SIGNUP",
        entity_type="tenant",
        entity_id=tenant.id,
        details={"tenant_name": tenant.name}
    )
    db.add(audit)
    db.commit()
    
    # 5. Return JWT pair
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    user.refresh_token_hash = hash_password(refresh_token)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }

def login_user(data: UserLogin, db: Session):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
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
        "user": user
    }
