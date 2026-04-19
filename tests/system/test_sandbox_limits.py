import asyncio
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from core.execution.base import ExecutionStatus
from core.execution.python import EphemeralPythonExecutor


@pytest.mark.asyncio
async def test_memory_limit_enforcement():
    executor = EphemeralPythonExecutor()

    # Code that consumes a lot of memory
    # We create a large list to hit the limit
    code = """
import time
large_list = []
for i in range(10**7): # This will consume significant memory
    large_list.append(" " * 100)
    if i % 10000 == 0:
        time.sleep(0.01)
"""

    # Set a small limit (50MB)
    result = await executor.execute(code, memory_limit_mb=50, timeout=10)

    print(f"\nMemory Test Status: {result.status}")
    print(f"Memory Test Error: {result.logs.stderr}")

    assert result.status == ExecutionStatus.MEMORY_LIMIT
    assert "Memory limit exceeded" in result.logs.stderr


@pytest.mark.asyncio
async def test_timeout_enforcement():
    executor = EphemeralPythonExecutor()

    code = "import time; time.sleep(10)"

    # Set a small timeout
    result = await executor.execute(code, timeout=2)

    print(f"\nTimeout Test Status: {result.status}")

    assert result.status == ExecutionStatus.TIMEOUT


if __name__ == "__main__":
    asyncio.run(test_memory_limit_enforcement())
    asyncio.run(test_timeout_enforcement())
