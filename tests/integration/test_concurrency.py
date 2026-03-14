import asyncio
import pytest
import uuid
from storage.sqlite_api import sqlite_storage

@pytest.mark.async_timeout(30)
@pytest.mark.asyncio
async def test_concurrent_upserts():
    """
    Simulate multiple concurrent upsert operations to verify the asyncio.Lock fix.
    """
    concurrency_count = 10
    
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
            "embedding": [0.1] * 1536 # Dummy embedding
        }
        return await sqlite_storage.upsert_function(data)

    # Execute concurrent tasks
    results = await asyncio.gather(*(task(i) for i in range(concurrency_count)), return_exceptions=True)
    
    # Check for exceptions
    for res in results:
        if isinstance(res, Exception):
            pytest.fail(f"Concurrent upsert failed with error: {res}")
        assert res is True, "Upsert should return True"

    # Verify all were saved
    all_funcs = await sqlite_storage.get_all_functions()
    saved_names = [f["name"] for f in all_funcs]
    for i in range(concurrency_count):
        assert f"concurrent_func_{i}" in saved_names
