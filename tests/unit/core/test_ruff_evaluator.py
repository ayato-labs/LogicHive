import pytest
from core.evaluation.plugins.static import RuffEvaluator


@pytest.mark.asyncio
async def test_ruff_evaluator_clean_code():
    evaluator = RuffEvaluator()
    code = "def hello():\n    print('hello')\n"
    result = await evaluator.evaluate(code, "python")
    # If ruff is not installed, it returns 100. If it is and clean, 100.
    assert result.score == 100.0


@pytest.mark.asyncio
async def test_ruff_evaluator_with_issues():
    evaluator = RuffEvaluator()
    # Unused import (F401)
    code = "import os\ndef hello():\n    pass\n"
    result = await evaluator.evaluate(code, "python")
    # If ruff is installed, score should be < 100.
    # We check if it ran by looking at the reason or score.
    # If ruff check skipped due to environment error, we should skip the test.
    if "Ruff check skipped" in result.reason:
        pytest.skip("Ruff not found or failed in environment")

    assert result.score < 100.0
    assert "Ruff: Found" in result.reason
