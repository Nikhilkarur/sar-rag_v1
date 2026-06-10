SCHEMA_PRESETS = {
    "STANDARD_FINTECH": {
        "name": "Standard Fintech Transaction Alert",
        "field_map": {
            "customer_name": "customer.full_name",
            "customer_id": "customer.id",
            "account_id": "account.number",
            "transaction_id": "txn.ref_id",
            "transaction_amount": "txn.amount",
            "transaction_currency": "txn.currency",
            "transaction_type": "txn.type",
            "transaction_direction": "txn.direction",
            "transaction_timestamp": "txn.timestamp",
            "counterparty_account": "counterparty.account",
            "counterparty_name": "counterparty.name",
            "counterparty_institution": "counterparty.bank",
            "ip_address": "metadata.ip",
            "device_id": "metadata.device_id",
            "risk_score": "risk.score",
            "alert_reason": "risk.reason"
        },
        "pii_fields": [
            "customer_name", 
            "customer_id", 
            "account_id", 
            "counterparty_account",
            "counterparty_name", 
            "ip_address", 
            "device_id"
        ]
    },
    "SEBI_BROKER": {
        "name": "SEBI Stock Broker Trading Alert",
        "field_map": {
            "customer_name": "client.name",
            "customer_id": "client.pan",
            "account_id": "demat.account_id",
            "transaction_amount": "trade.value",
            "transaction_currency": "trade.currency",
            "transaction_type": "trade.type",
            "transaction_timestamp": "trade.timestamp",
            "risk_score": "risk.score",
            "alert_reason": "risk.reason"
        },
        "pii_fields": [
            "customer_name", 
            "customer_id", 
            "account_id"
        ]
    },
    "PAYMENT_GW": {
        "name": "Payment Gateway Alert",
        "field_map": {
            "customer_name": "payer.name",
            "customer_id": "payer.vpa",
            "account_id": "payer.account",
            "transaction_amount": "txn.amount",
            "transaction_currency": "txn.currency",
            "transaction_type": "txn.method",
            "transaction_timestamp": "txn.timestamp",
            "risk_score": "risk.score",
            "alert_reason": "risk.reason"
        },
        "pii_fields": [
            "customer_name", 
            "customer_id", 
            "account_id"
        ]
    }
}
