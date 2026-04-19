import asyncio
import logging
import sys

import aiosqlite

# Configure logging to see aiosqlite threads/debug info
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


async def main():
    try:
        print("Starting test...")
        print(f"Aiosqlite version: {aiosqlite.__version__}")

        # Test 1: Simple connection/close
        db = await aiosqlite.connect(":memory:")
        await db.close()
        print("Test 1 (Simple) Passed.")

        # Test 2: Double connection (simulate sequence)
        db1 = await aiosqlite.connect(":memory:")
        await db1.close()
        db2 = await aiosqlite.connect(":memory:")
        await db2.close()
        print("Test 2 (Sequence) Passed.")

        print("All tests finished successfully.")
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
