import pytest
from orchestrator import do_save_async, do_search_async
from storage.sqlite_api import sqlite_storage
from core.exceptions import ValidationError

@pytest.mark.asyncio
async def test_full_save_and_search_flow(test_db, mock_intel):
    """Verifies the core orchestration flow (Save -> Search)."""
    name = "pipeline_func"
    code = "def pipeline_func(): return 42"
    
    # 1. Save
    success = await do_save_async(
        name=name,
        code=code,
        project="test-proj",
        tags=["pipeline"]
    )
    assert success is True
    
    # 2. Verify persistence in SQLite
    retrieved = await sqlite_storage.get_function_by_name(name, project="test-proj")
    assert retrieved is not None
    assert retrieved["code"] == code
    
    # 3. Verify Vector Search (Mocked embedding)
    mock_intel.generate_embedding.return_value = [0.5] * 768
    search_results = await do_search_async("some query", project="test-proj")
    assert len(search_results) >= 1
    assert search_results[0]["name"] == name

@pytest.mark.asyncio
async def test_orchestrator_rejection_on_invalid_code(test_db, mock_intel):
    """Verifies that the orchestrator blocks saving of syntactically broken code."""
    broken_code = "def missing_colon("
    
    # Should raise ValidationError or return False depending on your orchestrator's error handle
    # Based on src/orchestrator.py:202, it raises ValidationError for score=0
    with pytest.raises(ValidationError):
        await do_save_async(
            name="broken",
            code=broken_code,
            project="error-proj"
        )
    
    # Ensure it wasn't saved
    assert await sqlite_storage.get_function_by_name("broken", project="error-proj") is None

@pytest.mark.asyncio
async def test_orchestrator_metadata_optimization(test_db, mock_intel):
    """Verifies that orchestrator fills in missing metadata using AI."""
    # Setup mock to return optimized metadata
    mock_intel.optimize_metadata.return_value = {
        "description": "Optimized description",
        "tags": ["ai-tag"]
    }
    
    name = "no_meta_func"
    await do_save_async(
        name=name,
        code="pass",
        description="", # Empty
        tags=[],        # Empty
        project="meta-proj"
    )
    
    retrieved = await sqlite_storage.get_function_by_name(name, project="meta-proj")
    assert retrieved["description"] == "Optimized description"
    assert "ai-tag" in retrieved["tags"]
