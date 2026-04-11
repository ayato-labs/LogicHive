import pytest
from unittest.mock import MagicMock, AsyncMock
from core.evaluation.manager import EvaluationManager
from core.evaluation.plugins.ai import AIGateEvaluator
from core.evaluation.base import EvaluationResult

@pytest.mark.asyncio
async def test_hybrid_gate_integration_high_rigor():
    """
    Integration test: High rigor asset.
    Good code + Good tests -> High score.
    """
    manager = EvaluationManager()
    
    # We use LogicIntelligence as a mock to simulate LLM behavior in integration test
    mock_intel = MagicMock()
    mock_intel.evaluate_quality = AsyncMock(return_value={
        "score": 95, 
        "reason": "Expertly crafted logic with comprehensive tests."
    })
    
    # Inject mock intel into AI gate
    for ev in manager.evaluators:
        if isinstance(ev, AIGateEvaluator):
            ev.intel = mock_intel
            
    code = "def process_data(data): return [x * 2 for x in data]"
    test_code = "# Minimal Rigor\nassert True\nassert True\nassert True"
    
    result = await manager.evaluate_all(code, "python", test_code=test_code)
    
    # Det layer should give 100
    # AI layer gives 95
    
    assert result["score"] > 80
    assert "Satisfactory test density" in result["reason"]
    assert "AI Opinion:" in result["reason"]

@pytest.mark.asyncio
async def test_hybrid_gate_integration_sophistry_rejection():
    """
    Integration test: Sophistry rejection.
    AI says 90, but Deterministic says 0 (no assertions).
    Final score must be 0.
    """
    manager = EvaluationManager()
    
    mock_intel = MagicMock()
    mock_intel.evaluate_quality = AsyncMock(return_value={
        "score": 90, 
        "reason": "This code looks perfect and very safe."
    })
    
    for ev in manager.evaluators:
        if isinstance(ev, AIGateEvaluator):
            ev.intel = mock_intel
            
    code = "def complex_logic(): pass"
    test_code = "complex_logic()" # No assert -> Deterministic Rejection
    
    result = await manager.evaluate_all(code, "python", test_code=test_code)
    
    assert result["score"] == 0.0
    assert "DETERMINISTIC REJECTION" in result["reason"]
    # AI score 90 should be saved in details but ignored for final
    assert result["details"]["ai_gate"]["score"] == 90.0
