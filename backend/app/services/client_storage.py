"""
Per-client storage layout — ONE folder per client holds everything for that client.

  backend/storage/clients/<client_id>/
  ├── policy.pdf            # the client's uploaded AML policy (raw file)
  ├── alerts/<alert_id>.json  # every transaction request we received (logged record)
  ├── sar/<sar_id>.pdf      # the SAR PDFs we generated
  └── eval.json             # (optional) answer key for IR eval (rule -> section)

<client_id> is the tenant's public id (e.g. TEN-0001) for real clients, or "client_0"
for the synthetic mock client. The IR/RAGAS eval reads these same folders, so whatever
we do for testing we do for production.
"""
import json
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


def log_alert(client_id: str, alert_id: str, record: dict) -> None:
    """Save a received transaction request as a JSON record (best-effort)."""
    try:
        with open(alert_path(client_id, alert_id), "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False, default=str)
    except Exception:
        pass
