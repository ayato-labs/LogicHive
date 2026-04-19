import pytest
import asyncio
from core.evaluation.plugins.runtime import RuntimeEvaluator

@pytest.fixture
def runtime_evaluator():
    return RuntimeEvaluator()

@pytest.mark.asyncio
async def test_runtime_evaluator_pass(runtime_evaluator):
    """Verifies that the evaluator returns Score 100 for passing code."""
    code = "def check(): return True"
    test_code = "assert check() is True"

    result = await runtime_evaluator.evaluate(code, "python", test_code=test_code)

    assert result.score == 100.0
    assert "Tests passed" in result.reason
    assert "duration_ms" in result.details
    assert result.details["duration_ms"] >= 0

@pytest.mark.asyncio
async def test_runtime_evaluator_custom_timeout(runtime_evaluator):
    """Verifies that custom timeouts are respected."""
    code = "import asyncio\nasync def long_task(): await asyncio.sleep(0.5)"
    test_code = "import asyncio\nasyncio.run(long_task())"

    # Should pass with 5s timeout
    result = await runtime_evaluator.evaluate(code, "python", test_code=test_code, timeout=5)
    assert result.score == 100.0
    assert result.details["duration_ms"] >= 500

@pytest.mark.asyncio
async def test_runtime_evaluator_timeout_rejection(runtime_evaluator):
    """Verifies that the evaluator returns Score 0 and a timeout reason when exceeded."""
    code = "import asyncio\nasync def forever(): await asyncio.sleep(10)"
    test_code = "import asyncio\nasyncio.run(forever())"

    # Set a very short timeout that will be exceeded
    result = await runtime_evaluator.evaluate(code, "python", test_code=test_code, timeout=1)

    assert result.score == 0.0
    assert "Execution timed out" in result.reason
    assert result.details["status"] == "timeout"

@pytest.mark.asyncio
async def test_runtime_evaluator_no_test(runtime_evaluator):
    """Verifies that the evaluator returns 40 (unverified) if no test_code is provided."""
    code = "def check(): return True"
    result = await runtime_evaluator.evaluate(code, "python")

    assert result.score == 40.0
    assert "No test code provided" in result.reason
