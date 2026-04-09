import logging
import json
import asyncio
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Any
from core.config import (
    VECTOR_DIMENSION,
    FAISS_INDEX_PATH,
    FAISS_MAPPING_PATH,
    FAISS_GHOST_REBUILD_THRESHOLD,
)
from core.db import get_db_connection
from core.exceptions import StorageError

logger = logging.getLogger(__name__)


class VectorIndexManager:
    """Manages persistent FAISS index with incremental updates."""

    def __init__(self, dimension: int = VECTOR_DIMENSION):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.id_to_name = {}
        self.name_to_id = {}
        self._current_id = 0
        self._index_path = FAISS_INDEX_PATH
        self._mapping_path = FAISS_MAPPING_PATH
        self._lock = asyncio.Lock()
        self._initialized = False

    async def ensure_initialized(self, db_rows: List[Dict[str, Any]]):
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            # Load from disk if exists
            if Path(self._index_path).exists() and Path(self._mapping_path).exists():
                try:
                    self.index = faiss.read_index(self._index_path)
                    with open(self._mapping_path, "r") as f:
                        mapping = json.load(f)
                        self.id_to_name = {
                            int(k): v for k, v in mapping["id_to_name"].items()
                        }
                        self.name_to_id = mapping["name_to_id"]
                        self._current_id = mapping["current_id"]
                    self._initialized = True
                    logger.info("FAISS: Loaded index from disk.")
                    return
                except Exception as e:
                    logger.error(f"FAISS: Load failed, rebuilding: {e}")

            # Rebuild from DB rows
            embeddings = []
            names = []
            for row in db_rows:
                if "embedding" in row.keys() and row["embedding"]:
                    try:
                        vec = json.loads(row["embedding"])
                        project = row["project"] if "project" in row.keys() else "default"
                        name = row["name"]
                        full_key = f"{project}:{name}"
                        if len(vec) == self.dimension:
                            embeddings.append(vec)
                            names.append(full_key)
                    except (json.JSONDecodeError, TypeError, KeyError) as e:
                        logger.warning(
                            f"FAISS: Skipping row due to invalid embedding: {e}"
                        )
                        continue

            if embeddings:
                embeddings_np = np.array(embeddings).astype("float32")
                faiss.normalize_L2(embeddings_np)
                self.index.add(embeddings_np)
                for i, full_key in enumerate(names):
                    self.id_to_name[i] = full_key
                    self.name_to_id[full_key] = i
                self._current_id = len(names)

            self._initialized = True
            await self.save_to_disk()
            logger.info("FAISS: Rebuilt index from DB.")

    async def add_vector(self, name: str, embedding: List[float], project: str = "default"):
        async with self._lock:
            full_key = f"{project}:{name}"
            # 1. Basic validation
            if len(embedding) != self.dimension:
                logger.warning(
                    f"FAISS: Dimension mismatch for '{full_key}'. Expected {self.dimension}, got {len(embedding)}"
                )
                return

            needs_rebuild = False
            if full_key in self.name_to_id:
                # Mark as stale (ghost vector)
                old_id = self.name_to_id[full_key]
                if old_id in self.id_to_name:
                    del self.id_to_name[old_id]

                ghost_count = self.index.ntotal - len(self.id_to_name)
                if ghost_count > FAISS_GHOST_REBUILD_THRESHOLD:
                    needs_rebuild = True

            vec = np.array([embedding]).astype("float32")
            faiss.normalize_L2(vec)

            self.index.add(vec)
            new_id = self._current_id
            self.id_to_name[new_id] = full_key
            self.name_to_id[full_key] = new_id
            self._current_id += 1
            await self.save_to_disk()

            if needs_rebuild:
                logger.info(f"FAISS: Ghost vectors exceeded threshold for '{full_key}', rebuilding.")
                await self._rebuild_internal()

    async def remove_vector(self, name: str, project: str = "default"):
        """Removes a vector's mapping. Does not directly delete from FAISS (bloat mitigated by rebuild)."""
        async with self._lock:
            full_key = f"{project}:{name}"
            if full_key in self.name_to_id:
                old_id = self.name_to_id[full_key]
                if old_id in self.id_to_name:
                    del self.id_to_name[old_id]
                del self.name_to_id[full_key]

                await self.save_to_disk()

                ghost_count = self.index.ntotal - len(self.id_to_name)
                if ghost_count > FAISS_GHOST_REBUILD_THRESHOLD:
                    logger.info(
                        f"FAISS: Ghost vectors exceeded threshold during removal of '{full_key}', rebuilding."
                    )
                    await self._rebuild_internal()

    async def rebuild_index(self):
        """Public method to force rebuild index from DB."""
        async with self._lock:
            await self._rebuild_internal()

    async def _rebuild_internal(self):
        """Internal rebuild logic (assumes lock is held)."""
        logger.info("FAISS: Rebuilding index to clear bloat...")
        try:
            db = await get_db_connection()
            async with db.execute(
                "SELECT project, name, embedding FROM logichive_functions WHERE embedding IS NOT NULL"
            ) as cursor:
                rows = await cursor.fetchall()
            await db.close()

            self.index = faiss.IndexFlatIP(self.dimension)
            self.id_to_name = {}
            self.name_to_id = {}
            self._current_id = 0

            embeddings = []
            names = []
            for row in rows:
                try:
                    vec = json.loads(row["embedding"])
                    project = row["project"] if "project" in row.keys() else "default"
                    name = row["name"]
                    full_key = f"{project}:{name}"
                    if len(vec) == self.dimension:
                        embeddings.append(vec)
                        names.append(full_key)
                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    logger.warning(f"FAISS: Skipping row due to invalid embedding: {e}")
                    continue

            if embeddings:
                embeddings_np = np.array(embeddings).astype("float32")
                faiss.normalize_L2(embeddings_np)
                self.index.add(embeddings_np)
                for i, full_key in enumerate(names):
                    self.id_to_name[i] = full_key
                    self.name_to_id[full_key] = i
                self._current_id = len(names)

            await self.save_to_disk()
            logger.info(f"FAISS: Rebuild complete. Active vectors: {self.index.ntotal}")
        except Exception as e:
            logger.error(f"FAISS: Rebuild failed: {e}")
            raise StorageError(f"Vector Index Rebuild failed: {e}")

    async def save_to_disk(self):
        try:
            Path(self._index_path).parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, self._index_path)
            with open(self._mapping_path, "w") as f:
                json.dump(
                    {
                        "id_to_name": {str(k): v for k, v in self.id_to_name.items()},
                        "name_to_id": self.name_to_id,
                        "current_id": self._current_id,
                    },
                    f,
                )
        except Exception as e:
            logger.error(
                f"FAISS: Failed to save index to {self._index_path}: {e}", exc_info=True
            )

    async def search(self, query_emb: List[float], limit: int = 5) -> List[tuple]:
        if not self._initialized:
            return []

        query_vec = np.array([query_emb]).astype("float32")
        faiss.normalize_L2(query_vec)

        k = min(limit, self.index.ntotal)
        if k <= 0:
            return []

        similarities, indices = self.index.search(query_vec, k)

        results = []
        seen_keys = set()
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue
            full_key = self.id_to_name.get(idx)
            if full_key and full_key not in seen_keys:
                # full_key is project:name
                parts = full_key.split(":", 1)
                project = parts[0]
                name = parts[1]
                
                results.append({
                    "name": name,
                    "project": project,
                    "similarity": float(similarities[0][i])
                })
                seen_keys.add(full_key)
        return results


# Singleton instance
vector_manager = VectorIndexManager()
