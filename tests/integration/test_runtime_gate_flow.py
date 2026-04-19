import pytest

from core.evaluation.manager import EvaluationManager
from core.evaluation.plugins.ai import AIGateEvaluator


@pytest.fixture
def eval_manager(fake_intel):
    manager = EvaluationManager()
    # Inject fake_intel into AIGateEvaluator if present
    ai_gate = manager.get_evaluator("ai_gate")
    if ai_gate and isinstance(ai_gate, AIGateEvaluator):
        ai_gate.intel = fake_intel
    return manager


@pytest.mark.asyncio
async def test_runtime_gate_blocks_save(eval_manager):
    """Verifies that the Quality Gate as a whole fails if runtime tests fail."""
    code = "def divide(a, b): return a / b"
    # Provide a test that will fail (DivisionByZero)
    test_code = "assert divide(10, 0) == 5"

    result = await eval_manager.evaluate_all(code=code, language="python", test_code=test_code)

    assert result["score"] == 0.0
    assert "Critical Logic Failure" in result["reason"]
    assert "ZeroDivisionError" in result["reason"]


@pytest.mark.asyncio
async def test_runtime_gate_passes_success(eval_manager):
    """Verifies that the Quality Gate passes when runtime tests succeed."""
    code = "def multiply(a, b): return a * b"
    test_code = "assert multiply(2, 5) == 10"

    result = await eval_manager.evaluate_all(code=code, language="python", test_code=test_code)

    # Even if AI/Static give high scores, the runtime must pass
    assert result["score"] > 0
    assert result["details"]["runtime"]["score"] == 100.0


@pytest.mark.asyncio
async def test_runtime_gate_timeout_blocks(eval_manager):
    """Verifies that a timeout in runtime leads to a score of 0."""
    code = "import time\ndef hang():\n    while True: time.sleep(0.01)"
    test_code = "assert hang() is None"

    # We pass a short timeout via kwargs
    result = await eval_manager.evaluate_all(
        code=code,
        language="python",
        test_code=test_code,
        timeout=2,  # Short timeout for test
    )

    assert result["score"] == 0.0
    assert "Critical Logic Failure" in result["reason"]
    assert "timed out" in result["reason"].lower()
