import asyncio

import aiosqlite


async def test():
    print("Testing aiosqlite re-entry...")
    c = aiosqlite.connect(":memory:")
    await c
    print("First enter...")
    await c.__aenter__()
    print("First exit...")
    await c.__aexit__(None, None, None)

    try:
        print("Second enter...")
        await c.__aenter__()
        print("RE-ENTRY SUCCESS")
    except RuntimeError as e:
        print(f"RE-ENTRY FAILED: {e}")
    except Exception as e:
        print(f"OTHER ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(test())
