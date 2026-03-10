import logging
import json
import uuid
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.db import get_db_connection

logger = logging.getLogger(__name__)


class SqliteStorage:
    """
    Simplified SQLite Storage Engine for LogicHive (Personal MVP).
    Removed SaaS/Multi-tenancy/Billing logic.
    """

    def __init__(self):
        self._db_path = None
        self.SYSTEM_ORG_ID = "00000000-0000-0000-0000-000000000000"

    async def upsert_function(
        self, function_data: Dict[str, Any], organization_id: Optional[str] = None
    ) -> bool:
        """
        Inserts or updates a function. Defaults to SYSTEM_ORG_ID.
        """
        org_id = organization_id or self.SYSTEM_ORG_ID
        try:
            db = await get_db_connection()
            
            # Check if exists to get the same ID
            async with db.execute(
                "SELECT id FROM logichive_functions WHERE name = ? AND organization_id = ?",
                (function_data["name"], org_id),
            ) as cursor:
                row = await cursor.fetchone()
                row_id = row[0] if row else str(uuid.uuid4())

            data = (
                row_id,
                function_data["name"],
                function_data["code"],
                function_data.get("description", ""),
                function_data.get("language", "python"),
                json.dumps(function_data.get("tags", [])),
                function_data.get("reliability_score", 1.0),
                json.dumps(function_data.get("test_metrics", {})),
                json.dumps(function_data["embedding"]) if "embedding" in function_data else None,
                function_data.get("code_hash"),
                org_id,
            )

            await db.execute(
                """
                INSERT INTO logichive_functions 
                (id, name, code, description, language, tags, reliability_score, test_metrics, embedding, code_hash, organization_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name, organization_id) DO UPDATE SET
                code=excluded.code,
                description=excluded.description,
                language=excluded.language,
                tags=excluded.tags,
                reliability_score=excluded.reliability_score,
                test_metrics=excluded.test_metrics,
                embedding=excluded.embedding,
                code_hash=excluded.code_hash
            """,
                data,
            )

            await db.commit()
            await db.close()
            logger.info(f"SQLite: Successfully saved function '{function_data['name']}'")
            return True
        except Exception as e:
            logger.error(f"SQLite: Failed to save function: {e}")
            return False

    async def find_similar_functions(
        self,
        embedding: List[float],
        organization_id: Optional[str] = None,
        limit: int = 5,
        match_threshold: float = 0.1,
    ) -> List[Dict[str, Any]]:
        org_id = organization_id or self.SYSTEM_ORG_ID
        try:
            db = await get_db_connection()
            db.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            async with db.execute(
                "SELECT id, name, description, language, tags, reliability_score, embedding FROM logichive_functions WHERE organization_id = ? AND embedding IS NOT NULL",
                (org_id,),
            ) as cursor:
                rows = await cursor.fetchall()

            await db.close()
            if not rows:
                return []

            query_vec = np.array(embedding)
            results = []

            for row in rows:
                func_embedding = json.loads(row["embedding"])
                target_vec = np.array(func_embedding)

                norm_q = np.linalg.norm(query_vec)
                norm_t = np.linalg.norm(target_vec)
                if norm_q == 0 or norm_t == 0:
                    similarity = 0.0
                else:
                    similarity = np.dot(query_vec, target_vec) / (norm_q * norm_t)

                if similarity >= match_threshold:
                    results.append({
                        "id": row["id"],
                        "name": row["name"],
                        "description": row["description"],
                        "language": row["language"],
                        "tags": json.loads(row["tags"]),
                        "reliability_score": row["reliability_score"],
                        "similarity": float(similarity),
                    })

            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:limit]
        except Exception as e:
            logger.error(f"SQLite: Vector search failed: {e}")
            return []

    async def get_function_by_name(
        self, name: str, organization_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        org_id = organization_id or self.SYSTEM_ORG_ID
        try:
            db = await get_db_connection()
            db.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            async with db.execute(
                "SELECT * FROM logichive_functions WHERE name = ? AND organization_id = ?",
                (name, org_id),
            ) as cursor:
                row = await cursor.fetchone()
            await db.close()
            return row # Already a dict
        except Exception as e:
            logger.error(f"SQLite: Failed to get function '{name}': {e}")
            return None

    async def get_all_functions(self, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        org_id = organization_id or self.SYSTEM_ORG_ID
        try:
            db = await get_db_connection()
            db.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
            async with db.execute(
                "SELECT * FROM logichive_functions WHERE organization_id = ?",
                (org_id,),
            ) as cursor:
                rows = await cursor.fetchall()
            await db.close()
            return rows # Already a list of dicts
        except Exception as e:
            logger.error(f"SQLite: Failed to list all functions: {e}")
            return []

    async def increment_call_count(self, name: str, organization_id: Optional[str] = None) -> bool:
        org_id = organization_id or self.SYSTEM_ORG_ID
        try:
            db = await get_db_connection()
            await db.execute(
                "UPDATE logichive_functions SET call_count = call_count + 1 WHERE name = ? AND organization_id = ?",
                (name, org_id),
            )
            await db.commit()
            await db.close()
            return True
        except Exception as e:
            logger.error(f"SQLite: Increment failed for '{name}': {e}")
            return False

# Singleton instance
sqlite_storage = SqliteStorage()
