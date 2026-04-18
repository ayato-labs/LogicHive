import asyncio
import aiosqlite
import threading

async def t():
    print(f"Loop {id(asyncio.get_running_loop())} in thread {threading.get_ident()}")
    c = await aiosqlite.connect(':memory:')
    print("Connected")
    async with c.execute("SELECT 1") as cursor:
        print(f"Result: {await cursor.fetchone()}")
    await c.close()
    print("Closed")

async def main():
    print("--- Run 1 ---")
    await t()
    print("--- Run 2 ---")
    await t()

if __name__ == "__main__":
    asyncio.run(main())
