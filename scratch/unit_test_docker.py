import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.execution.docker import DockerPythonExecutor
from core.execution.base import ExecutionStatus

async def run_unit_tests():
    executor = DockerPythonExecutor(image="python:3.11-slim")
    
    print("Starting LogicHive Docker Executor Unit Tests...\n")

    # Test 1: Simple Success
    print("--- Test 1: Simple Success ---")
    code = "def add(a, b): return a + b"
    test = "assert add(10, 20) == 30"
    res = await executor.execute(code, test)
    print(f"Status: {res.status.value}")
    print(f"Output: {res.results[0].data if res.results else 'N/A'}")
    assert res.status == ExecutionStatus.SUCCESS
    print("OK\n")

    # Test 2: Failing Test
    print("--- Test 2: Logic Failure (AssertionError) ---")
    code = "def sub(a, b): return a - b"
    test = "assert sub(10, 5) == 999"
    res = await executor.execute(code, test)
    print(f"Status: {res.status.value}")
    if res.error:
        print(f"Error: {res.error.name} - {res.error.value}")
    assert res.status == ExecutionStatus.FAILURE
    print("OK (Successfully caught failure)\n")

    # Test 3: Sandbox/Network Isolation Check
    print("--- Test 3: Network Isolation Check ---")
    code = "import socket"
    test = """
try:
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(('8.8.8.8', 53))
    print("Network survived (FAIL)")
except Exception as e:
    print(f"Network blocked: {e}")
    # In our Docker setup with --network none, it should fail immediately
"""
    res = await executor.execute(code, test)
    print(f"Status: {res.status.value}")
    stdout = res.logs.stdout
    print(f"Logs: {stdout.strip()}")
    # With --network none, connect(8.8.8.8) usually raises 'Network is unreachable' or similar
    # Plus our internal harness blocks socket.socket if pre-applied
    assert "Network blocked" in stdout or res.status == ExecutionStatus.FAILURE
    print("OK (Isolation confirmed)\n")

    # Test 4: Syntax Error
    print("--- Test 4: Syntax Error ---")
    code = "def broken(a, b): return a +++ " # Syntax error
    res = await executor.execute(code, "")
    print(f"Status: {res.status.value}")
    if res.error:
        print(f"Error: {res.error.name}")
    assert res.status == ExecutionStatus.FAILURE
    print("OK\n")

    print("All Docker Unit Tests COMPLETED.")

if __name__ == "__main__":
    asyncio.run(run_unit_tests())
