def _safe_json_loads(data: Any, field_name: str) -> Any:
    """Helper to safely parse JSON strings and log errors."""
    if not data:
        return data
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.warning(f"SQLite: Failed to parse JSON for field '{field_name}': {e}. Raw data: {data}")
        return data  # Return raw as fallback or None depending on preference, returning raw for safety.