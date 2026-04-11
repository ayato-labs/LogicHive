import pytest
from orchestrator import do_save_async
from core.exceptions import ValidationError
from storage.sqlite_api import sqlite_storage

@pytest.mark.asyncio
async def test_rigor_story_sophistry_rejection(test_db):
    """
    SYSTEM TEST: The Rigor Story - Sophistry Rejection.
    User tries to save code that 'looks' good but has NO substance (no assertions).
    The system must reject it even if it's not a draft.
    """
    name = "sophistry_func"
    code = "def do_nothing(): pass"
    # test_code with NO assertions
    test_code = "do_nothing()"
    description = "A very complex and important logic asset."
    
    with pytest.raises(ValidationError) as excinfo:
        await do_save_async(
            name=name,
            code=code,
            description=description,
            test_code=test_code,
            language="python"
        )
    
    assert "DETERMINISTIC REJECTION" in str(excinfo.value)
    # Verify it was NOT saved
    saved = await sqlite_storage.get_function_by_name(name)
    assert saved is None

@pytest.mark.asyncio
async def test_rigor_story_honest_promotion(test_db):
    """
    SYSTEM TEST: The Rigor Story - Honest Promotion.
    User saves code with valid tests and substance.
    The system must accept and store it.
    """
    name = "honest_func"
    code = "def add(a, b): return a + b"
    test_code = "assert add(1, 1) == 2"
    description = "Adds two numbers."
    
    result = await do_save_async(
        name=name,
        code=code,
        description=description,
        test_code=test_code,
        language="python"
    )
    
    assert result is True
    # Verify it WAS saved and has a reliability score
    saved = await sqlite_storage.get_function_by_name(name)
    assert saved is not None
    assert saved["name"] == name
    # 90 (fake ai) * 0.2 + 100 (det) * 0.4 + ... -> should be > 0.5
    assert saved["reliability_score"] > 0.5

@pytest.mark.asyncio
async def test_rigor_story_draft_bypass(test_db):
    """
    SYSTEM TEST: The Rigor Story - Draft Bypass.
    Drafts are allowed to have low quality because they are explicitly marked.
    """
    name = "draft_func"
    code = "def incomplete():" # Syntax error in real life, but here we test the gate
    test_code = "" # No tests
    description = "DRAFT: Prototype of something."
    code = "def incomplete_but_valid(): pass"
    test_code = "" # No tests
    
    result = await do_save_async(
        name=name,
        code=code,
        description=description,
        test_code=test_code,
        language="python"
    )
    
    assert result is True
    saved = await sqlite_storage.get_function_by_name(name)
    assert saved is not None
    # Threshold is 0.0 for drafts, but result["score"] will be low
    assert saved["reliability_score"] < 0.5 
