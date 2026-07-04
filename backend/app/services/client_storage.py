"""
Per-client storage layout — ONE folder per client.

  backend/storage/clients/<client_id>/
  ├── policy.pdf            # the client's uploaded AML policy (raw file) — the ONLY live artifact
  ├── alerts/<alert_id>.json  # OFFLINE eval only: written by scripts/export_alerts.py, never by ingest
  ├── sar/<sar_id>.pdf      # OFFLINE demo only: written by scripts/*  (live SAR PDFs are
  │                         #   rendered in-memory and never persisted — they carry real PII)
  └── eval.json             # (optional) answer key for IR eval (rule -> section)

<client_id> is the tenant's public id (e.g. TEN-0005) for real clients, or "client_0"
for the synthetic mock client. LIVE data flow: alerts live ONLY in Postgres (alerts
table); this folder is the policy store + the offline eval/demo workspace.
"""
import os

_BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLIENTS_ROOT = os.path.join(_BACKEND, "storage", "clients")


def client_dir(client_id: str) -> str:
    d = os.path.join(CLIENTS_ROOT, str(client_id))
    os.makedirs(d, exist_ok=True)
    return d


def policy_path(client_id: str) -> str:
    return os.path.join(client_dir(client_id), "policy.pdf")


def alerts_dir(client_id: str) -> str:
    d = os.path.join(client_dir(client_id), "alerts")
    os.makedirs(d, exist_ok=True)
    return d


def alert_path(client_id: str, alert_id: str) -> str:
    return os.path.join(alerts_dir(client_id), f"{alert_id}.json")


def sar_dir(client_id: str) -> str:
    d = os.path.join(client_dir(client_id), "sar")
    os.makedirs(d, exist_ok=True)
    return d


def sar_path(client_id: str, sar_id: str) -> str:
    return os.path.join(sar_dir(client_id), f"{sar_id}.pdf")


def eval_config_path(client_id: str) -> str:
    return os.path.join(client_dir(client_id), "eval.json")
