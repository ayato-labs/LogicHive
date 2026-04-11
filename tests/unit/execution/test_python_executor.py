import pytest

from core.execution.base import ExecutionStatus
from core.execution.python import EphemeralPythonExecutor


@pytest.mark.asyncio
async def test_python_executor_success():
    """Verifies that valid Python code executes successfully."""
    executor = EphemeralPythonExecutor()
    code = "def add(a, b): return a + b"
    test_code = "assert add(2, 3) == 5"

    result = await executor.execute(code, test_code)

    assert result.status == ExecutionStatus.SUCCESS
    assert "Tests Passed" in result.results[0].data
    assert result.duration > 0

@pytest.mark.asyncio
async def test_python_executor_failure():
    """Verifies that failing assertions are captured as FAILURE."""
    executor = EphemeralPythonExecutor()
    code = "def add(a, b): return a + b"
    test_code = "assert add(2, 3) == 6"  # Wrong expectation

    result = await executor.execute(code, test_code)

    assert result.status == ExecutionStatus.FAILURE
    assert result.error is not None
    assert "AssertionError" in result.error.name

@pytest.mark.asyncio
async def test_python_executor_timeout():
    """Verifies that infinite loops are killed by the timeout."""
    executor = EphemeralPythonExecutor()
    code = "import time\nwhile True: time.sleep(0.1)"

    # Set a more realistic timeout for the test to allow uv startup and sync (Windows)
    result = await executor.execute(code, timeout=10)

    assert result.status == ExecutionStatus.TIMEOUT
    # Note: stderr might be empty if killed forcefully on Windows

@pytest.mark.asyncio
async def test_python_executor_with_dependencies():
    """
    Verifies that 'uv run --with' works for external dependencies.
    """
    executor = EphemeralPythonExecutor()
    code = "import numpy as np\ndef check(): return np.array([1, 2, 3]).sum()"
    test_code = "assert check() == 6"

    result = await executor.execute(code, test_code, dependencies=["numpy"])

    assert result.status == ExecutionStatus.SUCCESS
    assert "Tests Passed" in result.results[0].data

@pytest.mark.asyncio
async def test_python_executor_syntax_error():
    """Verifies that syntax errors in the user code are captured."""
    executor = EphemeralPythonExecutor()
    code = "def broken_syntax(:" # Missing paren

    result = await executor.execute(code)

    assert result.status == ExecutionStatus.FAILURE
    assert "SyntaxError" in result.error.name
