import asyncio
import os
import sys
import aiosqlite

# Add src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from core.config import SQLITE_DB_PATH

async def check():
    print(f"Checking Personal Vault at: {SQLITE_DB_PATH}")
    if not os.path.exists(SQLITE_DB_PATH):
        print("ERROR: Database file not found!")
        return

    async with aiosqlite.connect(SQLITE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        async with db.execute("SELECT count(*) as count FROM logichive_functions") as cursor:
            row = await cursor.fetchone()
            print(f"Logic Assets: {row['count']}")

        print("\n--- Recent Assets ---")
        async with db.execute("SELECT name, language, reliability_score FROM logichive_functions ORDER BY created_at DESC LIMIT 10") as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                print(f"  {r['name']} [{r['language']}] (Reliability: {r['reliability_score']})")

    print("\nCheck Complete.")

if __name__ == "__main__":
    asyncio.run(check())
