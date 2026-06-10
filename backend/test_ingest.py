import httpx
import json
import uuid
import datetime

url = "http://localhost:8000/api/v1/ingest/"
headers = {
    "X-Tenant-ID": "TEN-DEMO",
    "X-Api-Key": "sk-ae-demo",
    "Content-Type": "application/json"
}

payload = {
    "customer": {
        "full_name": "Rohan Gupta",
        "id": "CUST-99212"
    },
    "account": {
        "number": "00098172635"
    },
    "txn": {
        "ref_id": str(uuid.uuid4()),
        "amount": 950000,
        "currency": "INR",
        "type": "CASH_DEPOSIT",
        "direction": "CREDIT",
        "timestamp": datetime.datetime.now().isoformat()
    },
    "counterparty": {
        "account": "N/A",
        "name": "N/A",
        "bank": "Self"
    },
    "metadata": {
        "ip": "103.45.92.1",
        "device_id": "DEV-77631"
    },
    "risk": {
        "score": 60,
        "reason": "High value cash deposit"
    }
}

print("Triggering ingest...")
response = httpx.post(url, headers=headers, json=payload)
print(f"Status Code: {response.status_code}")
print("Response Body:")
print(json.dumps(response.json(), indent=2))
