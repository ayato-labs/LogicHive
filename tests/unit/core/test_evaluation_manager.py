import pytest
from core.evaluation.manager import EvaluationManager
from core.evaluation.plugins.ai import AIGateEvaluator

@pytest.mark.asyncio
async def test_evaluation_manager_rejection(fake_intel):
    """Verifies that EvaluationManager blocks code when an evaluator returns score=0."""
    manager = EvaluationManager()
    
    # 1. Structural failure (Unbalanced brackets)
    bad_code = "def hello("
    result = await manager.evaluate_all(bad_code, "python")
    assert result["score"] == 0
    assert "unbalanced brackets" in result["reason"]

@pytest.mark.asyncio
async def test_evaluation_manager_success(fake_intel):
    """Verifies that EvaluationManager passes good code with high score."""
    manager = EvaluationManager()
    good_code = "def hello():\n    pass"
    result = await manager.evaluate_all(good_code, "python")
    assert result["score"] >= 80
    assert "structural" in result["details"]

@pytest.mark.asyncio
async def test_ai_gate_evaluator_isolated(fake_intel):
    """Unit test for AIGateEvaluator using FakeLogicIntelligence (no MagicMock)."""
    evaluator = AIGateEvaluator(intel=fake_intel)
    
    # Normal case
    result = await evaluator.evaluate("def my_func(): pass", "python")
    assert result.score == 90 # Hardcoded in FakeLogicIntelligence
    
    # Triggering 'error' response in fake
    result_fail = await evaluator.evaluate("code with error in reason", "python")
    assert result_fail.score == 10
