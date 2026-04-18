import asyncio
import aiosqlite

async def test():
    print("Testing aiosqlite correct singleton pattern...")
    c = aiosqlite.connect(':memory:')
    # The Connection object is itself the context manager.
    # It owns the thread.
    print("Starting thread via await...")
    await c 
    
    print("Doing work 1...")
    async with c.execute("SELECT 1") as cursor:
        print(f"Result 1: {await cursor.fetchone()}")
        
    print("Doing work 2...")
    async with c.execute("SELECT 2") as cursor:
        print(f"Result 2: {await cursor.fetchone()}")
        
    print("Closing...")
    await c.close()
    print("DONE")

if __name__ == "__main__":
    asyncio.run(test())
