import logging
import aiosqlite
import json
import uuid
import asyncio
from functools import wraps
from typing import List, Dict, Any, Optional
from core.db import get_db_connection, retry_on_db_lock
from core.config import VECTOR_DIMENSION, SQLITE_DB_PATH
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
        logger.warning(
            f"SQLite: Failed to parse JSON for field '{field_name}': {e}. Raw data: {data}"
        )
        return data  # Return raw as fallback or None depending on preference, returning raw for safety.


class SqliteStorage:
    """
    Simplified SQLite Storage Engine for LogicHive (Personal MVP).
    Direct local access, no multi-tenancy.
    """

    def __init__(self, db_path: str = SQLITE_DB_PATH):
        self.db_path = db_path
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
                        await history_manager.archive_version(
                            db, dict(full_existing_row)
                        )
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

    async def list_all_functions(self) -> List[Dict[str, Any]]:
        """
        Retrieves all functions from the database without filtering.
        Used for backup and export utilities.
        """
        try:
            db = await aiosqlite.connect(self.db_path)
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM logichive_functions")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"SQLite: Failed to list all functions: {e}")
            return []

    async def delete_function(self, name: str) -> bool:
        """
        Deletes a function from the database by name.
        """
        try:
            db = await get_db_connection()
            await db.execute("DELETE FROM logichive_functions WHERE name = ?", (name,))
            await db.commit()
            await db.close()
            logger.info(f"SQLite: Function '{name}' deleted.")
            return True
        except Exception as e:
            logger.error(f"SQLite: Failed to delete function '{name}': {e}")
            return False

    async def find_similar_functions(
        self,
        embedding: Optional[List[float]] = None,
        query_text: Optional[str] = None,
        tags: Optional[List[str]] = None,
        language: Optional[str] = None,
        limit: int = 5,
        match_threshold: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """
        Enhanced Hybrid Search: Combines Vector Similarity (FAISS) with SQL-based Keyword/Tag/Language matching.

        Args:
            embedding: Vector embedding for semantic search.
            query_text: Optional text for keyword/name/description matching.
            tags: Optional list of tags for strict filtering.
            language: Optional language for strict filtering (e.g., "python").
            limit: Maximum results to return.
            match_threshold: Minimum similarity score for vector results.
        """
        try:
            # 1. Initialize Vector Manager if needed
            if not vector_manager._initialized:
                db = await get_db_connection()
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT name, embedding FROM logichive_functions WHERE embedding IS NOT NULL"
                ) as cursor:
                    rows = [dict(r) for r in await cursor.fetchall()]
                await db.close()
                await vector_manager.ensure_initialized(rows)

            # 2. Perform vector search (Core semantic results)
            vector_matches = []
            if embedding and len(embedding) == VECTOR_DIMENSION:
                try:
                    vector_matches = await vector_manager.search(embedding, limit=limit * 5)
                except Exception as ve:
                    logger.warning(f"SQLite: Vector search failed, falling back to pure SQL: {ve}")
            else:
                logger.info("SQLite: Empty or invalid embedding, performing pure SQL/Tag search.")

            # 3. Perform SQL Keyword/Tag/Language Search (High-precision results)
            sql_results = {}
            if query_text or tags or language:
                db = await get_db_connection()
                db.row_factory = aiosqlite.Row

                conditions = []
                params = []

                # Handle #tag syntax in query_text
                if query_text and query_text.startswith("#"):
                    tag_from_text = query_text[1:].lower()
                    if not tags:
                        tags = [tag_from_text]
                    else:
                        tags.append(tag_from_text)
                    query_text = None

                # Keyword Match (Name or Description) - Support multi-word matching
                if query_text:
                    words = [w.strip() for w in query_text.split() if len(w.strip()) > 2]
                    if not words: # Fallback for very short queries
                        words = [query_text.strip()]
                    
                    word_conditions = []
                    for word in words:
                        word_conditions.append("(name LIKE ? OR description LIKE ?)")
                        term = f"%{word.lower()}%"
                        params.extend([term, term])
                    
                    if word_conditions:
                        conditions.append(f"({' OR '.join(word_conditions)})")

                # Tag Exact Match
                if tags:
                    for tag in tags:
                        conditions.append(
                            "EXISTS (SELECT 1 FROM json_each(tags) WHERE LOWER(value) = LOWER(?))"
                        )
                        params.append(tag)

                # Language Strict Match
                if language:
                    conditions.append("LOWER(language) = LOWER(?)")
                    params.append(language)

                if conditions:
                    where_clause = " AND ".join(conditions)
                    sql = f"SELECT * FROM logichive_functions WHERE {where_clause} LIMIT {limit * 3}"
                    logger.debug(f"SQLite: SQL Search: {sql} with {params}")
                    async with db.execute(sql, params) as cursor:
                        sql_rows = await cursor.fetchall()

                    for row in sql_rows:
                        processed = self._process_row(dict(row))
                        # Boost SQL hits: 0.9 for keyword, higher if exact name match
                        score = 0.9
                        if (
                            query_text
                            and processed["name"].lower() == query_text.lower()
                        ):
                            score = 1.0
                        processed["similarity"] = score
                        sql_results[processed["name"]] = processed

                await db.close()

            # 4. Hydrate and Merge
            # Priority: Combine Vector similarity with SQL boost
            final_results = sql_results  # Start with SQL results

            db = await get_db_connection()
            db.row_factory = aiosqlite.Row

            names_to_hydrate = []
            similarities = {}

            for name, similarity in vector_matches:
                if name in final_results:
                    # If already in SQL results, combine scores
                    final_results[name]["similarity"] = max(
                        final_results[name]["similarity"], similarity
                    )
                elif similarity >= match_threshold:
                    names_to_hydrate.append(name)
                    similarities[name] = similarity

            if names_to_hydrate:
                placeholders = ", ".join(["?"] * len(names_to_hydrate))
                # Apply language filter even to hydrated results if specified
                lang_clause = "AND LOWER(language) = LOWER(?)" if language else ""
                sql = f"SELECT * FROM logichive_functions WHERE name IN ({placeholders}) {lang_clause}"
                
                query_params = names_to_hydrate.copy()
                if language:
                    query_params.append(language)

                async with db.execute(sql, query_params) as cursor:
                    db_rows = await cursor.fetchall()
                    for db_row in db_rows:
                        res = self._process_row(dict(db_row))
                        name = res["name"]
                        res["similarity"] = similarities[name]
                        final_results[name] = res

            await db.close()

            # 5. Sort by combined similarity and limit
            sorted_results = sorted(
                final_results.values(), key=lambda x: x["similarity"], reverse=True
            )
            return sorted_results[:limit]

        except Exception as e:
            logger.error(f"SQLite: Hybrid search failed", exc_info=True)
            # Return detailed error if possible
            error_msg = f"{type(e).__name__}: {str(e)}"
            raise StorageError(f"Hybrid search failed: {error_msg}")

    def _process_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to parse JSON fields from a database row."""
        if not row:
            return None
        processed = dict(row)

        if "tags" in processed:
            processed["tags"] = _safe_json_loads(processed["tags"], "tags")
        if "test_metrics" in processed:
            processed["test_metrics"] = _safe_json_loads(
                processed["test_metrics"], "test_metrics"
            )
        if "embedding" in processed:
            processed["embedding"] = _safe_json_loads(
                processed["embedding"], "embedding"
            )
        if "dependencies" in processed:
            processed["dependencies"] = _safe_json_loads(
                processed["dependencies"], "dependencies"
            )

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
