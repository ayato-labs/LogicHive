import pytest

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
    # Simpler slowness that works better in subprocess
    code = "import time\ndef long_task(): time.sleep(0.5)"
    test_code = "long_task()"

    # Should pass with 10s timeout (plenty of time)
    result = await runtime_evaluator.evaluate(code, "python", test_code=test_code, timeout=10)
    assert result.score == 100.0
    # duration_ms should be around 500ms + overhead
    assert result.details["duration_ms"] >= 400


@pytest.mark.asyncio
async def test_runtime_evaluator_timeout_rejection(runtime_evaluator):
    """Verifies that the evaluator returns Score 0 and a timeout reason when exceeded."""
    # Code that sleeps for 3 seconds
    code = "import time\ndef forever(): time.sleep(3)"
    test_code = "forever()"

    # Set a very short timeout (1s) that will DEFINITELY be exceeded
    result = await runtime_evaluator.evaluate(code, "python", test_code=test_code, timeout=1)

    assert result.score == 0.0
    # On some systems it might say "Execution timed out" or "Critical Failure"
    assert any(msg in result.reason for msg in ["timed out", "Possible infinite loop"])
    assert result.details["status"] == "timeout"


@pytest.mark.asyncio
async def test_runtime_evaluator_no_test(runtime_evaluator):
    """Verifies that the evaluator returns 40 (unverified) if no test_code is provided."""
    code = "def check(): return True"
    result = await runtime_evaluator.evaluate(code, "python")

    assert result.score == 40.0
    assert "No test code provided" in result.reason
