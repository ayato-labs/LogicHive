import pytest
from core.evaluation.manager import EvaluationManager
from core.evaluation.base import EvaluationResult

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
        project="integration-test"
    )
    
    # Check that 'runtime' evaluator data is present
    assert "runtime" in results["details"]
    runtime_details = results["details"]["runtime"]["details"]
    
    # Verify instrumentation metrics actually arrived
    assert "duration_ms" in runtime_details
    assert runtime_details["duration_ms"] >= 0
    assert "status" in runtime_details
    
    # Also verify the EvaluationManager returned them in its own top-level details if we updated it
    # Note: In EvaluationManager.evaluate_all, we return a dict. Let's check its structure.
    # From manager.py: results is a dict mapping name -> EvaluationResult
    assert isinstance(results["details"]["runtime"], EvaluationResult)
