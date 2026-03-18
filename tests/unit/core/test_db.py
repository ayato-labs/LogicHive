import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# Mock aiosqlite before importing core.db
mock_aiosqlite = MagicMock()
class MockOperationalError(Exception):
    pass
mock_aiosqlite.OperationalError = MockOperationalError
sys.modules["aiosqlite"] = mock_aiosqlite

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.db import retry_on_db_lock

# Define a custom exception for testing non-lock errors
class OtherOperationalError(MockOperationalError):
    pass

async def test_retry_on_db_lock_success():
    """Test that it returns the result if no error occurs."""
    mock_func = AsyncMock(return_value="success")
    decorated = retry_on_db_lock()(mock_func)

    result = await decorated("arg", kw="arg")

    assert result == "success"
    mock_func.assert_called_once_with("arg", kw="arg")

async def test_retry_on_db_lock_retry_then_success():
    """Test that it retries once and then succeeds."""
    mock_func = AsyncMock()
    # Raise 'database is locked' then return success
    mock_func.side_effect = [
        MockOperationalError("database is locked"),
        "success"
    ]

    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        decorated = retry_on_db_lock(max_retries=3, base_delay=0.1)(mock_func)
        result = await decorated()

        assert result == "success"
        assert mock_func.call_count == 2
        mock_sleep.assert_called_once_with(0.1)

async def test_retry_on_db_lock_max_retries_exceeded():
    """Test that it raises the error after max_retries."""
    max_retries = 2
    mock_func = AsyncMock()
    mock_func.side_effect = MockOperationalError("database is locked")

    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        decorated = retry_on_db_lock(max_retries=max_retries, base_delay=0.1)(mock_func)

        try:
            await decorated()
            assert False, "Should have raised MockOperationalError"
        except MockOperationalError as e:
            assert "database is locked" in str(e)

        # Initial call + max_retries = 3 calls
        assert mock_func.call_count == max_retries + 1
        assert mock_sleep.call_count == max_retries

async def test_retry_on_db_lock_other_error():
    """Test that it does not retry on other errors."""
    mock_func = AsyncMock()
    mock_func.side_effect = OtherOperationalError("some other error")

    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        decorated = retry_on_db_lock(max_retries=3)(mock_func)

        try:
            await decorated()
            assert False, "Should have raised OtherOperationalError"
        except OtherOperationalError as e:
            assert "some other error" in str(e)

        assert mock_func.call_count == 1
        assert mock_sleep.call_count == 0

async def test_retry_on_db_lock_exponential_backoff():
    """Test that exponential backoff works correctly."""
    mock_func = AsyncMock()
    mock_func.side_effect = [
        MockOperationalError("database is locked"),
        MockOperationalError("database is locked"),
        MockOperationalError("database is locked"),
        "success"
    ]

    base_delay = 0.2
    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        decorated = retry_on_db_lock(max_retries=5, base_delay=base_delay)(mock_func)
        await decorated()

        # Retries: 0 (delay 0.2*2^0=0.2), 1 (delay 0.2*2^1=0.4), 2 (delay 0.2*2^2=0.8)
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(0.2)
        mock_sleep.assert_any_call(0.4)
        mock_sleep.assert_any_call(0.8)

async def run_all_tests():
    """Entry point for pytest-like discovery or manual run."""
    await test_retry_on_db_lock_success()
    await test_retry_on_db_lock_retry_then_success()
    await test_retry_on_db_lock_max_retries_exceeded()
    await test_retry_on_db_lock_other_error()
    await test_retry_on_db_lock_exponential_backoff()

if __name__ == "__main__":
    asyncio.run(run_all_tests())
    print("All tests passed!")
