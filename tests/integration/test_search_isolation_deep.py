import pytest

from storage.sqlite_api import sqlite_storage


@pytest.mark.asyncio
async def test_search_isolation_shadowing_prevention(test_db, fake_intel):
    """
    Test whether Project A's quantity can crowd out Project B's results (The Shadowing Problem).
    1. Fill Project A with 20 'Generic Math' functions.
    2. Add 1 'Generic Math' function to Project B.
    3. Search Project B. It MUST find its own function, even if Project A has more similar ones.
    """
    # 1. Setup Project A (Noise)
    for i in range(20):
        code = f"def add_{i}(a, b): return a + b"
        desc = f"Generic Math version {i}"
        # Use fake_intel directly
        emb = await fake_intel.generate_embedding(desc)
        await sqlite_storage.upsert_function({
            "name": f"math_func_a_{i}",
            "code": code,
            "description": desc,
            "language": "python",
            "tags": ["math", "noise"],
            "project": "ProjectA",
            "embedding": emb,
            "code_hash": f"hash_a_{i}"
        })

    # 2. Setup Project B (Target)
    target_code = "def target_add(a, b): return a + b"
    target_desc = "Specific Math function for Project B"
    emb_target = await fake_intel.generate_embedding(target_desc)
    await sqlite_storage.upsert_function({
        "name": "math_func_b",
        "code": target_code,
        "description": target_desc,
        "language": "python",
        "tags": ["math", "target"],
        "project": "ProjectB",
        "embedding": emb_target,
        "code_hash": "hash_b"
    })

    # 3. Search Project B
    results = await sqlite_storage.find_similar_functions(
        embedding=emb_target,
        project="ProjectB",
        limit=5
    )

    # Check results
    assert len(results) > 0, "Should have found the function in Project B"
    assert results[0]["name"] == "math_func_b"
    assert all(r["project"] == "ProjectB" for r in results)
