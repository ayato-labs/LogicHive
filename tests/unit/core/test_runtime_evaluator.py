import pytest
from core.evaluation.plugins.runtime import RuntimeEvaluator

@pytest.fixture
def runtime_evaluator():
    # Ensure the python executor is registered (it should be via import)
    return RuntimeEvaluator()

@pytest.mark.asyncio
async def test_runtime_evaluator_pass(runtime_evaluator):
    """Verifies that the evaluator returns Score 100 for passing code."""
    code = "def check(): return True"
    test_code = "assert check() is True"
    
    result = await runtime_evaluator.evaluate(code, "python", test_code=test_code)
    
    assert result.score == 100.0
    assert "Tests passed" in result.reason

@pytest.mark.asyncio
async def test_runtime_evaluator_fail(runtime_evaluator):
    """Verifies that the evaluator returns Score 0 for failing tests."""
    code = "def check(): return False"
    test_code = "assert check() is True"
    
    result = await runtime_evaluator.evaluate(code, "python", test_code=test_code)
    
    assert result.score == 0.0
    assert "Critical Failure" in result.reason
    assert "AssertionError" in result.reason

@pytest.mark.asyncio
async def test_runtime_evaluator_no_test(runtime_evaluator):
    """Verifies that the evaluator returns 40 (unverified) if no test_code is provided."""
    code = "def check(): return True"
    result = await runtime_evaluator.evaluate(code, "python")
    
    assert result.score == 40.0
    assert "No test code provided" in result.reason
