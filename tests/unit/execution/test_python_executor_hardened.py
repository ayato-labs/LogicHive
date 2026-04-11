import asyncio
import subprocess
import sys

import psutil
import pytest

from core.execution.base import ExecutionStatus
from core.execution.python import EphemeralPythonExecutor


@pytest.fixture
def executor():
    return EphemeralPythonExecutor()

@pytest.mark.asyncio
async def test_kill_process_tree_unit(executor):
    """
    Unit test for _kill_process_tree helper. 
    Spawns a process with children and verifies they are all killed.
    """
    # Spawn a shell that spawns a sleep
    # In Windows: cmd /c "start /b timeout 100" or similar
    # For cross-platform test, we'll use a simple python sleeper
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; import subprocess; subprocess.Popen(['python', '-c', 'import time; time.sleep(100)']); time.sleep(100)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    pid = proc.pid
    p = psutil.Process(pid)
    await asyncio.sleep(0.5) # Wait for child to spawn

    children = p.children(recursive=True)
    assert len(children) >= 1

    # Kill tree
    executor._kill_process_tree(pid)

    # Verify all dead
    await asyncio.sleep(0.2)
    assert not p.is_running()
    for child in children:
        assert not child.is_running()

@pytest.mark.asyncio
async def test_memory_monitor_trigger(executor):
    """
    Verifies that the executor triggers MEMORY_LIMIT when using memory-intensive code.
    Uses a smaller limit for speed.
    """
    # This is a unit-level integration test
    code = """
import time
# Rapidly consume memory
data = bytearray(80 * 1024 * 1024) # 80MB
time.sleep(2) # Keep it alive long enough for monitor
"""
    # Limit to 50MB
    result = await executor.execute(code, memory_limit_mb=50, timeout=10)

    assert result.status == ExecutionStatus.MEMORY_LIMIT
    assert "Memory limit exceeded" in result.logs.stderr

@pytest.mark.asyncio
async def test_timeout_monitor_trigger(executor):
    """Verifies timeout triggers status."""
    code = "import time; time.sleep(10)"
    result = await executor.execute(code, timeout=1)

    assert result.status == ExecutionStatus.TIMEOUT

