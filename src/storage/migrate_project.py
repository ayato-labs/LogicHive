import asyncio
import os
import aiosqlite
import sys

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

    print(f"Migrating LogicHive vault at {db_path}...")
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # 1. Check if 'project' column already exists in logichive_functions
            async with db.execute("PRAGMA table_info(logichive_functions)") as cursor:
                columns = [row[1] for row in await cursor.fetchall()]
            
            if "project" in columns:
                print("Database already has 'project' column. Skipping migration.")
                return

            print("Adding 'project' column and updating constraints...")
            
            # Transactional migration
            await db.execute("BEGIN TRANSACTION")
            try:
                # --- logichive_functions migration ---
                await db.execute("ALTER TABLE logichive_functions RENAME TO logichive_functions_old")
                
                await db.execute("""
                CREATE TABLE logichive_functions (
                    id TEXT PRIMARY KEY,
                    project TEXT DEFAULT 'default',
                    name TEXT NOT NULL,
                    code TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    reliability_score REAL DEFAULT 1.0,
                    test_metrics TEXT,
                    embedding TEXT,
                    language TEXT DEFAULT 'python',
                    call_count INTEGER DEFAULT 0,
                    code_hash TEXT,
                    version INTEGER DEFAULT 1,
                    dependencies TEXT,
                    test_code TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project, name)
                )
                """)
                
                # Get columns from old table
                async with db.execute("PRAGMA table_info(logichive_functions_old)") as cursor:
                    old_cols = [row[1] for row in await cursor.fetchall()]
                
                # Define new table columns (excluding those not in old that we want to defaults)
                # Actually, just get intersection plus defaults
                target_cols = [
                    "id", "name", "code", "description", "tags", "reliability_score", 
                    "test_metrics", "embedding", "language", "call_count", "code_hash", 
                    "version", "dependencies", "test_code", "created_at", "updated_at"
                ]
                
                # Filter target columns to only those that exist in the old table
                common_cols = [c for c in target_cols if c in old_cols]
                cols_str = ", ".join(common_cols)
                
                print(f"Copying columns: {cols_str}")
                await db.execute(f"INSERT INTO logichive_functions ({cols_str}) SELECT {cols_str} FROM logichive_functions_old")
                
                # --- logichive_function_history migration ---
                await db.execute("ALTER TABLE logichive_function_history RENAME TO logichive_function_history_old")
                
                await db.execute("""
                CREATE TABLE logichive_function_history (
                    history_id TEXT PRIMARY KEY,
                    function_id TEXT NOT NULL,
                    project TEXT DEFAULT 'default',
                    name TEXT NOT NULL,
                    code TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    language TEXT,
                    version INTEGER NOT NULL,
                    code_hash TEXT,
                    dependencies TEXT,
                    test_code TEXT,
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                async with db.execute("PRAGMA table_info(logichive_function_history_old)") as cursor:
                    old_hist_cols = [row[1] for row in await cursor.fetchall()]
                
                hist_target_cols = [
                    "history_id", "function_id", "name", "code", "description", "tags", 
                    "language", "version", "code_hash", "dependencies", "test_code", "archived_at"
                ]
                common_hist_cols = [c for c in hist_target_cols if c in old_hist_cols]
                hist_cols_str = ", ".join(common_hist_cols)
                
                print(f"Copying history columns: {hist_cols_str}")
                await db.execute(f"INSERT INTO logichive_function_history ({hist_cols_str}) SELECT {hist_cols_str} FROM logichive_function_history_old")
                
                # --- Cleanup ---
                await db.execute("DROP TABLE logichive_functions_old")
                await db.execute("DROP TABLE logichive_function_history_old")
                
                # Update Indices
                await db.execute("DROP INDEX IF EXISTS idx_func_name")
                await db.execute("CREATE INDEX idx_func_project_name ON logichive_functions(project, name)")
                
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
