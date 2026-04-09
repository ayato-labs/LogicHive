import pytest
import numpy as np
from storage.vector_store import VectorIndexManager

@pytest.mark.asyncio
async def test_vector_add_and_search():
    """
    Unit test for VectorIndexManager using isolated fixtures.
    Checks that project-scoped composite keys work correctly.
    """
    manager = VectorIndexManager(dimension=768)
    
    # 1. Add vector for Project A
    emb_a = [0.1] * 768
    await manager.add_vector("func_a", emb_a, project="proj-a")
    
    # 2. Add vector for Project B (same name, different embedding)
    emb_b = [0.9] * 768
    await manager.add_vector("func_a", emb_b, project="proj-b")
    
    # 3. Search for Project A
    # Result should return 'proj-a:func_a'
    results = await manager.search(emb_a, limit=5)
    assert len(results) >= 1
    found_keys = [r["name"] for r in results]
    assert "proj-a:func_a" in found_keys
    
    # Check that it's NOT just returning 'func_a' (global)
    assert "proj-b:func_a" in found_keys # FAISS returns based on distance, both should be in index
    # But names must have project prefix
    for r in results:
        assert ":" in r["name"]

@pytest.mark.asyncio
async def test_vector_removal():
    manager = VectorIndexManager(dimension=768)
    name = "temp_func"
    project = "proj-x"
    full_key = f"{project}:{name}"
    
    await manager.add_vector(name, [0.5] * 768, project=project)
    assert full_key in manager.name_to_id
    
    # Verify FAISS didn't duplicate the mapping (should be 1 active name)
    assert len(manager.id_to_name) == 1, (
        "FAISS manager should have exactly 1 active mapping"
    )
    assert full_key in manager.name_to_id
    
    await manager.remove_vector(name, project=project)
    assert full_key not in manager.name_to_id
    assert manager.id_to_name == {} # Should be empty mapping after removal

@pytest.mark.asyncio
async def test_vector_dimension_validation():
    manager = VectorIndexManager(dimension=768)
    # Wrong dimension
    await manager.add_vector("bad_dim", [0.1, 0.2], project="test")
    assert manager.name_to_id == {}
    assert manager.index.ntotal == 0
