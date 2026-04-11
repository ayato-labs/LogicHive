import pytest
import asyncio
from storage.sqlite_api import SqliteStorage
from core.exceptions import StorageError

@pytest.fixture
async def storage(test_db):
    return SqliteStorage()

@pytest.mark.asyncio
async def test_get_functions_filtering(storage):
    """Tests project and tag filtering in get_functions."""
    # Setup: Insert test data
    f1 = {
        "name": "func1", "project": "projA", "code": "pass", 
        "tags": ["tag1", "common"], "language": "python", "code_hash": "h1"
    }
    f2 = {
        "name": "func2", "project": "projB", "code": "pass", 
        "tags": ["tag2", "common"], "language": "python", "code_hash": "h2"
    }
    
    await storage.upsert_function(f1)
    await storage.upsert_function(f2)
    
    # 1. Filter by project
    results_a = await storage.get_functions(project="projA")
    assert len(results_a) == 1
    assert results_a[0]["name"] == "func1"
    
    # 2. Filter by tag
    results_tag1 = await storage.get_functions(tags=["tag1"])
    assert len(results_tag1) == 1
    assert results_tag1[0]["name"] == "func1"
    
    # 3. Filter by common tag
    results_common = await storage.get_functions(tags=["common"])
    assert len(results_common) == 2
    
    # 4. Non-existent filter
    results_none = await storage.get_functions(project="projX")
    assert len(results_none) == 0

@pytest.mark.asyncio
async def test_process_row_resilience(storage):
    """Tests that _process_row handles malformed or missing JSON gracefully."""
    # Case 1: Normal processing
    row = {
        "name": "test", "tags": '["a", "b"]', "project": "default"
    }
    processed = storage._process_row(row)
    assert processed["tags"] == ["a", "b"]
    
    # Case 2: Malformed JSON
    row_bad = {
        "name": "test", "tags": '["unclosed', "project": "default"
    }
    processed_bad = storage._process_row(row_bad)
    # _process_row uses _safe_json_loads which returns raw on fail
    assert processed_bad["tags"] == '["unclosed'
    
    # Case 3: Missing project defaults to 'default'
    row_no_proj = {"name": "test", "project": None}
    processed_no_proj = storage._process_row(row_no_proj)
    assert processed_no_proj["project"] == "default"

@pytest.mark.asyncio
async def test_delete_function_storage(storage):
    """Tests function deletion."""
    f = {"name": "to_del", "project": "default", "code": "pass", "code_hash": "h"}
    await storage.upsert_function(f)
    
    # Verify exists
    assert await storage.get_function_by_name("to_del") is not None
    
    # Delete
    success = await storage.delete_function("to_del")
    assert success is True
    
    # Verify gone
    assert await storage.get_function_by_name("to_del") is None
