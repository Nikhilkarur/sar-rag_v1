"""
ONE reset button for the RAG workspace.

All per-client data (mock client_0 AND real TEN-xxxx) lives in the unified store
backend/storage/clients/<client_id>/ (policy.pdf, alerts/, sar/, eval.json). The
mock client_0 is regeneratable from scripts/seed_testing.py.

Usage (run from repo root):

  python scripts/reset.py
      WIPE runtime only:  outputs/ + all Chroma vector stores (repo + temp).
      Per-client data in backend/storage/clients/ is KEPT. Safe + re-runnable.

  python scripts/reset.py --seed
      Wipe runtime, then REGENERATE the mock client_0 under
      backend/storage/clients/client_0/ (policy.pdf + alerts + eval.json).
      Calls seed_testing.py.

  python scripts/reset.py --barebone
      Wipe runtime AND delete the dummy client_0. REAL clients are KEPT (safe default).

  python scripts/reset.py --barebone --seed
      Full wipe of client_0, then regenerate it from scratch (clean slate).

  python scripts/reset.py --barebone --all-clients
      DANGER: delete EVERY client folder, including REAL clients' uploaded policy.pdf
      and generated SARs. (Their DB rows + Chroma collections survive.)

NEVER touches: backend/app source, scripts/, *.md docs, or PostgreSQL
(use backend/clear_db.py for SQL).
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rm(path):
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
        print(f"  removed dir   {os.path.relpath(path, ROOT)}")
    elif os.path.isfile(path):
        os.remove(path)
        print(f"  removed file  {os.path.relpath(path, ROOT)}")


def wipe_runtime():
    print("Wiping runtime artifacts (outputs + Chroma stores):")
    _rm(os.path.join(ROOT, "outputs"))
    _rm(os.path.join(ROOT, "chroma_data"))
    _rm(os.path.join(ROOT, "backend", "chroma_data"))
    for d in glob.glob(os.path.join(tempfile.gettempdir(), "chroma_*")):
        _rm(d)


def wipe_client_data(all_clients=False):
    clients_root = os.path.join(ROOT, "backend", "storage", "clients")
    if all_clients:
        # DANGER: removes REAL clients' uploaded policy.pdf + generated SARs too.
        print("Removing ALL client data under backend/storage/clients/ (mock AND real):")
        for d in glob.glob(os.path.join(clients_root, "*")):
            if os.path.isdir(d):
                _rm(d)
    else:
        # Safe default: only the regeneratable dummy. Real clients are left untouched.
        print("Removing the dummy client_0 only (real clients are KEPT):")
        _rm(os.path.join(clients_root, "client_0"))


def seed():
    print("Regenerating mock client_0 (backend/storage/clients/client_0/):")
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "seed_testing.py")], check=True)


def main():
    ap = argparse.ArgumentParser(description="Reset the RAG workspace.")
    ap.add_argument("--barebone", action="store_true",
                    help="also delete the dummy client_0 (real clients KEPT)")
    ap.add_argument("--all-clients", action="store_true",
                    help="with --barebone: delete EVERY client folder incl. REAL clients' policies")
    ap.add_argument("--seed", action="store_true",
                    help="regenerate client_0 after wiping")
    args = ap.parse_args()

    if args.all_clients and not args.barebone:
        ap.error("--all-clients only applies together with --barebone")

    print("=" * 60)
    wipe_runtime()
    if args.barebone:
        wipe_client_data(all_clients=args.all_clients)
    if args.seed:
        seed()
    print("=" * 60)
    if args.barebone and not args.seed:
        scope = "ALL clients" if args.all_clients else "client_0"
        print(f"Done — PURE BAREBONE ({scope} removed). Run with --seed to regenerate client_0.")
    elif args.seed:
        print("Done — runtime cleared and mock client_0 regenerated under backend/storage/clients/.")
    else:
        print("Done — runtime cleared, client data kept. Re-run any script to rebuild the store.")


if __name__ == "__main__":
    main()
