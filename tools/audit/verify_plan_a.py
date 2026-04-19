import asyncio
import logging

from core.exceptions import ValidationError
from orchestrator import do_save_async

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)


async def verify_plan_a():
    print("\n--- LogicHive Plan A Verification ---")

    # 1. Test Rejection: Empty Description
    print("\n[Test 1] Saving with empty description...")
    try:
        await do_save_async(
            name="test_bad_desc",
            code="def foo(): pass",
            description="",
            tags=["test"],
            language="python",
        )
        print("❌ FAILED: Should have rejected empty description")
    except ValidationError as e:
        print(f"✅ PASSED: Caught expected validation error: {e}")

    # 2. Test Rejection: Short Description
    print("\n[Test 2] Saving with too short description...")
    try:
        await do_save_async(
            name="test_short_desc",
            code="def foo(): pass",
            description="too short",
            tags=["test"],
            language="python",
        )
        print("❌ FAILED: Should have rejected short description")
    except ValidationError as e:
        print(f"✅ PASSED: Caught expected validation error: {e}")

    # 3. Test Rejection: Empty Tags
    print("\n[Test 3] Saving with empty tags...")
    try:
        await do_save_async(
            name="test_no_tags",
            code="def foo(): pass",
            description="This is a valid long enough description for testing.",
            tags=[],
            language="python",
        )
        print("❌ FAILED: Should have rejected empty tags")
    except ValidationError as e:
        print(f"✅ PASSED: Caught expected validation error: {e}")

    # 4. Test Success: Valid Metadata
    print("\n[Test 4] Saving with valid metadata...")
    try:
        success = await do_save_async(
            name="test_valid_asset",
            code="def calculate_sum(a: int, b: int) -> int:\n    return a + b",
            description="A simple function to calculate the sum of two integers for arithmetic reuse.",
            tags=["math", "utility", "sum"],
            language="python",
        )
        if success:
            print("✅ PASSED: Successfully saved asset with valid metadata")
        else:
            print("❌ FAILED: do_save_async returned False")
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(verify_plan_a())
