import pytest
import asyncio
from core.execution.factory import ExecutorFactory
from core.execution.python import EphemeralPythonExecutor
from core.execution.base import ExecutionStatus

@pytest.mark.asyncio
async def test_sandbox_offline_enforcement():
    """
    Verify that code trying to access the internet is blocked in the sandbox.
    Requires uv to be configured to handle --offline.
    """
    executor = ExecutorFactory.get_executor("python")
    
    # Code that attempts to reach a known site. 
    # This should fail if --offline is correctly enforced.
    malicious_code = """
import urllib.request
try:
    response = urllib.request.urlopen('http://google.com', timeout=2)
    print("NETWORK_ACCESSIBLE")
except Exception as e:
    print(f"NETWORK_BLOCKED: {e}")
"""
    
    result = await executor.execute(malicious_code)
    
    # We expect either a failure from uv (due to --offline) 
    # or the result output to show a network error if run goes through but blocks at OS level.
    # Initially, this might PASS if we haven't implemented hardening yet.
    assert "NETWORK_BLOCKED" in result.logs.stdout or result.status != ExecutionStatus.SUCCESS
    assert "NETWORK_ACCESSIBLE" not in result.logs.stdout

@pytest.mark.asyncio
async def test_sandbox_environment_leakage():
    """
    Verify that sensitive environment variables (like API keys) are NOT leaked to the sandbox.
    """
    import os
    from core.execution.base import ExecutionStatus
    os.environ["SECRET_TOKEN_LEAK"] = "PRIVATE_DATA"
    
    executor = ExecutorFactory.get_executor("python")
    code = "import os; print(os.environ.get('SECRET_TOKEN_LEAK', 'NOT_FOUND'))"
    
    result = await executor.execute(code)
    assert "PRIVATE_DATA" not in result.logs.stdout
    assert "NOT_FOUND" in result.logs.stdout
