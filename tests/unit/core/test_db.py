import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import aiosqlite

# The decorator is in core.db
from core.db import retry_on_db_lock

class MockOperationalError(aiosqlite.OperationalError):
    pass

@pytest.mark.asyncio
async def test_retry_on_db_lock_success():
    """Test that it returns the result if no error occurs."""
    mock_func = AsyncMock(return_value="success")
    decorated = retry_on_db_lock()(mock_func)

    result = await decorated("arg", kw="arg")

    assert result == "success"
    mock_func.assert_called_once_with("arg", kw="arg")

@pytest.mark.asyncio
async def test_retry_on_db_lock_retry_then_success():
    """Test that it retries once and then succeeds on 'database is locked'."""
    mock_func = AsyncMock()
    # Raise a real-looking OperationalError
    mock_func.side_effect = [
        aiosqlite.OperationalError("database is locked"),
        "success"
    ]

    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        decorated = retry_on_db_lock(max_retries=3, base_delay=0.1)(mock_func)
        result = await decorated()

        assert result == "success"
        assert mock_func.call_count == 2
        mock_sleep.assert_called_once_with(0.1)

@pytest.mark.asyncio
async def test_retry_on_db_lock_max_retries_exceeded():
    """Test that it raises the error after max_retries."""
    max_retries = 2
    mock_func = AsyncMock()
    mock_func.side_effect = aiosqlite.OperationalError("database is locked")

    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        decorated = retry_on_db_lock(max_retries=max_retries, base_delay=0.1)(mock_func)

        with pytest.raises(aiosqlite.OperationalError) as excinfo:
            await decorated()
        
        assert "database is locked" in str(excinfo.value)
        assert mock_func.call_count == max_retries + 1

@pytest.mark.asyncio
async def test_retry_on_db_lock_other_error():
    """Test that it does not retry on other OperationalErrors."""
    mock_func = AsyncMock()
    mock_func.side_effect = aiosqlite.OperationalError("some other error")

    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        decorated = retry_on_db_lock(max_retries=3)(mock_func)

        with pytest.raises(aiosqlite.OperationalError) as excinfo:
            await decorated()
        
        assert "some other error" in str(excinfo.value)
        assert mock_func.call_count == 1
        assert mock_sleep.call_count == 0
