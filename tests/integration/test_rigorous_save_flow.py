import pytest
from src.orchestrator import do_save_async, do_search_async
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_rigorous_save_flow_blocked_by_security():
    """Integration: A function with 'eval' should be blocked even if AI says it's good."""
    # 1. Code that has 'eval' (Critical security flaw)
    bad_code = "def runner(cmd): eval(cmd)"
    
    # Even if AI were to give it a high score (via fake), 
    # the static filter in EvaluationManager should crush it.
    try:
        await do_save_async(
            name="unsafe_runner",
            code=bad_code,
            description="A dangerous runner",
            test_code="def test_none(): assert True" # Minimum test to avoid Sophistry gate
        )
        pytest.fail("Safety Gate failed to raise ValidationError for 'eval'")
    except Exception as e:
        assert "Security" in str(e) or "Gate" in str(e)
    
    # Verify it's NOT in the database
    search_res = await do_search_async(query="unsafe_runner")
    # Search might return nothing or items not matching the name
    assert not any(r["name"] == "unsafe_runner" for r in search_res)

@pytest.mark.asyncio
async def test_rigorous_save_flow_blocked_by_dependencies():
    """Integration: A function with hallucinated imports should be blocked."""
    # Code with fake import
    bad_code = "import mysterious_ai_lib\nprint('hello')"
    
    try:
        await do_save_async(
            name="hallucinated_util",
            code=bad_code,
            description="A utility with missing deps",
            test_code="def test_none(): assert True"
        )
        pytest.fail("Safety Gate failed to raise ValidationError for missing dependency")
    except Exception as e:
        assert "Dependency" in str(e) or "Gate" in str(e)

@pytest.mark.asyncio
async def test_rigorous_save_flow_success():
    """Integration: Clean code with tests should pass full pipeline."""
    clean_code = "def multiply(a, b): return a * b"
    test_code = "def test_multiply(): assert multiply(2, 3) == 6"
    
    result = await do_save_async(
        name="math_multiply",
        code=clean_code,
        description="Multiplies two numbers",
        tags=["math", "basic"],
        test_code=test_code
    )
    
    assert result is True # sqlite_storage.upsert_function returns True on success
    
    # Verify it IS in the database
    search_res = await do_search_async(query="math_multiply")
    assert len(search_res) > 0
    assert any(r["name"] == "math_multiply" for r in search_res)
