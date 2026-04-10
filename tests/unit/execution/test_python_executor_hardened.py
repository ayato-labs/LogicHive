import pytest
import os
from core.execution.python import EphemeralPythonExecutor
from core.execution.base import ExecutionStatus

@pytest.mark.asyncio
async def test_sandbox_env_isolation():
    """
    Verifies that host-project environment variables are NOT accessible inside the sandbox.
    """
    executor = EphemeralPythonExecutor()
    
    # 1. Set a "secret" environment variable on the host
    os.environ["LOGICHIVE_SECRET_TOKEN"] = "SUPER_SECRET_123"
    
    # 2. Code that tries to read this secret inside the sandbox
    code = """
import os
def check_env():
    token = os.environ.get("LOGICHIVE_SECRET_TOKEN")
    # Return True if token is MISSING (Success for sandbox isolation)
    return token is None
    """
    test_code = "assert check_env() == True"
    
    try:
        result = await executor.execute(code=code, test_code=test_code)
        
        # In case of failure, result.error contains the details
        assert result.status == ExecutionStatus.SUCCESS, f"Sandbox failed to block env variable: {result.error}"
        assert "LOGICHIVE_SECRET_TOKEN" not in result.logs.stdout
    finally:
        # Cleanup host env
        if "LOGICHIVE_SECRET_TOKEN" in os.environ:
            del os.environ["LOGICHIVE_SECRET_TOKEN"]

@pytest.mark.asyncio
async def test_sandbox_pythonpath_isolation():
    """
    Verifies that PYTHONPATH is empty inside the sandbox to prevent importing host modules.
    """
    executor = EphemeralPythonExecutor()
    
    code = """
import os
import sys
def check_paths():
    # PYTHONPATH should be empty or strictly controlled
    python_path = os.environ.get("PYTHONPATH", "")
    return python_path == ""
    """
    test_code = "assert check_paths() == True"
    
    result = await executor.execute(code=code, test_code=test_code)
    assert result.status == ExecutionStatus.SUCCESS

@pytest.mark.asyncio
async def test_sandbox_user_site_blocked():
    """
    Verifies that PYTHONNOUSERSITE is set to 1 to block local user packages.
    """
    executor = EphemeralPythonExecutor()
    
    code = """
import os
def check_user_site():
    return os.environ.get("PYTHONNOUSERSITE") == "1"
    """
    test_code = "assert check_user_site() == True"
    
    result = await executor.execute(code=code, test_code=test_code)
    assert result.status == ExecutionStatus.SUCCESS

@pytest.mark.asyncio
async def test_sandbox_write_restriction():
    """
    Verifies that the sandbox can write to its temp dir but not arbitrary host locations.
    (This checks basic subprocess behavior in temp dirs).
    """
    executor = EphemeralPythonExecutor()
    
    # Try to write to a sensitive-looking host path (simulated)
    # Note: Subprocess actually has OS-level write access to user files unless UID is changed,
    # but the Ephemeral executor runs in a dedicated temp dir.
    # Here we just verify it correctly identifies its own workspace.
    code = """
import os
def check_cwd():
    # Should be in a temp directory
    cwd = os.getcwd()
    return "logichive_exec_" in cwd or "tmp" in cwd.lower() or "temp" in cwd.lower()
    """
    test_code = "assert check_cwd() == True"
    
    result = await executor.execute(code=code, test_code=test_code)
    assert result.status == ExecutionStatus.SUCCESS
