import asyncio
import os
import sys

# Add backend to sys.path to import core
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from core.db import get_db_connection


async def init_db():
    print(
        f"Initializing personal LogicHive vault at {os.getenv('SQLITE_DB_PATH', 'logichive.db')}..."
    )
    db = await get_db_connection()

    # Main table for current versions
    await db.execute("""
    CREATE TABLE IF NOT EXISTS logichive_functions (
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
    );
    """)

    # History table for old versions
    await db.execute("""
    CREATE TABLE IF NOT EXISTS logichive_function_history (
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
    );
    """)

    # Create indices for performance
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_func_project_name ON logichive_functions(project, name);"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_func_hash ON logichive_functions(code_hash);"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_hist_name ON logichive_function_history(name);"
    )

    await db.commit()
    await db.close()
    print("Personal database initialization complete.")


if __name__ == "__main__":
    asyncio.run(init_db())
