def verify_api_key(key: str):
    """Verifies an API key against the database."""
    conn = duckdb.connect(str(API_KEYS_DB_PATH), read_only=True)
    try:
        # Table must already exist. If not, select will fail.
        res = conn.execute("SELECT user_id FROM api_keys WHERE key = ?", [key]).fetchone()
        if res:
            return True, res[0]
        return False, None
    except Exception:
        # If table doesn't exist yet, it's not a valid key
        return False, None
    finally:
        conn.close()
