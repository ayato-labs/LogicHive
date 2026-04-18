import pytest
import ast
from src.core.evaluation.plugins.security_static import SecurityStaticEvaluator, SecurityVisitor

@pytest.mark.asyncio
async def test_security_eval_detection():
    """Unit: Detect dangerous eval() calls."""
    evaluator = SecurityStaticEvaluator()
    code = "def dangerous(): eval('os.system(\"rm -rf /\")')"
    result = await evaluator.evaluate(code, "python")
    assert result.score == 60.0 # 100 - 40
    assert "eval" in result.reason.lower()

@pytest.mark.asyncio
async def test_security_secret_detection():
    """Unit: Detect hardcoded high-entropy secrets."""
    evaluator = SecurityStaticEvaluator()
    code = "AWS_SECRET_KEY = 'AKIAI47BCDEFGHIKLMNOPT'"
    result = await evaluator.evaluate(code, "python")
    assert result.score == 60.0
    assert "secret" in result.reason.lower()

@pytest.mark.asyncio
async def test_security_subprocess_shell_true():
    """Unit: Detect shell=True in subprocess."""
    evaluator = SecurityStaticEvaluator()
    code = "import subprocess\nsubprocess.run('ls', shell=True)"
    result = await evaluator.evaluate(code, "python")
    assert result.score == 60.0
    assert "shell=true" in result.reason.lower()

@pytest.mark.asyncio
async def test_security_sql_injection():
    """Unit: Detect obvious SQL injection patterns via regex."""
    evaluator = SecurityStaticEvaluator()
    code = "db.execute(f'SELECT * FROM users WHERE id={user_id}')"
    result = await evaluator.evaluate(code, "python")
    assert result.score == 60.0
    assert "sql injection" in result.reason.lower()

@pytest.mark.asyncio
async def test_security_syntax_error_resilience():
    """Unit: Ensure evaluator doesn't crash on invalid Python code."""
    evaluator = SecurityStaticEvaluator()
    invalid_code = "def broken(:"
    result = await evaluator.evaluate(invalid_code, "python")
    assert result.score == 0.0
    assert "syntax error" in result.reason.lower()

@pytest.mark.asyncio
async def test_security_clean_code():
    """Unit: Correct code should get 100."""
    evaluator = SecurityStaticEvaluator()
    clean_code = "def safe_add(a, b):\n    return a + b"
    result = await evaluator.evaluate(clean_code, "python")
    assert result.score == 100.0
