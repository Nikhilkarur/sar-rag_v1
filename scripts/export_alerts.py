"""
Export a client's alerts from Postgres (the source of truth) into their unified
per-client folder as JSON, so the offline RAGAS eval can score them.

Live alerts are stored in the `alerts` table (raw_payload JSONB), per tenant — we do
NOT mirror them to disk on ingest. This script pulls a sample on demand:

  backend/storage/clients/<public_id>/alerts/<alert_id>.json   ({"raw_payload": {...}})

Then run:  python eval/ragas_eval.py <public_id>

(The mock client_0 needs no export — its alerts are seeded offline by seed_testing.py.)

Run from repo root:
  python scripts/export_alerts.py TEN-0001                    # latest 20 alerts
  python scripts/export_alerts.py TEN-0001 --limit 1 --oldest # the client's 1st request
  python scripts/export_alerts.py TEN-0001 --limit 50         # latest 50
  python scripts/export_alerts.py TEN-0001 --all              # all alerts
  python scripts/export_alerts.py TEN-0001 --include-synthetic
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)  # load backend/.env (DB connection)

from app.database import SessionLocal                                   # noqa: E402
from app.models.tenant import Tenant                                    # noqa: E402
from app.models.alert import Alert                                      # noqa: E402
from app.services import client_storage                                 # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Export a client's alerts from the DB to their folder.")
    ap.add_argument("public_id", help="tenant public id, e.g. TEN-0001")
    ap.add_argument("--limit", type=int, default=20, help="how many alerts (default 20)")
    ap.add_argument("--all", action="store_true", help="export ALL alerts (ignores --limit)")
    ap.add_argument("--oldest", action="store_true",
                    help="take the EARLIEST alerts (e.g. the client's 1st request); default is most-recent")
    ap.add_argument("--include-synthetic", action="store_true",
                    help="also export portal-simulator (is_synthetic) alerts")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.tenant_id_public == args.public_id).first()
        if not tenant:
            print(f"No tenant with public id '{args.public_id}'. Seed the DB first.")
            return

        q = db.query(Alert).filter(Alert.tenant_id == tenant.id, Alert.is_deleted == False)  # noqa: E712
        if not args.include_synthetic:
            q = q.filter(Alert.is_synthetic == False)  # noqa: E712
        q = q.order_by(Alert.created_at.asc() if args.oldest else Alert.created_at.desc())
        if not args.all:
            q = q.limit(args.limit)
        alerts = q.all()

        if not alerts:
            print(f"No alerts found for {args.public_id} "
                  f"({'incl.' if args.include_synthetic else 'excl.'} synthetic). Nothing to export.")
            return

        out_dir = client_storage.alerts_dir(args.public_id)
        for a in alerts:
            path = client_storage.alert_path(args.public_id, str(a.id))
            # The live system already normalized + masked these with the tenant's OWN
            # schema (ingest.py). Export those alongside raw so the eval scores EXACTLY
            # what live produced — instead of re-normalizing raw with a guessed preset.
            record = {"raw_payload": a.raw_payload}
            if a.normalized_payload is not None:
                record["normalized_payload"] = a.normalized_payload
            if a.masked_payload is not None:
                record["masked_payload"] = a.masked_payload
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2, ensure_ascii=False, default=str)

        print(f"Exported {len(alerts)} alert(s) for {args.public_id} -> "
              f"{os.path.relpath(out_dir, ROOT)}")
        print(f"Now run:  python eval/ragas_eval.py {args.public_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
