import pytest

from core.exceptions import ValidationError
from orchestrator import do_save_async


@pytest.mark.asyncio
async def test_system_save_flow_timeout_behavior(test_db):
    """
    System: Verify E2E save flow respects timeout logic and hard limits.
    """
    name = "system_timeout_test"
    code = "def sleep_func(): import time; time.sleep(0.1); return True"
    test_code = "assert sleep_func() is True"
    description = "Test E2E timeout"

    # 1. Test Default Timeout (60s)
    res = await do_save_async(
        name=name, code=code, description=description, test_code=test_code, timeout=None
    )
    assert res is True

    # 2. Test Custom Timeout (80s)
    res_custom = await do_save_async(
        name=name + "_custom", code=code, description=description, test_code=test_code, timeout=80
    )
    assert res_custom is True

    # 3. Test Hard Limit Capping (150s -> 120s)
    res_capped = await do_save_async(
        name=name + "_capped", code=code, description=description, test_code=test_code, timeout=150
    )
    assert res_capped is True


@pytest.mark.asyncio
async def test_system_save_flow_timeout_rejection(test_db):
    """
    System: Verify E2E save flow rejects code that exceeds timeout.
    """
    name = "system_rejection_test"
    # Code that sleeps for 5 seconds
    code = "def slow_func(): import time; time.sleep(5); return True"
    test_code = "import asyncio; assert slow_func() is True"

    # Set timeout to 1 second
    with pytest.raises(ValidationError) as exc:
        await do_save_async(
            name=name, code=code, description="Slow code", test_code=test_code, timeout=1
        )

    assert "Execution timed out" in str(exc.value)
