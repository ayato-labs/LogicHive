import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from orchestrator import do_save_async, do_search_async
from storage.sqlite_api import sqlite_storage
from core.execution.base import ExecutionStatus

@pytest.mark.asyncio
async def test_upsert_function_integration_flow(test_db):
    """
    Verifies the full 'Save & Enrich' integration flow.
    We use the default FakeIntelligence provided by the global patch.
    """
    code = "def add_numbers(a, b): return a + b"
    name = "add_numbers"
    project = "integration_test"
    
    # Execute
    # The global fake will return score 95 and auto-tags
    result = await do_save_async(
        name=name,
        code=code,
        project=project,
        language="python"
    )
    
    # Note: Result is the save_result (True/False or maybe the added data)
    # Actually do_save_async returns save_result from sqlite_storage.upsert_function
    assert result is True
    
    # 2. Check persistence in SQLite
    found = await sqlite_storage.get_function_by_name(name, project=project)
    assert found is not None
    assert found["code"] == code
    assert found["reliability_score"] == 0.95
    
    # 3. Check vector discovery
    search_results = await do_search_async(
        query="test query",
        project=project,
        limit=5
    )
    assert len(search_results) > 0
    assert search_results[0]["name"] == name

@pytest.mark.asyncio
async def test_upsert_function_quality_gate_rejection_flow(test_db):
    """
    Verifies that low quality code (detected by Fake) is rejected.
    """
    # Triggering the "fail" keyword in our FakeIntelligence
    bad_code = "def error_func(): pass"
    
    from core.exceptions import ValidationError
    with pytest.raises(ValidationError) as excinfo:
        await do_save_async(
            name="bad_func",
            code=bad_code,
            project="rejection_test"
        )
    
    assert "Quality Gate rejected" in str(excinfo.value)
