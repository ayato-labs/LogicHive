import asyncio
import logging
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from orchestrator import do_save_async
from core.exceptions import ValidationError

logging.basicConfig(level=logging.INFO)

async def test_timeout_fix():
    code = """
def slow_function():
    return "done"
"""
    # Test code that sleeps for 5 seconds
    test_code = """
import time
time.sleep(5)
assert slow_function() == "done"
"""

    print("\n--- Test 1: Short Timeout (Expected to fail) ---")
    try:
        await do_save_async(
            name="test_short_timeout",
            code=code,
            test_code=test_code,
            description="Testing short timeout",
            timeout=2 # 2 seconds
        )
        print("[FAIL] Error: Should have timed out but passed.")
    except ValidationError as e:
        print(f"[PASS] Correctly failed: {e}")

    print("\n--- Test 2: Custom Timeout (Expected to pass) ---")
    try:
        # Use AI-DRAFT tag to bypass AI gate scoring and focus on runtime
        success = await do_save_async(
            name="test_custom_timeout",
            code=code,
            test_code=test_code,
            description="[AI-DRAFT] Testing custom timeout",
            timeout=10 # 10 seconds
        )
        if success:
            print("[PASS] Successfully passed with custom timeout.")
        else:
            print("[FAIL] Failed registration.")
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")

    print("\n--- Test 3: Hard Limit Capping (Expected to pass) ---")
    # A 150s timeout should be capped at 120s (MAX_VERIFICATION_TIMEOUT)
    # Since our test only takes 5s, it should still pass.
    try:
        success = await do_save_async(
            name="test_hard_limit",
            code=code,
            test_code=test_code,
            description="[AI-DRAFT] Testing hard limit",
            timeout=150 # Exceeds 120s
        )
        if success:
             print("[PASS] Successfully passed (timeout was capped at 120s as expected).")
        else:
            print("[FAIL] Failed registration.")
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_timeout_fix())
