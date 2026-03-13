import logging
import aiosqlite
import json
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from core.db import get_db_connection
from core.exceptions import StorageError

from storage.vector_store import vector_manager
from storage.history_manager import history_manager

logger = logging.getLogger(__name__)

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
        limit: int = 5,
        match_threshold: float = 0.1,
    ) -> List[Dict[str, Any]]:
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

            # 2. Perform vector search
            matches = await vector_manager.search(embedding, limit=limit)

            if not matches:
                return []

            # 3. Hydrate results from DB
            results = []
            db = await get_db_connection()
            db.row_factory = lambda cursor, row: dict(
                zip([col[0] for col in cursor.description], row)
            )

            for name, similarity in matches:
                if similarity < match_threshold:
                    continue

                async with db.execute(
                    "SELECT id, name, description, language, tags, reliability_score FROM logichive_functions WHERE name = ?",
                    (name,),
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        res = self._process_row(row)
                        res["similarity"] = similarity
                        results.append(res)

            await db.close()
            return results
        except Exception as e:
            logger.error(f"SQLite: Vector search failed: {e}")
            raise StorageError(f"Search failed: {e}")

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
