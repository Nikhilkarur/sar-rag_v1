from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt
import bcrypt
import secrets
from app.config import settings

import base64
import hashlib
import ipaddress
import json
import socket
from urllib.parse import urlparse
from cryptography.fernet import Fernet, InvalidToken

def _preprocess_password(password: str) -> bytes:
    pw_bytes = password.encode('utf-8')
    if len(pw_bytes) > 71:
        # Prevent bcrypt 72-byte limit while preserving entropy
        return hashlib.sha256(pw_bytes).hexdigest().encode('utf-8')
    return pw_bytes

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(_preprocess_password(password), salt).decode('utf-8')

# Pre-computed hash used to equalize timing on code paths where no real
# credential exists (unknown user/tenant), so attackers cannot distinguish
# "record not found" from "wrong secret" by measuring response latency.
_DUMMY_HASH = bcrypt.hashpw(b"aegis-timing-equalizer", bcrypt.gensalt())

def dummy_verify(plain_secret: str = "x") -> None:
    """Burn a full bcrypt round against a throwaway hash. Call this on
    not-found branches so they take the same time as a real verification."""
    bcrypt.hashpw(_preprocess_password(plain_secret), _DUMMY_HASH)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        hashed_bytes = hashed_password.encode('utf-8')
        candidate = bcrypt.hashpw(_preprocess_password(plain_password), hashed_bytes)
        return secrets.compare_digest(candidate, hashed_bytes)
    except ValueError:
        # Malformed stored hash: still pay the bcrypt cost before rejecting
        dummy_verify(plain_password)
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # "type" claim prevents a long-lived refresh token from being replayed
    # as a short-lived access token (token-type confusion)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- PII encryption at rest (Fernet: AES-128-CBC + HMAC-SHA256) ---

def _get_fernet() -> Fernet:
    if settings.PII_ENCRYPTION_KEY:
        key = settings.PII_ENCRYPTION_KEY.encode('utf-8')
    else:
        # Dev fallback: derive a stable key from SECRET_KEY. Set
        # PII_ENCRYPTION_KEY explicitly in production so the JWT signing key
        # and the data-at-rest key can be rotated independently.
        digest = hashlib.sha256(f"pii-at-rest:{settings.SECRET_KEY}".encode('utf-8')).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)

def encrypt_json(obj: Any) -> str:
    return _get_fernet().encrypt(json.dumps(obj).encode('utf-8')).decode('utf-8')

def decrypt_json(token: str) -> Any:
    try:
        return json.loads(_get_fernet().decrypt(token.encode('utf-8')))
    except InvalidToken:
        raise ValueError("PII decryption failed: wrong PII_ENCRYPTION_KEY or corrupted ciphertext")

# --- SSRF guard for tenant-supplied outbound URLs (webhooks) ---

def validate_webhook_url(url: str) -> None:
    """Raise ValueError unless the URL is safe to call from the server.
    Blocks loopback, RFC1918, link-local (incl. 169.254.169.254 cloud
    metadata), reserved and multicast ranges across every resolved A/AAAA
    record. NOTE: any future dispatcher must re-resolve and re-check at
    connect time (or pin these IPs) to defeat DNS rebinding."""
    if not url or len(url) > 500:
        raise ValueError("Webhook URL must be 1-500 characters")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Webhook URL must use http or https")
    if settings.ENVIRONMENT == "production" and parsed.scheme != "https":
        raise ValueError("Webhook URL must use https in production")
    if parsed.username or parsed.password:
        raise ValueError("Webhook URL must not embed credentials")
    if not parsed.hostname:
        raise ValueError("Webhook URL has no hostname")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addr_infos = socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError("Webhook hostname could not be resolved")

    for info in addr_infos:
        ip = ipaddress.ip_address(info[4][0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped  # ::ffff:10.0.0.1 must be judged as 10.0.0.1
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError("Webhook URL resolves to a private/internal address and was rejected")

def generate_api_key() -> str:
    return f"sk-ae-{secrets.token_hex(17)}"

def hash_api_key(key: str) -> str:
    return hash_password(key)

def verify_api_key(plain_key: str, stored_hash: str) -> bool:
    return verify_password(plain_key, stored_hash)
