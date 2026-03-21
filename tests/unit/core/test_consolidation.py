import pytest
import os
from core.consolidation import LogicIntelligence
from core.config import GEMINI_API_KEY

@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="Real Gemini API Key not set")
async def test_evaluate_quality_real_gemini():
    """Verifies that the strict quality gate identifies broken code using real Gemini API."""
    intel = LogicIntelligence(os.environ.get("GEMINI_API_KEY"))
    
    # 1. Broken code (Missing colon and pass)
    broken_code = "def broken_func()"
    result = await intel.evaluate_quality(broken_code)
    
    # Assert rejection (Should be near 0 for syntax errors per our prompt)
    assert result["score"] <= 10, f"Expected near 0 for syntax error, got {result['score']}"
    assert "syntax" in result["reason"].lower() or "colon" in result["reason"].lower(), f"Expected clear syntax error reason, got: {result['reason']}"
    
    # 2. Good code
    good_code = """
def calculate_factorial(n: int) -> int:
    \"\"\"Calculates the factorial of a number using recursion.\"\"\"
    if n == 0:
        return 1
    else:
        return n * calculate_factorial(n-1)
"""
    result = await intel.evaluate_quality(good_code)
    
    # Assert strict acceptance for perfect code
    assert result["score"] >= 85, f"Expected 85+ for perfect code, got {result['score']}"
    # Ensure it's not rejecting based on syntax (even if the word 'syntax' is used positively)
    reason_lower = result["reason"].lower()
    negative_indicators = ["syntax error", "missing", "invalid", "broken"]
    assert not any(indicator in reason_lower for indicator in negative_indicators), f"Found negative indicator in reason: {result['reason']}"
