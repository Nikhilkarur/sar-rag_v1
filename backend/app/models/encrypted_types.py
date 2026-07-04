"""
SQLAlchemy TypeDecorators that transparently Fernet-encrypt PII columns at rest,
so a stolen DB dump exposes only ciphertext. Encryption/decryption happens in
Python on write/read; the underlying column type (JSONB / TEXT) is unchanged, so
NO DDL migration is required to adopt them.

Both decorators are LEGACY-TOLERANT: rows written as plaintext before the column
was switched over still decode (the encryption marker is simply absent), so an
existing database keeps working and only newly-written rows are encrypted.

NOTE: because values are encrypted opaquely, these columns can no longer be
filtered/indexed with SQL JSONB operators. Every current reader loads them as
Python attributes, so that's fine — keep it that way.
"""
from typing import Any

from sqlalchemy import TEXT, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB

from app.utils.security import encrypt_json, decrypt_json

# Sentinel prefix marking an EncryptedText payload (distinguishes ciphertext from
# a legacy plaintext narrative). Fernet tokens are opaque, so we tag our own.
_TEXT_ENC_PREFIX = "enc::v1::"


class EncryptedJSONB(TypeDecorator):
    """Fernet-encrypts a JSON value before it reaches the database. Stored as
    {"__enc__": "<token>"} inside the existing JSONB column. Plaintext rows
    written before this change are still readable (marker key absent)."""
    impl = JSONB
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return {"__enc__": encrypt_json(value)}

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, dict) and "__enc__" in value:
            return decrypt_json(value["__enc__"])
        return value  # legacy plaintext row


class EncryptedText(TypeDecorator):
    """Fernet-encrypts a text value (e.g. a rehydrated SAR narrative carrying real
    PII) before it reaches the database. Stored in the existing TEXT column with a
    sentinel prefix. Legacy plaintext rows (no prefix) are returned as-is."""
    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _TEXT_ENC_PREFIX + encrypt_json(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str) and value.startswith(_TEXT_ENC_PREFIX):
            return decrypt_json(value[len(_TEXT_ENC_PREFIX):])
        return value  # legacy plaintext row
