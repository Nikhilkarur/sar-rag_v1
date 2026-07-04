"""Admin-dashboard data hygiene.

Two demo-cleanliness fixes that keep the super-admin console honest:

  1. Purge throwaway "Probe Fintech" tenants that scripts/verify_stack.py signs up on every
     run (they pile up as PENDING_VERIFICATION junk in the Verification Queue).
  2. Rename the legacy seed tenant TEN-0001 so it no longer collides with the real onboarded
     mock bank (TEN-0005), which is ALSO named "Meridian Bank Limited" — ambiguous everywhere
     in the admin views (Customers, Logs filter, LLM Usage).

Safe + idempotent: run it as often as you like.

    python scripts/admin_hygiene.py            # apply both fixes
    python scripts/admin_hygiene.py --dry-run  # show what would change, touch nothing
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)  # load backend/.env (DB connection)

from app.database import SessionLocal          # noqa: E402
from app.models.tenant import Tenant           # noqa: E402
from app.models.user import User               # noqa: E402

# The legacy seed tenant that shares a name with the real onboarded bank.
SEED_TENANT_PUBLIC_ID = "TEN-0001"
SEED_TENANT_NEW_NAME = "Test Fintech Pvt Ltd"
PROBE_NAME = "Probe Fintech"


def purge_probes(db, dry_run: bool) -> int:
    probes = db.query(Tenant).filter(Tenant.name == PROBE_NAME).all()
    if not probes:
        print("  [probes] none found — queue is clean.")
        return 0
    for t in probes:
        users = db.query(User).filter(User.tenant_id == t.id).all()
        emails = ", ".join(u.email for u in users) or "(no users)"
        print(f"  [probes] {'would delete' if dry_run else 'deleting'} {t.name} "
              f"({t.status}) - {emails}")
        if not dry_run:
            # Users aren't ON DELETE CASCADE from tenants, so remove them explicitly first.
            for u in users:
                db.delete(u)
            db.delete(t)  # alerts/matches/etc. are ON DELETE CASCADE
    return len(probes)


def rename_seed(db, dry_run: bool) -> bool:
    seed = db.query(Tenant).filter(Tenant.tenant_id_public == SEED_TENANT_PUBLIC_ID).first()
    if not seed:
        print(f"  [rename] {SEED_TENANT_PUBLIC_ID} not found — skipping.")
        return False
    if seed.name == SEED_TENANT_NEW_NAME:
        print(f"  [rename] {SEED_TENANT_PUBLIC_ID} already named '{SEED_TENANT_NEW_NAME}'.")
        return False
    print(f"  [rename] {'would rename' if dry_run else 'renaming'} {SEED_TENANT_PUBLIC_ID}: "
          f"'{seed.name}' -> '{SEED_TENANT_NEW_NAME}'")
    if not dry_run:
        seed.name = SEED_TENANT_NEW_NAME
    return True


def main():
    ap = argparse.ArgumentParser(description="Admin dashboard data hygiene")
    ap.add_argument("--dry-run", action="store_true", help="show changes without applying")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        print("== Admin hygiene ==")
        n = purge_probes(db, args.dry_run)
        renamed = rename_seed(db, args.dry_run)
        if not args.dry_run and (n or renamed):
            db.commit()
            print(f"Done: purged {n} probe tenant(s), rename {'applied' if renamed else 'not needed'}.")
        elif args.dry_run:
            print("Dry run — nothing committed.")
        else:
            print("Nothing to do.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
