import asyncio
import logging
import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

from core.exceptions import ValidationError
from orchestrator import do_save_async


async def verify():
    # Configure minimal logging to avoid noise
    logging.basicConfig(level=logging.ERROR)

    print("\n[1] Testing Detailed Rejection (Assertion Error)")
    try:
        await do_save_async(
            name="repro_failure",
            code="def power(a, b): return a ** b",
            description="Testing transparent feedback",
            test_code="assert power(2, 3) == 9",  # Deliberate failure: 2^3 is 8
            timeout=10,
        )
    except ValidationError as e:
        print("✅ Success: Caught ValidationError")
        import json

        print(f"Full Details: {json.dumps(e.details, indent=2)}")

        details = e.details or {}
        # ... (rest of the checks)

    print("\n[2] Testing 'Unverified' Score (No tests)")
    try:
        # Saving without tests used to be Score 0 (Immediate Rejection)
        # Now it should be Score 40 (Still rejected if threshold is 70, but different reason)
        await do_save_async(
            name="repro_no_test",
            code="def greet(): return 'hi'",
            description="Testing unverified flow",
            test_code="",  # No tests
            timeout=10,
        )
    except ValidationError as e:
        score = e.details.get("score")
        print(f"Score: {score}")
        if score == 40.0:
            print("✅ Success: Asset given 'Unverified' score 40 instead of 0")
        else:
            print(f"❌ Failure: Unexpected score {score}")


if __name__ == "__main__":
    asyncio.run(verify())
