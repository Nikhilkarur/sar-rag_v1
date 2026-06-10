import hashlib
import re

def generate_token(value: str, field_name: str) -> str:
    """Generate a deterministic token based on the field type and value."""
    if not value:
        return value
        
    hash_str = hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:8]
    
    if field_name in ["customer_name", "counterparty_name"]:
        prefix = "USR_"
    elif field_name in ["account_id", "counterparty_account"]:
        prefix = "ACC_"
    elif field_name == "ip_address":
        prefix = "IP_"
    elif field_name == "device_id":
        prefix = "DEV_"
    elif field_name == "customer_id":
        prefix = "CID_"
    else:
        prefix = "TOK_"
        
    return f"{prefix}{hash_str}"

def mask_payload(normalized: dict, pii_fields: list) -> tuple[dict, dict]:
    """
    Mask PII fields in the normalized payload.
    Returns: (masked_payload, token_map)
    """
    masked = normalized.copy()
    token_map = {}
    
    for field in pii_fields:
        val = masked.get(field)
        if val is not None:
            token = generate_token(val, field)
            masked[field] = token
            token_map[token] = str(val)
            
    return masked, token_map

def rehydrate_text(text: str, token_map: dict) -> str:
    """
    Replace tokens in text with their original values.
    """
    if not text:
        return text
        
    rehydrated = text
    for token, original_value in token_map.items():
        rehydrated = rehydrated.replace(token, original_value)
        
    return rehydrated
