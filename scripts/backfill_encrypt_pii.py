"""
One-time backfill: re-encrypt every PII-bearing row so nothing sensitive remains
as plaintext in Postgres.

Context: the at-rest encryption (app/models/encrypted_types.py) is legacy-tolerant —
rows written BEFORE the change stay readable as plaintext, and only NEW writes are
encrypted. That's great for zero-downtime rollout, but it means historical rows
(e.g. TEN-0005 / client_0 data created before 2026-07-05) still sit in cleartext.

This script loads and re-saves each such row through the ORM. Reading transparently
decrypts (or passes plaintext through); writing re-encrypts. It is IDEMPOTENT — a row
that's already encrypted just gets a fresh ciphertext, same plaintext. Run it once
after deploying the encryption change (and after setting PII_ENCRYPTION_KEY).

Usage (from repo root, backend venv):
    python scripts/backfill_encrypt_pii.py            # apply
    python scripts/backfill_encrypt_pii.py --dry-run  # count only, no writes
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from sqlalchemy.orm.attributes import flag_modified  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.alert import Alert  # noqa: E402
from app.models.sar import SARDraft  # noqa: E402
from app.models.pii_map import PIIMap  # noqa: E402
from app.models.webhook import WebhookSinkEvent  # noqa: E402

# (model, [encrypted attribute names]) — every column backed by EncryptedJSONB / EncryptedText.
TARGETS = [
    (Alert, ["raw_payload", "normalized_payload"]),
    (SARDraft, ["approved_text", "rehydrated_text"]),
    (PIIMap, ["token_map"]),
    (WebhookSinkEvent, ["payload"]),
]

BATCH = 500


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="count rows, write nothing")
    args = ap.parse_args()

    db = SessionLocal()
    total = 0
    try:
        for model, fields in TARGETS:
            rows = db.query(model).all()
            touched = 0
            for i, row in enumerate(rows, 1):
                changed = False
                for f in fields:
                    val = getattr(row, f)
                    if val is None:
                        continue
                    # Force a re-write so the bind param re-encrypts on flush.
                    flag_modified(row, f)
                    changed = True
                if changed:
                    touched += 1
                if not args.dry_run and i % BATCH == 0:
                    db.commit()
            if not args.dry_run:
                db.commit()
            total += touched
            print(f"{model.__tablename__:<22} rows={len(rows):>5}  re-encrypted={touched}"
                  + ("  (dry-run)" if args.dry_run else ""))
        print(f"\n{'Would re-encrypt' if args.dry_run else 'Re-encrypted'} {total} rows total.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
