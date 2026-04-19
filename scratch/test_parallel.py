import asyncio
import threading

import aiosqlite


async def t(i):
    print(f"[{i}] Loop {id(asyncio.get_running_loop())} in thread {threading.get_ident()}")
    c = await aiosqlite.connect(":memory:")
    print(f"[{i}] Connected")
    async with c.execute("SELECT 1") as cursor:
        await cursor.fetchone()
    await c.close()
    print(f"[{i}] Closed")


async def main():
    print("--- Parallel Run ---")
    await asyncio.gather(*[t(i) for i in range(5)])


if __name__ == "__main__":
    asyncio.run(main())
