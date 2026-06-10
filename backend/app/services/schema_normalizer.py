from typing import Any, Dict

def get_nested_value(data: dict, path: str) -> Any:
    keys = path.split('.')
    current = data
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return None
    return current

def normalize_payload(raw_payload: dict, field_map: dict) -> dict:
    """
    Extract values from raw_payload using the dot-notation paths in field_map.
    """
    normalized = {}
    for standard_field, json_path in field_map.items():
        val = get_nested_value(raw_payload, json_path)
        normalized[standard_field] = val
        
    return normalized
