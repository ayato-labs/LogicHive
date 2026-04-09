import pytest
from storage.sqlite_api import sqlite_storage, vector_manager


@pytest.mark.asyncio
async def test_upsert_and_retrieve_function(test_db):
    """Tests saving and retrieving a function with dependencies and test_code."""
    data = {
        "name": "test_func",
        "code": "def test_func(): pass",
        "description": "A test function",
        "language": "python",
        "tags": ["test"],
        "reliability_score": 0.95,
        "test_metrics": {"complexity": 1},
        "embedding": [0.1] * 768,
        "code_hash": "hash123",
        "dependencies": ["pytest", "requests"],
        "test_code": "assert True",
    }

    # Save
    success = await sqlite_storage.upsert_function(data)
    assert success is True

    # Retrieve
    retrieved = await sqlite_storage.get_function_by_name("test_func")
    assert retrieved is not None
    assert retrieved["name"] == "test_func"
    assert retrieved["dependencies"] == ["pytest", "requests"]
    assert retrieved["test_code"] == "assert True"
    assert retrieved["version"] == 1

    # Assert JSON array parsing
    assert isinstance(retrieved["embedding"], list)
    assert len(retrieved["embedding"]) == 768

    # Assert FAISS index sync
    assert len(vector_manager.id_to_name) == 1, (
        "FAISS manager should have exactly 1 active mapping"
    )
    # Check project prefix in FAISS key
    assert "default:test_func" in vector_manager.name_to_id


@pytest.mark.asyncio
async def test_versioning_on_code_change(test_db):
    """Verifies that changing code increases version and archives history."""
    name = "version_test"
    data1 = {
        "name": name,
        "code": "v1 code",
        "code_hash": "hash1",
        "embedding": [0.1] * 768,
    }

    await sqlite_storage.upsert_function(data1)

    data2 = data1.copy()
    data2["code"] = "v2 code"
    data2["code_hash"] = "hash2"

    await sqlite_storage.upsert_function(data2)

    retrieved = await sqlite_storage.get_function_by_name(name)
    assert retrieved["version"] == 2
    assert retrieved["code"] == "v2 code"

    # Check history (directly via DB connection for verification)
    from core.db import get_db_connection

    db = await get_db_connection()
    async with db.execute(
        "SELECT * FROM logichive_function_history WHERE name = ?", (name,)
    ) as cursor:
        rows = await cursor.fetchall()
        assert len(rows) == 1, "There should be exactly 1 archived version"
        history_row = dict(rows[0])
        assert history_row["version"] == 1
        assert history_row["code"] == "v1 code"
        assert history_row["code_hash"] == "hash1"
    await db.close()

    # Verify FAISS didn't duplicate the mapping (should be 1 active name)
    assert len(vector_manager.id_to_name) == 1, (
        "FAISS manager should have exactly 1 active mapping"
    )
    assert "default:version_test" in vector_manager.name_to_id


@pytest.mark.asyncio
async def test_semantic_search_real_faiss(test_db):
    """Tests semantic search using the real FAISS manager."""
    # Ensure vector manager is empty due to conftest clear_cache fixture

    func1_emb = [0.0] * 768
    func1_emb[0] = 1.0  # Vector toward axis 0
    func2_emb = [0.0] * 768
    func2_emb[1] = 1.0  # Vector toward axis 1

    await sqlite_storage.upsert_function(
        {"name": "math_util", "embedding": func1_emb, "code": "...", "code_hash": "h1"}
    )
    await sqlite_storage.upsert_function(
        {
            "name": "string_util",
            "embedding": func2_emb,
            "code": "...",
            "code_hash": "h2",
        }
    )

    # Search for something near func2 (axis 1)
    query_emb = [0.0] * 768
    query_emb[1] = 0.9
    query_emb[0] = 0.1
    results = await sqlite_storage.find_similar_functions(query_emb, limit=1)

    assert len(results) > 0
    assert results[0]["name"] == "string_util"
    assert results[0]["similarity"] > 0.8


@pytest.mark.asyncio
async def test_project_isolation_in_sqlite(test_db):
    """Verifies that functions with same name in different projects don't collide."""
    common_name = "shared_name"
    
    # Project A
    await sqlite_storage.upsert_function({
        "name": common_name, "project": "proj-a", "code": "code-a", "code_hash": "ha", "embedding": [0.1]*768
    })
    
    # Project B
    await sqlite_storage.upsert_function({
        "name": common_name, "project": "proj-b", "code": "code-b", "code_hash": "hb", "embedding": [0.2]*768
    })
    
    # Retrieve Project A version
    func_a = await sqlite_storage.get_function_by_name(common_name, project="proj-a")
    assert func_a["code"] == "code-a"
    assert func_a["project"] == "proj-a"
    
    # Retrieve Project B version
    func_b = await sqlite_storage.get_function_by_name(common_name, project="proj-b")
    assert func_b["code"] == "code-b"
    assert func_b["project"] == "proj-b"
    
    # Ensure default retrieval doesn't find them if they aren't in default
    func_none = await sqlite_storage.get_function_by_name(common_name, project="default")
    assert func_none is None
