"""Permanently delete a tenant and ALL of its history.

Removes the tenant row; every child table (alerts, sar_drafts, compliance_matches, users,
llm_configs, webhooks, api_logs, audit, pii_map, schemas, deliveries) is ON DELETE CASCADE
from tenants.id, so a single delete cleaves no orphans. IRREVERSIBLE.

    python scripts/delete_tenant.py TEN-0001            # dry-run: show what would be deleted
    python scripts/delete_tenant.py TEN-0001 --confirm  # actually delete

Refuses to touch the live demo bank (TEN-0005) unless you pass --force, to prevent fat-fingering.
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)  # load backend/.env (DB connection)

from sqlalchemy import func                       # noqa: E402
from app.database import SessionLocal             # noqa: E402
from app.models.tenant import Tenant              # noqa: E402
from app.models.user import User                  # noqa: E402
from app.models.alert import Alert                # noqa: E402
from app.models.sar import SARDraft               # noqa: E402
from app.models.compliance import ComplianceMatch # noqa: E402
from app.models.api_log import APILog             # noqa: E402

PROTECTED = {"TEN-0005"}  # the live demo bank — guard against accidental deletion


def main():
    ap = argparse.ArgumentParser(description="Delete a tenant and all its history")
    ap.add_argument("tenant_public_id", help="e.g. TEN-0001")
    ap.add_argument("--confirm", action="store_true", help="actually delete (default is dry-run)")
    ap.add_argument("--force", action="store_true", help="allow deleting a PROTECTED tenant")
    args = ap.parse_args()

    tid_public = args.tenant_public_id
    if tid_public in PROTECTED and not args.force:
        print(f"REFUSING to delete protected tenant {tid_public} without --force.")
        sys.exit(2)

    db = SessionLocal()
    try:
        t = db.query(Tenant).filter(Tenant.tenant_id_public == tid_public).first()
        if not t:
            print(f"Tenant {tid_public} not found — nothing to do.")
            return

        counts = {
            "users": db.query(func.count(User.id)).filter(User.tenant_id == t.id).scalar(),
            "alerts": db.query(func.count(Alert.id)).filter(Alert.tenant_id == t.id).scalar(),
            "sar_drafts": db.query(func.count(SARDraft.id)).filter(SARDraft.tenant_id == t.id).scalar(),
            "compliance_matches": db.query(func.count(ComplianceMatch.id)).filter(ComplianceMatch.tenant_id == t.id).scalar(),
            "api_logs": db.query(func.count(APILog.id)).filter(APILog.tenant_id == t.id).scalar(),
        }
        print(f"== Tenant {tid_public}: {t.name} (status {t.status}) ==")
        for k, v in counts.items():
            print(f"  {k:20} {v}")
        total_children = sum(counts.values())

        if not args.confirm:
            print(f"\nDRY RUN — would delete this tenant + {total_children} child rows (cascade). "
                  f"Re-run with --confirm to apply.")
            return

        db.delete(t)  # cascades to all child tables
        db.commit()
        print(f"\nDeleted tenant {tid_public} and {total_children} child rows.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
