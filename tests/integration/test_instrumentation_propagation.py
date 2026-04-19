import pytest

from core.evaluation.manager import EvaluationManager


@pytest.mark.asyncio
async def test_instrumentation_propagation_full(fake_intel):
    """
    Integration: Verify that duration_ms from RuntimeEvaluator is preserved
    through EvaluationManager and included in the final results.
    """
    manager = EvaluationManager()

    code = "def add(a, b): return a + b"
    test_code = "assert add(1, 2) == 3"

    # We use a real RuntimeEvaluator but Fake AI gate (via intelligence_isolation fixture in conftest)
    results = await manager.evaluate_all(
        code=code,
        language="python",
        test_code=test_code,
        name="test_instrumentation",
        project="integration-test",
    )

    # Check that 'runtime' evaluator data is present
    assert "runtime" in results["details"]
    runtime_res = results["details"]["runtime"]

    # Verify instrumentation metrics actually arrived (now in dict format)
    assert "duration_ms" in runtime_res["details"]
    assert runtime_res["details"]["duration_ms"] >= 0
    assert "status" in runtime_res["details"]

    # Verify the structure: it should be a dict conforming to EvaluationResult fields
    assert "score" in runtime_res
    assert "reason" in runtime_res
    assert isinstance(runtime_res, dict)
