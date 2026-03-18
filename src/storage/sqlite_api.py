import logging
import aiosqlite
import json
import uuid
import asyncio
from functools import wraps
from typing import List, Dict, Any, Optional
from core.db import get_db_connection, retry_on_db_lock
from core.exceptions import StorageError

from storage.vector_store import vector_manager
from storage.history_manager import history_manager

logger = logging.getLogger(__name__)

def with_write_lock(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        async with self._lock:
            return await func(self, *args, **kwargs)
    return wrapper

def _safe_json_loads(data: Any, field_name: str) -> Any:
    """Helper to safely parse JSON strings and log errors."""
    if not data:
        return data
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.warning(f"SQLite: Failed to parse JSON for field '{field_name}': {e}. Raw data: {data}")
        return data  # Return raw as fallback or None depending on preference, returning raw for safety.

class SqliteStorage:
    """
    Simplified SQLite Storage Engine for LogicHive (Personal MVP).
    Direct local access, no multi-tenancy.
    """

    def __init__(self):
        self._db_path = None
        self._lock = asyncio.Lock()

    @retry_on_db_lock()
    @with_write_lock
    async def upsert_function(self, function_data: Dict[str, Any]) -> bool:
        """
        Inserts or updates a function.
        """
        try:
            db = await get_db_connection()
            db.row_factory = aiosqlite.Row

            # 1. Check if name exists to handle versioning
            async with db.execute(
                "SELECT id, code, code_hash, version FROM logichive_functions WHERE name = ?",
                (function_data["name"],),
            ) as cursor:
                row = await cursor.fetchone()
                existing = dict(row) if row else None

            row_id = str(uuid.uuid4())
            new_version = 1

            if existing:
                # If code has changed, archive the old version
                if existing["code_hash"] != function_data["code_hash"]:
                    new_version = existing["version"] + 1

                    # Get full details of existing to archive
                    async with db.execute(
                        "SELECT * FROM logichive_functions WHERE name = ?",
                        (function_data["name"],),
                    ) as cursor:
                        full_existing_row = await cursor.fetchone()
                        
                    if full_existing_row:
                        await history_manager.archive_version(db, dict(full_existing_row))
                else:
                    # Unchanged code, we can just return or perform a stay-put update
                    await db.close()
                    return True

            data = (
                existing["id"] if existing else row_id,
                function_data["name"],
                function_data["code"],
                function_data.get("description", ""),
                function_data.get("language", "python"),
                json.dumps(function_data.get("tags", [])),
                function_data.get("reliability_score", 1.0),
                json.dumps(function_data.get("test_metrics", {})),
                json.dumps(function_data["embedding"])
                if "embedding" in function_data
                else None,
                function_data.get("code_hash"),
                new_version,
                json.dumps(function_data.get("dependencies", [])),
                function_data.get("test_code", ""),
            )

            await db.execute(
                """
                INSERT OR REPLACE INTO logichive_functions 
                (id, name, code, description, language, tags, reliability_score, test_metrics, embedding, code_hash, version, dependencies, test_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                data,
            )

            await db.commit()
            await db.close()

            # Incremental FAISS update
            if "embedding" in function_data:
                await vector_manager.add_vector(
                    function_data["name"], function_data["embedding"]
                )

            logger.info(
                f"SQLite: Successfully saved version {new_version} of function '{function_data['name']}'"
            )
            return True
        except Exception as e:
            logger.error(f"SQLite: Failed to save function: {e}")
            raise StorageError(f"Database upsert failed: {e}")

    async def find_similar_functions(
        self,
        embedding: List[float],
        query_text: Optional[str] = None,
        limit: int = 5,
        match_threshold: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid Search: Combines Vector Similarity (FAISS) with SQL-based Exact/Keyword matching.
        """
        try:
            # 1. Initialize Vector Manager if needed
            if not vector_manager._initialized:
                db = await get_db_connection()
                db.row_factory = lambda cursor, row: dict(
                    zip([col[0] for col in cursor.description], row)
                )
                async with db.execute(
                    "SELECT name, embedding FROM logichive_functions WHERE embedding IS NOT NULL"
                ) as cursor:
                    rows = await cursor.fetchall()
                await db.close()
                await vector_manager.ensure_initialized(rows)

            # 2. Perform vector search (Core semantic results)
            vector_matches = await vector_manager.search(embedding, limit=limit * 2)

            # 3. Perform SQL Keyword/Tag Search (High-precision results)
            sql_results = []
            if query_text:
                db = await get_db_connection()
                db.row_factory = lambda cursor, row: dict(
                    zip([col[0] for col in cursor.description], row)
                )

                # Keyword Match (Name) or Tag Match (#tag syntax)
                search_term = query_text.lower()
                is_tag_search = search_term.startswith("#")
                
                if is_tag_search:
                    tag_to_find = search_term[1:]
                    # Check if the tag exists in the JSON array of tags
                    sql = """
                    SELECT * FROM logichive_functions 
                    WHERE EXISTS (
                        SELECT 1 FROM json_each(tags) WHERE value = ?
                    )
                    LIMIT ?
                    """
                    params = (tag_to_find, limit)
                else:
                    sql = "SELECT * FROM logichive_functions WHERE name LIKE ? LIMIT ?"
                    params = (f"%{search_term}%", limit)

                async with db.execute(sql, params) as cursor:
                    sql_rows = await cursor.fetchall()
                
                for row in sql_rows:
                    processed = self._process_row(row)
                    # Boost SQL hits to ensure they appear high in results if direct match
                    processed["similarity"] = 1.0 if not is_tag_search else 0.95 
                    sql_results.append(processed)
                await db.close()

            # 4. Hydrate and Merge
            # Priority: Existing name in sql_results > FAISS result
            final_results = {r["name"]: r for r in sql_results}
            
            db = await get_db_connection()
            db.row_factory = lambda cursor, row: dict(
                zip([col[0] for col in cursor.description], row)
            )

            names_to_hydrate = []
            similarities = {}
            for name, similarity in vector_matches:
                if name in final_results:
                    # Update similarity to be combined/max if already found
                    final_results[name]["similarity"] = max(final_results[name]["similarity"], similarity)
                elif similarity >= match_threshold:
                    if name in similarities:
                        similarities[name] = max(similarities[name], similarity)
                    else:
                        names_to_hydrate.append(name)
                        similarities[name] = similarity

            if names_to_hydrate:
                placeholders = ", ".join(["?"] * len(names_to_hydrate))
                sql = f"SELECT id, name, description, language, tags, reliability_score FROM logichive_functions WHERE name IN ({placeholders})"
                async with db.execute(sql, names_to_hydrate) as cursor:
                    db_rows = await cursor.fetchall()
                    for db_row in db_rows:
                        res = self._process_row(db_row)
                        name = res["name"]
                        res["similarity"] = similarities[name]
                        final_results[name] = res

            await db.close()
            
            # 5. Sort by combined similarity and limit
            sorted_results = sorted(final_results.values(), key=lambda x: x["similarity"], reverse=True)
            return sorted_results[:limit]

        except Exception as e:
            logger.error(f"SQLite: Hybrid search failed: {e}")
            raise StorageError(f"Hybrid search failed: {e}")

    def _process_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to parse JSON fields from a database row."""
        if not row:
            return None
        processed = dict(row)
        
        if "tags" in processed:
            processed["tags"] = _safe_json_loads(processed["tags"], "tags")
        if "test_metrics" in processed:
            processed["test_metrics"] = _safe_json_loads(processed["test_metrics"], "test_metrics")
        if "embedding" in processed:
            processed["embedding"] = _safe_json_loads(processed["embedding"], "embedding")
        if "dependencies" in processed:
            processed["dependencies"] = _safe_json_loads(processed["dependencies"], "dependencies")

        return processed

    async def get_function_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            db = await get_db_connection()
            db.row_factory = lambda cursor, row: dict(
                zip([col[0] for col in cursor.description], row)
            )
            async with db.execute(
                "SELECT * FROM logichive_functions WHERE name = ?",
                (name,),
            ) as cursor:
                row = await cursor.fetchone()
            await db.close()
            return self._process_row(row)
        except Exception as e:
            logger.error(f"SQLite: Failed to get function '{name}': {e}")
            return None

    async def get_all_functions(self) -> List[Dict[str, Any]]:
        try:
            db = await get_db_connection()
            db.row_factory = lambda cursor, row: dict(
                zip([col[0] for col in cursor.description], row)
            )
            async with db.execute("SELECT * FROM logichive_functions") as cursor:
                rows = await cursor.fetchall()
            await db.close()
            return [self._process_row(row) for row in rows]
        except Exception as e:
            logger.error(f"SQLite: Failed to list all functions: {e}")
            raise StorageError(f"Failed to list all functions: {e}")

    @retry_on_db_lock()
    @with_write_lock
    async def increment_call_count(self, name: str) -> bool:
        try:
            db = await get_db_connection()
            await db.execute(
                "UPDATE logichive_functions SET call_count = call_count + 1 WHERE name = ?",
                (name,),
            )
            await db.commit()
            await db.close()
            return True
        except Exception as e:
            logger.error(f"SQLite: Increment failed for '{name}': {e}")
            raise StorageError(f"Failed to increment call count for '{name}': {e}")


# Singleton instance
sqlite_storage = SqliteStorage()
