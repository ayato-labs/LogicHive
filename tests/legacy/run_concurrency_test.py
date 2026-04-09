import asyncio
import uuid
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from storage.sqlite_api import sqlite_storage
from storage.init_db import init_db


async def run_test():
    print("Initializing test database...")
    os.environ["SQLITE_DB_PATH"] = "test_concurrency.db"
    await init_db()

    concurrency_count = 20
    print(f"Starting {concurrency_count} concurrent upserts...")

    async def task(i):
        name = f"concurrent_func_{i}"
        data = {
            "id": str(uuid.uuid4()),
            "name": name,
            "code": f"def {name}(): return {i}",
            "description": f"Test concurrent function {i}",
            "language": "python",
            "tags": ["test", "concurrency"],
            "reliability_score": 0.95,
            "code_hash": f"hash_{i}",
            "embedding": [0.1] * 1536,  # Dummy embedding
        }
        try:
            success = await sqlite_storage.upsert_function(data)
            return success
        except Exception as e:
            print(f"Task {i} failed: {e}")
            return e

    # Execute concurrent tasks
    results = await asyncio.gather(
        *(task(i) for i in range(concurrency_count)), return_exceptions=True
    )

    success_count = sum(1 for res in results if res is True)
    error_count = sum(
        1 for res in results if isinstance(res, Exception) or res is False
    )

    print(f"Results: {success_count} successes, {error_count} errors")

    if error_count == 0:
        print("SUCCESS: All concurrent writes passed without locking issues.")
    else:
        print("FAILED: Some writes encountered issues.")
        sys.exit(1)

    # Cleanup
    if os.path.exists("test_concurrency.db"):
        os.remove("test_concurrency.db")
        # Also cleanup WAL files
        for f in ["test_concurrency.db-wal", "test_concurrency.db-shm"]:
            if os.path.exists(f):
                os.remove(f)


if __name__ == "__main__":
    asyncio.run(run_test())
