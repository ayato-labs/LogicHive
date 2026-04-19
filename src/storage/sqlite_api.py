import asyncio
import json
import logging
import uuid
from functools import wraps
from typing import Any

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
        if isinstance(data, (dict, list)):
            return data
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.warning(
            f"SQLite: Failed to parse JSON for field '{field_name}': {e}. Raw data: {data}"
        )
        return data


class SqliteStorage:
    """
    Simplified SQLite Storage Engine for LogicHive (Personal MVP).
    Uses a shared singleton connection to prevent threading issues on Windows.
    """

    def __init__(self, db_path: str = SQLITE_DB_PATH):
        self.db_path = db_path
        self._lock = asyncio.Lock()

    @retry_on_db_lock()
    @with_write_lock
    async def upsert_function(self, function_data: dict[str, Any]) -> bool:
        """
        Inserts or updates a function using the shared singleton connection.
        """
        try:
            db = await get_db_connection()
            project = function_data.get("project", "default")
            name = function_data["name"]

            # 1. Check if name exists in specific project
            async with db.execute(
                "SELECT id, code, code_hash, version FROM logichive_functions WHERE project = ? AND name = ?",
                (project, name),
            ) as cursor:
                row = await cursor.fetchone()
                existing = dict(row) if row else None

            row_id = str(uuid.uuid4())
            new_version = 1

            if existing:
                if existing["code_hash"] != function_data.get("code_hash"):
                    new_version = (existing.get("version") or 0) + 1
                    async with db.execute(
                        "SELECT * FROM logichive_functions WHERE project = ? AND name = ?",
                        (project, name),
                    ) as cursor:
                        full_existing_row = await cursor.fetchone()

                    if full_existing_row:
                        await history_manager.archive_version(db, dict(full_existing_row))
                else:
                    row_id = existing["id"]
                    new_version = existing["version"]

            data = (
                row_id,
                project,
                name,
                function_data["code"],
                function_data.get("description", ""),
                function_data.get("language", "python"),
                json.dumps(function_data.get("tags", [])),
                function_data.get("reliability_score", 1.0),
                json.dumps(function_data.get("test_metrics", {})),
                json.dumps(function_data["embedding"]) if "embedding" in function_data else None,
                function_data.get("code_hash"),
                new_version,
                json.dumps(function_data.get("dependencies", [])),
                function_data.get("test_code", ""),
                json.dumps(function_data.get("env_fingerprint", {}))
                if function_data.get("env_fingerprint")
                else None,
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

            if "embedding" in function_data:
                await vector_manager.add_vector(name, function_data["embedding"], project=project)

            return True
        except Exception as e:
            logger.error(f"SQLite: Failed to save function: {e}")
            raise StorageError(f"Database upsert failed: {e}")

    async def list_all_functions(self) -> list[dict[str, Any]]:
        try:
            db = await get_db_connection()
            async with db.execute("SELECT * FROM logichive_functions") as cursor:
                rows = await cursor.fetchall()
                return [self._process_row(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"SQLite: Failed to list all functions: {e}")
            return []

    async def delete_function(self, name: str, project: str = "default") -> bool:
        try:
            db = await get_db_connection()
            await db.execute(
                "DELETE FROM logichive_functions WHERE project = ? AND name = ?",
                (project, name),
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"SQLite: Delete failed for '{name}': {e}")
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
        try:
            async with self._lock:
                if not vector_manager._initialized:
                    db = await get_db_connection()
                    async with db.execute(
                        "SELECT name, embedding, project FROM logichive_functions WHERE embedding IS NOT NULL"
                    ) as cursor:
                        rows = [dict(r) for r in await cursor.fetchall()]
                    await vector_manager.ensure_initialized(rows)

                vector_matches = []
                if embedding and len(embedding) == VECTOR_DIMENSION:
                    try:
                        vector_matches = await vector_manager.search(
                            embedding, limit=limit, project=project
                        )
                    except Exception as ve:
                        logger.warning(f"SQLite: Vector search failed: {ve}")

                sql_results = {}
                select_fields = "id, name, description, language, tags, reliability_score, project, version, created_at, updated_at, code"

                if query_text or tags or language or project:
                    conditions = []
                    params = []

                    if query_text:
                        term = f"%{query_text.lower()}%"
                        conditions.append("(LOWER(name) LIKE ? OR LOWER(description) LIKE ?)")
                        params.extend([term, term])

                    if tags:
                        for tag in tags:
                            conditions.append(
                                "EXISTS (SELECT 1 FROM json_each(tags) WHERE LOWER(value) = LOWER(?))"
                            )
                            params.append(tag)

                    if language:
                        conditions.append("LOWER(language) = LOWER(?)")
                        params.append(language)

                    if project:
                        conditions.append("project = ?")
                        params.append(project)

                    if conditions:
                        where_clause = " AND ".join(conditions)
                        sql = f"SELECT {select_fields} FROM logichive_functions WHERE {where_clause} LIMIT {limit * 3}"
                        db = await get_db_connection()
                        async with db.execute(sql, params) as cursor:
                            rows = await cursor.fetchall()
                            for r in rows:
                                processed = self._process_row(dict(r))
                                processed["similarity"] = 0.9
                                sql_results[(processed["project"], processed["name"])] = processed

                final_results = sql_results
                if vector_matches:
                    db = await get_db_connection()
                    for match in vector_matches:
                        res_key = (match["project"], match["name"])
                        if res_key in final_results:
                            final_results[res_key]["similarity"] = max(
                                final_results[res_key]["similarity"], match["similarity"]
                            )
                        else:
                            async with db.execute(
                                f"SELECT {select_fields} FROM logichive_functions WHERE project = ? AND name = ?",
                                res_key,
                            ) as cursor:
                                row = await cursor.fetchone()
                                if row:
                                    processed = self._process_row(dict(row))
                                    processed["similarity"] = match["similarity"]
                                    final_results[res_key] = processed

                results_list = sorted(
                    final_results.values(), key=lambda x: x.get("similarity", 0), reverse=True
                )
                return results_list[:limit]
        except Exception as e:
            logger.error(f"SQLite: Find similar failed: {e}")
            raise StorageError(f"Hybrid search failed: {e}")

    def _process_row(self, row: dict[str, Any]) -> dict[str, Any]:
        if not row:
            return None
        processed = dict(row)
        for field in ["tags", "test_metrics", "embedding", "dependencies", "env_fingerprint"]:
            if field in processed:
                processed[field] = _safe_json_loads(processed[field], field)
        if "project" not in processed or not processed["project"]:
            processed["project"] = "default"
        return processed

    async def get_function_by_name(
        self, name: str, project: str = "default"
    ) -> dict[str, Any] | None:
        try:
            db = await get_db_connection()
            async with db.execute(
                "SELECT * FROM logichive_functions WHERE project = ? AND name = ?", (project, name)
            ) as cursor:
                row = await cursor.fetchone()
            return self._process_row(dict(row)) if row else None
        except Exception as e:
            logger.error(f"SQLite: Get failed for '{name}': {e}")
            return None

    async def get_functions(
        self, project: str = None, tags: list[str] = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        try:
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

            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
            sql = (
                f"SELECT * FROM logichive_functions{where_clause} ORDER BY updated_at DESC LIMIT ?"
            )
            params.append(limit)

            db = await get_db_connection()
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [self._process_row(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"SQLite: List failed: {e}")
            raise StorageError(f"Failed to list functions: {e}")

    async def get_all_functions(self) -> list[dict[str, Any]]:
        return await self.get_functions(limit=1000)

    async def get_function_count(self) -> int:
        """Returns the total number of functions in the vault."""
        try:
            db = await get_db_connection()
            async with db.execute("SELECT COUNT(*) FROM logichive_functions") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"SQLite: Failed to get function count: {e}")
            return 0

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
            return True
        except Exception as e:
            logger.error(f"SQLite: Increment failed for '{name}': {e}")
            return False

    async def get_function_count(self) -> int:
        """Returns the total number of functions in the vault."""
        try:
            db = await get_db_connection()
            async with db.execute("SELECT count(*) FROM logichive_functions") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"SQLite: Failed to count functions: {e}")
            return 0

    async def check_health(self) -> dict[str, Any]:
        """Checks if the database is accessible and the main table exists."""
        try:
            db = await get_db_connection()
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='logichive_functions'"
            ) as cursor:
                if await cursor.fetchone():
                    return {"status": "Healthy", "message": "Database OK"}
                return {"status": "Error", "message": "Table not found"}
        except Exception as e:
            return {"status": "Error", "message": str(e)}


sqlite_storage = SqliteStorage()
