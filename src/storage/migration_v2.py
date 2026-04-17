import asyncio
import os
import sys
import aiosqlite

# Add src to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

async def migrate():
    # Use existing config to find DB
    try:
        from core.config import SQLITE_DB_PATH
        db_path = SQLITE_DB_PATH
    except ImportError:
        db_path = os.getenv("SQLITE_DB_PATH", "logichive.db")

    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. Nothing to migrate.")
        return

    print(f"Migrating LogicHive vault (V2: Environmental Fingerprinting) at {db_path}...")
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # 1. Check if 'env_fingerprint' column already exists in logichive_functions
            async with db.execute("PRAGMA table_info(logichive_functions)") as cursor:
                columns = [row[1] for row in await cursor.fetchall()]

            if "env_fingerprint" in columns:
                print("Database already has 'env_fingerprint' column. Migration skipped.")
                return

            print("Adding 'env_fingerprint' column...")

            # Transactional migration
            await db.execute("BEGIN TRANSACTION")
            try:
                # Add column to main table
                await db.execute("ALTER TABLE logichive_functions ADD COLUMN env_fingerprint TEXT")
                
                # Add column to history table
                await db.execute("ALTER TABLE logichive_function_history ADD COLUMN env_fingerprint TEXT")

                await db.commit()
                print("Migration successful.")
            except Exception as e:
                await db.rollback()
                print(f"Migration transaction failed: {e}")
                raise
                
    except Exception as ex:
        print(f"Connection/Migration failed: {ex}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(migrate())
