import asyncio
import json
import logging
import uuid
from functools import wraps
from typing import Any

import aiosqlite

from core.config import SQLITE_DB_PATH, VECTOR_DIMENSION
from core.db import get_db_connection, retry_on_db_lock
from core.exceptions import StorageError
from storage.history_manager import history_manager
from storage.vector_store import vector_manager

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
    async def upsert_function(self, function_data: dict[str, Any]) -> bool:
        """
        Inserts or updates a function.
        """
        try:
            db = await get_db_connection()
            db.row_factory = aiosqlite.Row

            project = function_data.get("project", "default")
            name = function_data["name"]

            # 1. Check if name exists in specific project to handle versioning
            async with db.execute(
                "SELECT id, code, code_hash, version FROM logichive_functions WHERE project = ? AND name = ?",
                (project, name),
            ) as cursor:
                row = await cursor.fetchone()
                existing = dict(row) if row else None

            row_id = str(uuid.uuid4())
            new_version = 1

            if existing:
                # Case A: Code changed -> Increment version and archive old
                if existing["code_hash"] != function_data.get("code_hash"):
                    new_version = (existing.get("version") or 0) + 1

                    # Get full details of existing to archive
                    async with db.execute(
                        "SELECT * FROM logichive_functions WHERE project = ? AND name = ?",
                        (project, name),
                    ) as cursor:
                        full_existing_row = await cursor.fetchone()

                    if full_existing_row:
                        await history_manager.archive_version(
                            db, dict(full_existing_row)
                        )
                else:
                    # Case B: Code same, but metadata (description, score, etc.) might have changed
                    # Keep same ID and version
                    row_id = existing["id"]
                    new_version = existing["version"]
                    logger.debug(f"SQLite: In-place update for '{name}' (same code_hash)")

            data = (
                row_id if not existing else existing["id"],
                project,
                name,
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
                json.dumps(function_data.get("env_fingerprint", {})) if function_data.get("env_fingerprint") else None,
            )

            await db.execute(
                """
                INSERT OR REPLACE INTO logichive_functions 
                (id, project, name, code, description, language, tags, reliability_score, test_metrics, embedding, code_hash, version, dependencies, test_code, env_fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                data,
            )

            await db.commit()
            await db.close()

            # Incremental FAISS update
            if "embedding" in function_data:
                await vector_manager.add_vector(
                    name, function_data["embedding"], project=project
                )

            logger.info(
                f"SQLite: Successfully saved version {new_version} of function '{name}' in project '{project}'"
            )
            return True
        except Exception as e:
            logger.error(f"SQLite: Failed to save function: {e}")
            raise StorageError(f"Database upsert failed: {e}")

    async def list_all_functions(self) -> list[dict[str, Any]]:
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

    async def delete_function(self, name: str, project: str = "default") -> bool:
        """
        Deletes a function from the database by project and name.
        """
        try:
            db = await get_db_connection()
            await db.execute(
                "DELETE FROM logichive_functions WHERE project = ? AND name = ?",
                (project, name),
            )
            await db.commit()
            await db.close()
            logger.info(f"SQLite: Function '{name}' in project '{project}' deleted.")
            return True
        except Exception as e:
            logger.error(
                f"SQLite: Failed to delete function '{name}' in project '{project}': {e}"
            )
            return False

    async def find_similar_functions(
        self,
        embedding: list[float] = None,
        limit: int = 5,
        query_text: str = None,
        tags: list[str] = None,
        language: str = None,
        project: str = None,
        include_code: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Hybrid search combining FAISS vector search and SQLite keyword/tag filtering.
        """
        try:
            async with self._lock:
                # 1. Initialize Vector Manager if needed
                if not vector_manager._initialized:
                    db = await get_db_connection()
                    db.row_factory = aiosqlite.Row
                    async with db.execute(
                        "SELECT name, embedding, project FROM logichive_functions WHERE embedding IS NOT NULL"
                    ) as cursor:
                        rows = [dict(r) for r in await cursor.fetchall()]
                    await db.close()
                    await vector_manager.ensure_initialized(rows)

                # 2. Perform vector search (Core semantic results)
                vector_matches = []
                if embedding and len(embedding) == VECTOR_DIMENSION:
                    try:
                        vector_matches = await vector_manager.search(
                            embedding, limit=limit, project=project
                        )
                    except Exception as ve:
                        logger.warning(
                            f"SQLite: Vector search failed, falling back to pure SQL: {ve}"
                        )

                # 3. Perform SQL Keyword/Tag/Language Search (High-precision results)
                sql_results = {}
                select_fields = "name, description, language, tags, reliability_score, project, version, created_at, updated_at"
                if include_code:
                    select_fields = "*"

                if query_text or tags or language or project:
                    db = await get_db_connection()
                    db.row_factory = aiosqlite.Row

                    conditions = []
                    params = []

                    if query_text and query_text.startswith("#"):
                        tag_from_text = query_text[1:].lower()
                        if not tags:
                            tags = [tag_from_text]
                        else:
                            tags.append(tag_from_text)
                        query_text = None

                    if query_text:
                        words = [w.strip() for w in query_text.split() if len(w.strip()) > 2]
                        if not words:
                            words = [query_text.strip()]
                        word_conditions = ["(name LIKE ? OR description LIKE ?)"] * len(words)
                        for word in words:
                            term = f"%{word.lower()}%"
                            params.extend([term, term])
                        conditions.append(f"({' OR '.join(word_conditions)})")

                    if tags:
                        for tag in tags:
                            conditions.append("EXISTS (SELECT 1 FROM json_each(tags) WHERE LOWER(value) = LOWER(?))")
                            params.append(tag)

                    if language:
                        conditions.append("LOWER(language) = LOWER(?)")
                        params.append(language)

                    search_project = project or "default"
                    conditions.append("project = ?")
                    params.append(search_project)

                    if conditions:
                        where_clause = " AND ".join(conditions)
                        sql = f"SELECT {select_fields} FROM logichive_functions WHERE {where_clause} LIMIT {limit * 3}"
                        async with db.execute(sql, params) as cursor:
                            sql_rows = await cursor.fetchall()

                        for row in sql_rows:
                            processed = self._process_row(dict(row))
                            processed["similarity"] = 0.9 # Default SQL boost
                            res_key = (processed.get("project", "default"), processed["name"])
                            sql_results[res_key] = processed
                    await db.close()

                # 4. Hydrate Vector results
                final_results = sql_results
                if vector_matches:
                    db = await get_db_connection()
                    db.row_factory = aiosqlite.Row
                    for match in vector_matches:
                        v_name = match["name"]
                        v_project = match["project"]
                        similarity = match["similarity"]
                        res_key = (v_project, v_name)

                        if res_key in final_results:
                            final_results[res_key]["similarity"] = max(final_results[res_key]["similarity"], similarity)
                        else:
                            async with db.execute(
                                f"SELECT {select_fields} FROM logichive_functions WHERE name = ? AND project = ?",
                                (v_name, v_project),
                            ) as cursor:
                                row = await cursor.fetchone()
                                if row:
                                    processed = self._process_row(dict(row))
                                    processed["similarity"] = similarity
                                    final_results[res_key] = processed
                    await db.close()

                # 4. Final Aggregation
                # Standardize all results to have consistent keys
                final_results_list = []
                for key, val in final_results.items():
                    # val is a processed dict from _process_row or vector match
                    res_dict = dict(val)
                    p_key, n_key = key if isinstance(key, tuple) else ("default", key)

                    if "project" not in res_dict:
                        res_dict["project"] = p_key
                    if "name" not in res_dict:
                        res_dict["name"] = n_key
                    if "similarity" not in res_dict:
                        res_dict["similarity"] = 0.5

                    final_results_list.append(res_dict)

                sorted_results = sorted(final_results_list, key=lambda x: x.get("similarity", 0), reverse=True)
                return sorted_results[:limit]

        except Exception as e:
            logger.error("SQLite: Hybrid search failed", exc_info=True)
            # Return detailed error if possible
            error_msg = f"{type(e).__name__}: {str(e)}"
            raise StorageError(f"Hybrid search failed: {error_msg}")

    def _process_row(self, row: dict[str, Any]) -> dict[str, Any]:
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
        if "env_fingerprint" in processed:
            processed["env_fingerprint"] = _safe_json_loads(
                processed["env_fingerprint"], "env_fingerprint"
            )

        if "project" not in processed or processed.get("project") is None:
            processed["project"] = "default"

        return processed

    async def get_function_by_name(
        self, name: str, project: str = "default"
    ) -> dict[str, Any] | None:
        try:
            db = await get_db_connection()
            db.row_factory = lambda cursor, row: dict(
                zip([col[0] for col in cursor.description], row)
            )
            async with db.execute(
                "SELECT * FROM logichive_functions WHERE project = ? AND name = ?",
                (project, name),
            ) as cursor:
                row = await cursor.fetchone()
            await db.close()
            return self._process_row(row)
        except Exception as e:
            logger.error(
                f"SQLite: Failed to get function '{name}' in project '{project}': {e}"
            )
            return None

    async def get_functions(
        self, project: str = None, tags: list[str] = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Flexible listing of functions with optional project and tag filtering.
        """
        try:
            db = await get_db_connection()
            db.row_factory = aiosqlite.Row
            conditions = []
            params = []

            if project:
                conditions.append("project = ?")
                params.append(project)

            if tags:
                for tag in tags:
                    conditions.append(
                        "EXISTS (SELECT 1 FROM json_each(tags) WHERE LOWER(value) = LOWER(?))"
                    )
                    params.append(tag)

            where_clause = ""
            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)

            sql = f"SELECT * FROM logichive_functions{where_clause} ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)

            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
            await db.close()
            return [self._process_row(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"SQLite: Failed to list functions: {e}")
            raise StorageError(f"Failed to list functions: {e}")

    async def get_all_functions(self) -> list[dict[str, Any]]:
        """Backwards compatibility wrapper."""
        return await self.get_functions(limit=1000)

    @retry_on_db_lock()
    @with_write_lock
    async def increment_call_count(self, name: str, project: str = "default") -> bool:
        try:
            db = await get_db_connection()
            await db.execute(
                "UPDATE logichive_functions SET call_count = call_count + 1 WHERE project = ? AND name = ?",
                (project, name),
            )
            await db.commit()
            await db.close()
            return True
        except Exception as e:
            logger.error(
                f"SQLite: Increment failed for '{name}' in project '{project}': {e}"
            )
            raise StorageError(
                f"Failed to increment call count for '{name}' in project '{project}': {e}"
            )


    async def check_health(self) -> dict[str, Any]:
        """Checks if the database is accessible and the main table exists."""
        try:
            db = await get_db_connection()
            async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='logichive_functions'") as cursor:
                row = await cursor.fetchone()
                if row:
                    await db.close()
                    return {"status": "Healthy", "message": "Database and main table are OK."}
                else:
                    await db.close()
                    return {"status": "Error", "message": "Table 'logichive_functions' not found."}
        except Exception as e:
            return {"status": "Error", "message": f"Database check failed: {e}"}

# Singleton instance
sqlite_storage = SqliteStorage()
