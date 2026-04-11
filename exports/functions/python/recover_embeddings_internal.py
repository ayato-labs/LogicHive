def recover_embeddings_internal(conn):
    try:
        current_model = embedding_service.model_name
        expected_dim = embedding_service.get_model_info()["dimension"]
        rows = conn.execute(
            """
            SELECT f.name, f.description, f.tags, f.metadata, f.code
            FROM functions f
            LEFT JOIN embeddings e ON f.name = e.function_name
            WHERE e.model_name != ? OR e.dimension != ? OR e.function_name IS NULL
        """,
            (current_model, expected_dim),
        ).fetchall()
        for row in rows:
            name, desc, tags_j, meta_j, code = row
            tags = json.loads(tags_j) if tags_j else []
            meta = json.loads(meta_j) if meta_j else {}
            deps = meta.get("dependencies", [])
            from core.consolidation import LogicIntelligence
            intel = LogicIntelligence()
            text = intel.construct_search_document(name, desc, tags, code)
            emb = embedding_service.get_embedding(text)
            conn.execute(
                """
                INSERT OR REPLACE INTO embeddings (function_name, vector, model_name, dimension, encoded_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (name, emb, current_model, len(emb)),
            )
        conn.commit()
    except Exception as e:
        logger.error(
            f"Recovery failed (recover_embeddings_internal): {e}", exc_info=True
        )
