import pytest
from orchestrator import do_save_async, do_search_async
from storage.sqlite_api import sqlite_storage

@pytest.mark.asyncio
async def test_full_save_and_search_integration():
    """Tests the full flow from orchestrator to storage using real Gemini API."""
    name = "integration_test_func"
    code = """
def integration_test_func(x: int) -> int:
    \"\"\"Multiplies input by 2.\"\"\"
    return x * 2
"""
    # 1. Save with all Phase 1 bells and whistles
    success = await do_save_async(
        name=name,
        code=code,
        description="A function for integration testing",
        language="python",
        tags=["integration"],
        dependencies=["pytest"],
        test_code="assert integration_test_func(5) == 10"
    )
    
    assert success is True
    
    # 2. Verify persistence
    func = await sqlite_storage.get_function_by_name(name)
    assert func is not None
    assert func["reliability_score"] > 0.8  # Should pass real Quality Gate
    assert "pytest" in func["dependencies"]
    
    # 3. Semantic Search
    # Search for something related to multiplication
    results = await do_search_async("function that doubles an integer", limit=1)
    
    assert len(results) > 0
    assert results[0]["name"] == name
