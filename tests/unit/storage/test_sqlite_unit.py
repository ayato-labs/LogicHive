import pytest

from storage.sqlite_api import sqlite_storage


@pytest.fixture
async def storage(test_db):
    return sqlite_storage


@pytest.mark.asyncio
async def test_find_similar_functions_include_code_false(storage):
    """
    Verifies that search results do NOT contain code when include_code=False.
    """
    # Use the API instead of direct SQL to stay schema-aligned
    data = {
        "name": "test_func",
        "code": "def secret_code(): pass",
        "description": "desc",
        "language": "python",
        "project": "p1",
        "embedding": [0.1] * 768,
        "code_hash": "hash1",
    }
    await storage.upsert_function(data)

    # CASE 1: include_code=False
    results = await storage.find_similar_functions(
        embedding=data["embedding"], project="p1", include_code=False
    )

    assert len(results) > 0
    assert results[0]["name"] == "test_func"
    assert "code" not in results[0]
    assert results[0]["description"] == "desc"


@pytest.mark.asyncio
async def test_find_similar_functions_include_code_true(storage):
    """
    Verifies that search results DO contain code when include_code=True (default).
    """
    data = {
        "name": "test_code_func",
        "code": "def my_code(): pass",
        "description": "desc",
        "language": "python",
        "project": "p1",
        "embedding": [0.1] * 768,
        "code_hash": "hash2",
    }
    await storage.upsert_function(data)

    # CASE 2: include_code=True
    results = await storage.find_similar_functions(
        embedding=data["embedding"], project="p1", include_code=True
    )

    assert len(results) > 0
    assert "code" in results[0]
    assert results[0]["code"] == "def my_code(): pass"


@pytest.mark.asyncio
async def test_process_row_logic(storage):
    """Verifies that _process_row correctly parses JSON fields."""
    row_data = {
        "name": "func1",
        "code": "code1",
        "description": "desc1",
        "tags": '["t1"]',
        "language": "python",
        "project": "p1",
        "embedding": "[0.1, 0.2]",
    }

    processed = storage._process_row(row_data)

    assert processed["name"] == "func1"
    assert processed["tags"] == ["t1"]
    assert processed["embedding"] == [0.1, 0.2]
    assert processed["code"] == "code1"
