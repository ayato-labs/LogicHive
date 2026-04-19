import asyncio
import logging
import os
import shutil

from core.db import get_db_connection
from storage.sqlite_api import sqlite_storage
from storage.vector_store import vector_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_1_5():
    logger.info("--- LogicHive Phase 1.5 Verification ---")

    # 1. Clean up potential old data for clean test
    db = await get_db_connection()
    await db.execute("DELETE FROM logichive_functions")
    await db.execute("DELETE FROM logichive_function_history")
    await db.commit()
    await db.close()

    if os.path.exists("exports/projects"):
        shutil.rmtree("exports/projects")

    # Rebuild index to clear memory
    await vector_manager.rebuild_index()

    # 2. Test Vector Store & Backup Isolation
    logger.info("[1] Testing Vector Store & Backup Isolation...")

    from storage.auto_backup import backup_manager

    # Save directly via sqlite_storage to bypass AI pipeline for infra test
    data_a = {
        "name": "isolated_func",
        "code": "def proj_a(): return 'A'",
        "project": "proj-a",
        "language": "python",
        "embedding": [0.1] * 768,
        "code_hash": "hash-a",
        "tags": ["a_tag"],
    }
    await sqlite_storage.upsert_function(data_a)
    await backup_manager.export_asset(data_a)  # Manually trigger export

    data_b = {
        "name": "isolated_func",
        "code": "def proj_b(): return 'B'",
        "project": "proj-b",
        "language": "python",
        "embedding": [0.2] * 768,
        "code_hash": "hash-b",
        "tags": ["b_tag"],
    }
    await sqlite_storage.upsert_function(data_b)
    await backup_manager.export_asset(data_b)  # Manually trigger export

    # 3. Check FAISS mappings
    logger.info("[2] Checking FAISS composite keys...")
    assert "proj-a:isolated_func" in vector_manager.name_to_id, "Missing Proj A key"
    assert "proj-b:isolated_func" in vector_manager.name_to_id, "Missing Proj B key"
    logger.info("PASS: FAISS mapping uses composite keys.")

    # 4. Check Backup Structure
    logger.info("[3] Checking Backup Directory Structure...")
    path_a = os.path.join(
        "exports", "projects", "proj-a", "functions", "python", "isolated_func.py"
    )
    path_b = os.path.join(
        "exports", "projects", "proj-b", "functions", "python", "isolated_func.py"
    )

    assert os.path.exists(path_a), f"Missing backup A: {path_a}"
    assert os.path.exists(path_b), f"Missing backup B: {path_b}"

    with open(path_a) as f:
        assert "proj_a" in f.read(), "Content mismatch in A"
    with open(path_b) as f:
        assert "proj_b" in f.read(), "Content mismatch in B"
    logger.info("PASS: Backup structure is project-partitioned.")

    # 5. Check History Column
    logger.info("[4] Checking History Project context...")
    # Update Proj A (v2) to trigger history archive
    data_a_v2 = data_a.copy()
    data_a_v2["code"] = "def proj_a_v2(): return 'A2'"
    data_a_v2["code_hash"] = "hash-a2"
    await sqlite_storage.upsert_function(data_a_v2)

    db = await get_db_connection()
    async with db.execute(
        "SELECT project FROM logichive_function_history WHERE name='isolated_func'"
    ) as cursor:
        rows = await cursor.fetchall()
        assert len(rows) > 0, "History not archived"
        assert rows[0][0] == "proj-a", f"Project context lost in history: {rows[0][0]}"
    await db.close()
    logger.info("PASS: History preserves project context.")

    logger.info("--- Phase 1.5 Verification COMPLETED SUCCESSFULY ---")


if __name__ == "__main__":
    asyncio.run(verify_1_5())
