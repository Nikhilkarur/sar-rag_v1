"""
ONE reset button for the RAG workspace.

Mock data lives under testing/ (regeneratable). Real client data lives under
production/ (starts empty). This tool wipes the 'mess' and can regenerate the
whole mock environment.

Usage (run from repo root):

  python scripts/reset.py
      WIPE runtime only:  outputs/ + all Chroma vector stores (repo + temp).
      testing/ and production/ data are KEPT. Safe + re-runnable any time.

  python scripts/reset.py --seed
      Wipe runtime, then REGENERATE the entire mock environment under testing/
      (policy PDF + demo input + client_0 eval config/alerts). Calls seed_testing.py.

  python scripts/reset.py --barebone
      Wipe runtime AND delete ALL mock data under testing/ (corpus, inputs,
      clients) — leaving testing/build_policy.py + testing/sources.md and the
      empty production/ tree. The 'pure barebone' state.

  python scripts/reset.py --barebone --seed
      Full wipe, then regenerate the mock environment from scratch (clean slate,
      fully reversible).

NEVER touches: backend/app source, scripts/, *.md docs, testing/build_policy.py,
production/ structure, or PostgreSQL (use backend/clear_db.py for SQL).
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


def wipe_testing_data():
    print("Removing ALL mock data under testing/ (barebone):")
    for pdf in glob.glob(os.path.join(ROOT, "testing", "corpus", "*.pdf")):
        _rm(pdf)
    for j in glob.glob(os.path.join(ROOT, "testing", "inputs", "*.json")):
        _rm(j)
    for d in glob.glob(os.path.join(ROOT, "testing", "clients", "*")):
        if os.path.isdir(d):
            _rm(d)


def seed():
    print("Regenerating the mock environment (testing/):")
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "seed_testing.py")], check=True)


def main():
    ap = argparse.ArgumentParser(description="Reset the RAG workspace.")
    ap.add_argument("--barebone", action="store_true",
                    help="also delete ALL mock data under testing/")
    ap.add_argument("--seed", action="store_true",
                    help="regenerate the whole mock environment after wiping")
    args = ap.parse_args()

    print("=" * 60)
    wipe_runtime()
    if args.barebone:
        wipe_testing_data()
    if args.seed:
        seed()
    print("=" * 60)
    if args.barebone and not args.seed:
        print("Done — PURE BAREBONE (mock data removed). Run with --seed to regenerate.")
    elif args.seed:
        print("Done — runtime cleared and mock environment regenerated under testing/.")
    else:
        print("Done — runtime cleared, mock data kept. Re-run any script to rebuild the store.")


if __name__ == "__main__":
    main()
