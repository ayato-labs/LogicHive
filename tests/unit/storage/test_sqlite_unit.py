import pytest
import sqlite3
import json
from storage.sqlite_api import SqliteStorage

@pytest.fixture
async def storage(test_db):
    return SqliteStorage()

@pytest.mark.asyncio
async def test_find_similar_functions_include_code_false(storage):
    """
    Verifies that search results do NOT contain code when include_code=False.
    """
    # Preset: Manual insert into DB bypasses integration overhead
    conn = sqlite3.connect(storage.db_path)
    conn.execute(
        "INSERT INTO logichive_functions (id, name, code, description, tags, language, project, embedding) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("fake_id_1", "test_func", "def secret_code(): pass", "desc", "[]", "python", "p1", json.dumps([0.1]*768))
    )
    conn.commit()
    conn.close()
    
    # Mocking embedding to return a deterministic vector
    query_emb = [0.1] * 768
    
    # CASE 1: include_code=False
    results = await storage.find_similar_functions(
        query_emb, project="p1", include_code=False
    )
    
    assert len(results) > 0
    assert results[0]["name"] == "test_func"
    assert "code" not in results[0] or results[0]["code"] == ""
    assert results[0]["description"] == "desc"

@pytest.mark.asyncio
async def test_find_similar_functions_include_code_true(storage):
    """
    Verifies that search results DO contain code when include_code=True (default).
    """
    conn = sqlite3.connect(storage.db_path)
    conn.execute(
        "INSERT INTO logichive_functions (id, name, code, description, tags, language, project, embedding) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("fake_id_2", "test_code_func", "def my_code(): pass", "desc", "[]", "python", "p1", json.dumps([0.1]*768))
    )
    conn.commit()
    conn.close()
    
    query_emb = [0.1] * 768
    
    # CASE 2: include_code=True
    results = await storage.find_similar_functions(
        query_emb, project="p1", include_code=True
    )
    
    assert len(results) > 0
    assert "code" in results[0]
    assert results[0]["code"] == "def my_code(): pass"

@pytest.mark.asyncio
async def test_process_row_logic(storage):
    """Verifies that _process_row correctly parses JSON fields."""
    # Simulate a row that behaves like a dict (sqlite3.Row behavior)
    row_data = {
        "name": "func1", 
        "code": "code1", 
        "description": "desc1", 
        "tags": '["t1"]', 
        "language": "python", 
        "project": "p1", 
        "metadata": '{"meta":"val"}'
    }
    
    # We pass the dict directly as _process_row does dict(row)
    processed = storage._process_row(row_data.items()) # dict(items) works
    
    assert processed["name"] == "func1"
    assert processed["tags"] == ["t1"]
    # metadata is handled by SqliteStorage separately in some flows, 
    # but _process_row only does tags/metrics/embedding/dependencies
    assert processed["code"] == "code1"
