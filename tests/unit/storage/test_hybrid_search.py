import pytest
import asyncio
from storage.sqlite_api import sqlite_storage
from core.db import get_db_connection

@pytest.mark.asyncio
async def test_hybrid_search_keyword_and_tags():
    # Setup: Insert a dummy function with tags
    db = await get_db_connection()
    await db.execute("DELETE FROM logichive_functions WHERE name = 'hybrid_test_func'")
    await db.execute(
        """
        INSERT INTO logichive_functions (id, name, code, description, tags, language, version)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("test-id-123", "hybrid_test_func", "def hybrid(): pass", "A test function for hybrid search.", '["search", "hybrid", "test"]', "python", 1)
    )
    await db.commit()
    await db.close()

    # Test 1: Vector-only search (embedding is dummy)
    dummy_emb = [0.1] * 768
    results_vector = await sqlite_storage.find_similar_functions(dummy_emb, limit=10)
    # Just check it runs and returns something
    assert isinstance(results_vector, list)

    # Test 2: Keyword search (name)
    results_name = await sqlite_storage.find_similar_functions(dummy_emb, query_text="hybrid_test", limit=5)
    assert any(r["name"] == "hybrid_test_func" for r in results_name)
    # Check boost
    matched = next(r for r in results_name if r["name"] == "hybrid_test_func")
    assert matched["similarity"] >= 0.9

    # Test 3: Tag search (# syntax)
    results_tag = await sqlite_storage.find_similar_functions(dummy_emb, query_text="#hybrid", limit=5)
    assert any(r["name"] == "hybrid_test_func" for r in results_tag)

    # Test 4: Explicit tags
    results_tags = await sqlite_storage.find_similar_functions(dummy_emb, tags=["test"], limit=5)
    assert any(r["name"] == "hybrid_test_func" for r in results_tags)

    # Test 5: Keyword + Tags (Combined)
    results_both = await sqlite_storage.find_similar_functions(dummy_emb, query_text="hybrid", tags=["search"], limit=5)
    assert any(r["name"] == "hybrid_test_func" for r in results_both)

    # Cleanup
    db = await get_db_connection()
    await db.execute("DELETE FROM logichive_functions WHERE name = 'hybrid_test_func'")
    await db.commit()
    await db.close()
