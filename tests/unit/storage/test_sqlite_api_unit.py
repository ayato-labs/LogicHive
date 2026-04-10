import pytest
from storage.sqlite_api import sqlite_storage

@pytest.mark.asyncio
async def test_storage_upsert_and_get(test_db):
    """Verifies basic CRUD operations on the SQLite storage."""
    data = {
        "name": "test_persistence",
        "project": "default",
        "code": "def hello(): print('world')",
        "description": "A survival test",
        "embedding": [0.5] * 768,
        "language": "python",
        "tags": ["test"]
    }
    
    # Save
    success = await sqlite_storage.upsert_function(data)
    assert success
    
    # Retrieve
    stored = await sqlite_storage.get_function_by_name("test_persistence")
    assert stored is not None
    assert stored["code"] == data["code"]
    assert stored["description"] == data["description"]

@pytest.mark.asyncio
async def test_storage_project_isolation(test_db):
    """Verifies that functions with the same name but different projects are isolated."""
    common_name = "shared_name"
    
    # Save in project A
    await sqlite_storage.upsert_function({
        "name": common_name,
        "project": "ProjectA",
        "code": "code A",
        "embedding": [0.1] * 768
    })
    
    # Save in project B
    await sqlite_storage.upsert_function({
        "name": common_name,
        "project": "ProjectB",
        "code": "code B",
        "embedding": [0.2] * 768
    })
    
    # Verify retrieval fetches correct one
    res_a = await sqlite_storage.get_function_by_name(common_name, project="ProjectA")
    res_b = await sqlite_storage.get_function_by_name(common_name, project="ProjectB")
    
    assert res_a["code"] == "code A"
    assert res_b["code"] == "code B"

@pytest.mark.asyncio
async def test_storage_deletion(test_db):
    """Verifies function deletion."""
    name = "to_be_deleted"
    await sqlite_storage.upsert_function({
        "name": name,
        "project": "default",
        "code": "pass",
        "embedding": [0.0] * 768
    })
    
    # Delete
    success = await sqlite_storage.delete_function(name)
    assert success
    
    # Confirm gone
    stored = await sqlite_storage.get_function_by_name(name)
    assert stored is None
