def init_db():
    with DBWriteLock():
        conn = get_db_connection()
        try:
            conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_emb_id START 1")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS functions (
                    name VARCHAR PRIMARY KEY,
                    code VARCHAR,
                    description VARCHAR,
                    tags VARCHAR,
                    metadata VARCHAR,
                    status VARCHAR DEFAULT 'active',
                    test_cases VARCHAR,
                    call_count INTEGER DEFAULT 0,
                    last_called_at VARCHAR,
                    created_at VARCHAR,
                    updated_at VARCHAR
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY DEFAULT nextval('seq_emb_id'),
                    function_name VARCHAR,
                    vector FLOAT[],
                    model_name VARCHAR,
                    dimension INTEGER,
                    encoded_at VARCHAR
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key VARCHAR PRIMARY KEY,
                    value VARCHAR
                )
            """)

            # Simple migration for embeddings if needed
            columns_res = conn.execute("DESCRIBE embeddings").fetchall()
            cols = [r[0] for r in columns_res]
            if "function_id" in cols and "function_name" not in cols:
                conn.execute("ALTER TABLE embeddings ADD COLUMN function_name VARCHAR")

            _check_model_version_internal(conn)
            recover_embeddings_internal(conn)
        finally:
            conn.close()
