"""
seed.py - the absolute bare minimum to log in and test. No dummy alerts.

Creates (idempotently):
  1. One SUPER_ADMIN          admin@aegis-aml.com          (override: AEGIS_ADMIN_EMAIL / AEGIS_ADMIN_PASSWORD)
  2. One ACTIVE tenant        "Test Fintech Pvt Ltd"       TEN-0001
     with a freshly generated API key (hash + encrypted copy for portal reveal),
     a webhook config (internal sink, HMAC secret), an LLM config, and the
     STANDARD_FINTECH ingestion schema preset.
  3. One TENANT_ADMIN         admin@testfintech.in         (override: AEGIS_TENANT_ADMIN_EMAIL / AEGIS_TENANT_ADMIN_PASSWORD)

The API key is printed ONCE at the end - copy it into your environment for
scripts/simulator_client.py. Re-running this script never regenerates an
existing key (rotate from the portal instead).

The schema must already exist (run `python clean_db_for_prod.py --yes` or
`python -m alembic upgrade head` first) - this script does NOT create tables.
"""
import os
import secrets
import sys

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.database import SessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.models.alert import Alert
from app.models.schema import IngestionSchema
from app.models.webhook import WebhookConfig
from app.models.llm_config import LLMConfig
from app.utils.security import (
    hash_password,
    hash_api_key,
    generate_api_key,
    encrypt_json,
)
from app.data.schema_presets import SCHEMA_PRESETS

ADMIN_EMAIL = os.environ.get("AEGIS_ADMIN_EMAIL", "admin@aegis-aml.com")
ADMIN_PASSWORD = os.environ.get("AEGIS_ADMIN_PASSWORD", "AegisAdmin2026!")
TENANT_ADMIN_EMAIL = os.environ.get("AEGIS_TENANT_ADMIN_EMAIL", "admin@testfintech.in")
TENANT_ADMIN_PASSWORD = os.environ.get("AEGIS_TENANT_ADMIN_PASSWORD", "TestFintech2026!")

TENANT_NAME = "Test Fintech Pvt Ltd"
TENANT_SLUG = "test-fintech"
TENANT_PUBLIC_ID = "TEN-0001"


def seed() -> int:
    db = SessionLocal()
    plaintext_key = None
    try:
        # Schema sanity: fail with a friendly message instead of a traceback
        try:
            db.execute(text("SELECT 1 FROM users LIMIT 1"))
        except (OperationalError, ProgrammingError):
            print("ERROR: tables do not exist yet.")
            print("Run:  python clean_db_for_prod.py --yes   (or: python -m alembic upgrade head)")
            return 2

        # -- 1. Super Admin --------------------------------------------
        admin = db.query(User).filter_by(email=ADMIN_EMAIL).first()
        if not admin:
            admin = User(
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                full_name="Aegis Super Admin",
                role="SUPER_ADMIN",
            )
            db.add(admin)
            db.commit()
            print(f"[+] Super Admin created: {ADMIN_EMAIL}")
        else:
            print(f"[=] Super Admin exists:  {ADMIN_EMAIL}")

        # -- 2. Test Fintech tenant (ACTIVE, real API key) -------------
        tenant = db.query(Tenant).filter_by(slug=TENANT_SLUG).first()
        if not tenant:
            plaintext_key = generate_api_key()
            tenant = Tenant(
                name=TENANT_NAME,
                slug=TENANT_SLUG,
                company_type="FINTECH",
                status="ACTIVE",
                api_key_hash=hash_api_key(plaintext_key),
                api_key_prefix=plaintext_key[:12],
                api_key_encrypted=encrypt_json(plaintext_key),
                tenant_id_public=TENANT_PUBLIC_ID,
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"[+] Tenant created:      {TENANT_NAME} ({TENANT_PUBLIC_ID})")
        else:
            print(f"[=] Tenant exists:       {TENANT_NAME} ({tenant.tenant_id_public}) - API key unchanged")

        # -- 3. Tenant Admin user --------------------------------------
        user = db.query(User).filter_by(email=TENANT_ADMIN_EMAIL).first()
        if not user:
            user = User(
                tenant_id=tenant.id,
                email=TENANT_ADMIN_EMAIL,
                password_hash=hash_password(TENANT_ADMIN_PASSWORD),
                full_name="Test Fintech Admin",
                designation="Compliance Officer",
                role="TENANT_ADMIN",
            )
            db.add(user)
            db.commit()
            print(f"[+] Tenant Admin created: {TENANT_ADMIN_EMAIL}")
        else:
            print(f"[=] Tenant Admin exists:  {TENANT_ADMIN_EMAIL}")

        # -- 4. Ingestion schema preset --------------------------------
        schema = db.query(IngestionSchema).filter_by(tenant_id=tenant.id).first()
        if not schema:
            preset = SCHEMA_PRESETS["STANDARD_FINTECH"]
            db.add(IngestionSchema(
                tenant_id=tenant.id,
                name=preset["name"],
                template_key="STANDARD_FINTECH",
                field_map=preset["field_map"],
                pii_fields=preset["pii_fields"],
            ))
            db.commit()
            print("[+] Ingestion schema:     STANDARD_FINTECH")
        else:
            print(f"[=] Ingestion schema:     {schema.template_key}")

        # -- 5. Webhook config (internal sink + HMAC secret) -----------
        if not db.query(WebhookConfig).filter_by(tenant_id=tenant.id).first():
            webhook_secret = secrets.token_hex(32)
            db.add(WebhookConfig(
                tenant_id=tenant.id,
                use_internal_sink=True,
                secret_hash=hash_api_key(webhook_secret),
                secret_encrypted=encrypt_json(webhook_secret),
                secret_prefix=webhook_secret[:12],
            ))
            db.commit()
            print("[+] Webhook config:       internal sink")

        # -- 6. LLM config ---------------------------------------------
        if not db.query(LLMConfig).filter_by(tenant_id=tenant.id).first():
            db.add(LLMConfig(
                tenant_id=tenant.id,
                provider="GROQ",
                model_name="llama-3.3-70b-versatile",
                sar_template_style="BOTH",
            ))
            db.commit()
            print("[+] LLM config:           GROQ / llama-3.3-70b-versatile")

        # -- 7. Assert zero dummy data ---------------------------------
        alert_count = db.query(Alert).count()
        if alert_count:
            print(f"[!] WARNING: {alert_count} alert(s) already in the DB - this seed never creates "
                  "alerts; run clean_db_for_prod.py for a true clean slate.")
        else:
            print("[=] Alerts table:         empty (use scripts/simulator_client.py to generate)")

        # -- Credentials summary ---------------------------------------
        print("\n" + "=" * 64)
        print("LOGIN CREDENTIALS")
        print("=" * 64)
        print(f"  Super Admin : {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"  Tenant Admin: {TENANT_ADMIN_EMAIL} / {TENANT_ADMIN_PASSWORD}")
        print(f"  Tenant ID   : {tenant.tenant_id_public}")
        if plaintext_key:
            print("\n  API KEY (shown ONCE - copy now, or reveal/rotate from the portal):")
            print(f"  {plaintext_key}")
            print("\n  For the simulator (PowerShell):")
            print(f"    $env:AEGIS_API_KEY = \"{plaintext_key}\"")
            print(f"    $env:AEGIS_TENANT_ID = \"{tenant.tenant_id_public}\"")
            print("    python scripts/simulator_client.py --scenario structuring --count 5")
        else:
            print("\n  API key: unchanged (reveal or rotate it from Settings -> Credentials)")
        print("=" * 64)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding minimal data ...")
    sys.exit(seed())
