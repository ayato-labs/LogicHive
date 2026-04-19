import pytest
from core.execution.factory import ExecutorFactory
from core.execution.base import ExecutionStatus

@pytest.mark.asyncio
async def test_executor_large_output_resilience():
    """
    Integration: Verify that the Python executor can handle large stdout streams 
    without deadlocking on the pipe buffer.
    """
    executor = ExecutorFactory.get_executor("python")
    
    # Generate ~1MB of output
    code = "print('A' * 1024 * 1024)"
    test_code = "pass"
    
    # Use a safe timeout
    result = await executor.execute(
        code=code,
        test_code=test_code,
        timeout=10
    )
    
    # If using communicate(), this should succeed. 
    # If using wait() without reading pipes, this would hang indefinitely.
    assert result.status == ExecutionStatus.SUCCESS
    assert len(result.logs.stdout) >= 1024 * 1024
    assert result.duration < 5 # Should be fast
