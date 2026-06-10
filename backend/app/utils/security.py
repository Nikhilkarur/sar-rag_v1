from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt
import bcrypt
import secrets
from app.config import settings

import hashlib

def _preprocess_password(password: str) -> bytes:
    pw_bytes = password.encode('utf-8')
    if len(pw_bytes) > 71:
        # Prevent bcrypt 72-byte limit while preserving entropy
        return hashlib.sha256(pw_bytes).hexdigest().encode('utf-8')
    return pw_bytes

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(_preprocess_password(password), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(_preprocess_password(plain_password), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def generate_api_key() -> str:
    return f"sk-ae-{secrets.token_hex(17)}"

def hash_api_key(key: str) -> str:
    return hash_password(key)

def verify_api_key(plain_key: str, stored_hash: str) -> bool:
    return verify_password(plain_key, stored_hash)
