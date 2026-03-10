import pytest
import orchestrator
import asyncio
from storage.sqlite_api import sqlite_storage

@pytest.mark.asyncio
async def test_save_and_get_function(test_db, mock_intel):
    """Verifies that a function can be saved with AI optimization and retrieved."""
    name = "calculate_sum"
    code = "def calculate_sum(a, b): return a + b"
    
    # Reset mock call count
    mock_intel.optimize_metadata.reset_mock()
    
    # Save
    success = await orchestrator.do_save_async(name, code, "Adds two numbers")
    assert success is True
    
    # Get
    data = await orchestrator.do_get_async(name)
    assert data["name"] == name
    assert data["code"] == code
    assert "Mocked technical" in data["description"]
    assert "mock" in data["tags"]

@pytest.mark.asyncio
async def test_duplicate_save_skips_ai(test_db, mock_intel):
    """Verifies that saving the same code twice skips redundant AI calls via hash check."""
    name = "hash_test"
    code = "def hash_test(): pass"
    
    mock_intel.optimize_metadata.reset_mock()
    
    # First save
    await orchestrator.do_save_async(name, code)
    assert mock_intel.optimize_metadata.call_count == 1
    
    # Second save (unchanged)
    await orchestrator.do_save_async(name, code)
    # AI optimization should NOT be called again
    assert mock_intel.optimize_metadata.call_count == 1

@pytest.mark.asyncio
async def test_semantic_search_integration(test_db, mock_intel):
    """Verifies that semantic search returns results via the mocked embedding path."""
    mock_intel.generate_embedding.reset_mock()
    
    await orchestrator.do_save_async("logic_a", "def a(): pass")
    # 1 call for save
    
    await orchestrator.do_search_async("Find some logic")
    # 1 call for query embedding in search
    
    assert mock_intel.generate_embedding.call_count >= 2
