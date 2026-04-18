import pytest
import os
import shutil
import tempfile
from src.core.evaluation.plugins.security_static import SecurityStaticEvaluator
from src.core.evaluation.plugins.dependency_vouch import DependencyVouchEvaluator
from src.core.evaluation.plugins.metrics_gate import MetricsGateEvaluator

@pytest.mark.asyncio
async def test_security_static_evaluator():
    evaluator = SecurityStaticEvaluator()
    
    # 1. Dangerous eval
    bad_code = "def insecure(): eval('1+1')"
    res = await evaluator.evaluate(bad_code, "python")
    assert res.score < 100
    assert "eval" in res.reason.lower()
    
    # 2. Hardcoded secret
    secret_code = "API_KEY = 'sk-1234567890abcdef'"
    res = await evaluator.evaluate(secret_code, "python")
    assert res.score < 100
    assert "secret" in res.reason.lower()
    
    # 3. Clean code
    clean_code = "def add(a, b): return a + b"
    res = await evaluator.evaluate(clean_code, "python")
    assert res.score == 100

@pytest.mark.asyncio
async def test_dependency_vouch_evaluator():
    evaluator = DependencyVouchEvaluator()
    
    # 1. Hallucinated import (unlikely to exist in stdlib/local)
    bad_code = "import non_existent_library_xyz\nprint('hello')"
    # Create temp requirements.txt to simulate project context
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            # 1. No requirements.txt -> should flag
            res = await evaluator.evaluate(bad_code, "python")
            assert res.score < 100
            
            # 2. Add to requirements.txt -> should pass
            with open("requirements.txt", "w") as f:
                f.write("non_existent_library_xyz==1.0.0")
            
            # Re-instantiate or trigger re-scan of manifest
            new_evaluator = DependencyVouchEvaluator()
            res = await new_evaluator.evaluate(bad_code, "python")
            assert res.score == 100, f"Expected 100 with requirements.txt, got {res.score}. Reason: {res.reason}"
        finally:
            os.chdir(old_cwd)

@pytest.mark.asyncio
async def test_metrics_gate_evaluator():
    evaluator = MetricsGateEvaluator()
    
    # 1. Too complex code
    complex_code = "def complex_func(x):\n"
    for i in range(12):
        complex_code += f"    if x > {i}: print({i})\n"
    complex_code += "    return x"
    
    res = await evaluator.evaluate(complex_code, "python")
    assert res.score < 100
    assert "complex" in res.reason.lower()
    
    # 2. Too many parameters
    many_params = "def too_many(a, b, c, d, e, f, g): pass" # 7 parameters
    res = await evaluator.evaluate(many_params, "python")
    assert res.score < 100
    assert "parameters" in res.reason.lower()
