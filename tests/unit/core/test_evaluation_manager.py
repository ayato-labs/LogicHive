from unittest.mock import AsyncMock

import pytest

from core.evaluation.base import EvaluationResult
from core.evaluation.manager import EvaluationManager
from core.evaluation.plugins.ai import AIGateEvaluator


@pytest.mark.asyncio
async def test_evaluation_manager_rejection(fake_intel):
    """Verifies that EvaluationManager blocks code with structural errors."""
    manager = EvaluationManager()

    # Structural failure (Unbalanced brackets)
    bad_code = "def hello("
    result = await manager.evaluate_all(bad_code, "python", is_draft=True)
    assert result["score"] == 0
    assert "structural error" in result["reason"].lower()

@pytest.mark.asyncio
async def test_evaluation_manager_deterministic_veto(fake_intel):
    """Verifies that DETERMINISTIC REJECTION (score=0) forces final score to 0."""
    manager = EvaluationManager()

    # Valid code BUT NO assertions in tests -> Deterministic score 0
    code = "def add(a, b): return a + b"
    test_code = "add(1, 1)" # No assert

    result = await manager.evaluate_all(code, "python", test_code=test_code)
    assert result["score"] == 0.0
    assert "DETERMINISTIC REJECTION" in result["reason"]

@pytest.mark.asyncio
async def test_weight_calculation_correctness(fake_intel):
    """
    Verifies the 4:3:2:1 weight distribution.
    40% Det, 30% Run, 20% AI, 10% Static.
    """
    manager = EvaluationManager()

    # Manually patch the instances in the manager
    for ev in manager.evaluators:
        if ev.name == "deterministic":
            ev.evaluate = AsyncMock(return_value=EvaluationResult(score=100.0, reason="Facts ok"))
        elif ev.name == "runtime":
            ev.evaluate = AsyncMock(return_value=EvaluationResult(score=80.0, reason="Runtime ok"))
        elif ev.name == "ai_gate":
            ev.evaluate = AsyncMock(return_value=EvaluationResult(score=90.0, reason="AI ok"))
        elif ev.name == "ruff":
            ev.evaluate = AsyncMock(return_value=EvaluationResult(score=100.0, reason="Static ok"))
        elif ev.name == "structural":
            ev.evaluate = AsyncMock(return_value=EvaluationResult(score=100.0, reason="Struct ok"))

    # Expected: (100*0.4) + (80*0.3) + (90*0.2) + (100*0.1) = 40 + 24 + 18 + 10 = 92.0
    result = await manager.evaluate_all("def f(): pass", "python", is_draft=True)
    assert result["score"] == pytest.approx(92.0)

@pytest.mark.asyncio
async def test_ai_auditor_veto_theater(fake_intel):
    """Verifies that AI score < 30 (Quality Theater) triggers rejection."""
    manager = EvaluationManager()

    for ev in manager.evaluators:
        if ev.name == "ai_gate":
            ev.evaluate = AsyncMock(return_value=EvaluationResult(score=20.0, reason="Quality Theater Detected"))
        elif ev.name == "structural":
            ev.evaluate = AsyncMock(return_value=EvaluationResult(score=100.0, reason="Struct ok"))
        else:
            ev.evaluate = AsyncMock(return_value=EvaluationResult(score=100.0, reason="ok"))

    result = await manager.evaluate_all("def fake(): pass", "python", is_draft=True)
    assert result["score"] == 0.0
    assert "VETO" in result["reason"]

@pytest.mark.asyncio
async def test_ai_gate_evaluator_isolated(fake_intel):
    """Unit test for AIGateEvaluator using FakeLogicIntelligence (no MagicMock)."""
    evaluator = AIGateEvaluator(intel=fake_intel)

    # Normal case
    result = await evaluator.evaluate("def my_func(): pass", "python")
    assert result.score == 90

    # Triggering 'error' response in fake
    result_fail = await evaluator.evaluate("code with error in reason", "python")
    assert result_fail.score == 10
