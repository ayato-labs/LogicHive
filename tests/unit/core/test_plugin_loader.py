import pytest
from core.evaluation.manager import EvaluationManager

def test_plugin_loading():
    manager = EvaluationManager()
    # Check if evaluators are loaded
    evaluator_names = [ev.name for ev in manager.evaluators]
    print(f"Loaded evaluators: {evaluator_names}")
    
    # These should be present after migration to plugins/
    assert "structural" in evaluator_names
    assert "python_static" in evaluator_names
    assert "ruff" in evaluator_names
    assert "eslint" in evaluator_names
    assert "ai_gate" in evaluator_names

@pytest.mark.asyncio
async def test_evaluate_all_with_plugins():
    manager = EvaluationManager()
    code = "def hello():\n    pass"
    result = await manager.evaluate_all(code, "python")
    
    assert "score" in result
    assert "details" in result
    # Python results should have at least structural and python_static (and others if available)
    assert "structural" in result["details"]
    assert "python_static" in result["details"]
