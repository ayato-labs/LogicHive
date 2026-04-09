import pytest
import asyncio
from storage.sqlite_api import SqliteStorage
from core.consolidation import LogicIntelligence
from core.config import GEMINI_API_KEY

@pytest.mark.asyncio
async def test_search_isolation_shadowing_prevention():
    """
    Test whether Project A's quantity can crowd out Project B's results (The Shadowing Problem).
    1. Fill Project A with 20 'Generic Math' functions.
    2. Add 1 'Generic Math' function to Project B.
    3. Search Project B. It MUST find its own function, even if Project A has more similar ones.
    """
    storage = SqliteStorage()
    intel = LogicIntelligence(GEMINI_API_KEY)
    
    # 1. Setup Project A (Noise)
    for i in range(20):
        code = f"def add_{i}(a, b): return a + b"
        emb = await intel.generate_embedding(f"Simple math function version {i}")
        await storage.upsert_function({
            "name": f"math_func_a_{i}",
            "code": code,
            "description": f"Generic Math version {i}",
            "language": "python",
            "tags": ["math", "noise"],
            "project": "ProjectA",
            "embedding": emb,
            "code_hash": str(hash(code))
        })
        
    # 2. Setup Project B (Target)
    target_code = "def target_add(a, b): return a + b"
    target_desc = "Specific Math function for Project B"
    emb_target = await intel.generate_embedding(target_desc)
    await storage.upsert_function({
        "name": "math_func_b",
        "code": target_code,
        "description": target_desc,
        "language": "python",
        "tags": ["math", "target"],
        "project": "ProjectB",
        "embedding": emb_target,
        "code_hash": str(hash(target_code))
    })
    
    # 3. Search Project B
    results = await storage.find_similar_functions(
        embedding=emb_target,
        project="ProjectB",
        limit=5
    )
    
    # Cleanup
    for i in range(20): await storage.delete_function(f"math_func_a_{i}", "ProjectA")
    await storage.delete_function("math_func_b", "ProjectB")
    
    # Check results
    assert len(results) > 0, "Should have found the function in Project B"
    assert results[0]["name"] == "math_func_b"
    assert all(r["project"] == "ProjectB" for r in results)
