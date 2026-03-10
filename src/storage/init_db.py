import asyncio
import os
import sys

# Add backend to sys.path to import core
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from core.db import get_db_connection

async def init_db():
    print(f"Initializing personal LogicHive vault at {os.getenv('SQLITE_DB_PATH', 'logichive.db')}...")
    db = await get_db_connection()

    # Minimal organizations table just to keep existing FOREIGN KEYs happy if any, 
    # but primarily focusing on single user.
    await db.execute("""
    CREATE TABLE IF NOT EXISTS organizations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS logichive_functions (
        id TEXT PRIMARY KEY,
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
        organization_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        UNIQUE(name, organization_id)
    );
    """)

    # Create indices for performance
    await db.execute("CREATE INDEX IF NOT EXISTS idx_func_name ON logichive_functions(name);")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_func_hash ON logichive_functions(code_hash);")

    # Insert Default System Organization
    SYSTEM_ORG_ID = "00000000-0000-0000-0000-000000000000"
    await db.execute(
        "INSERT OR IGNORE INTO organizations (id, name) VALUES (?, ?)",
        (SYSTEM_ORG_ID, "Personal Vault"),
    )

    await db.commit()
    await db.close()
    print("Personal database initialization complete.")

if __name__ == "__main__":
    asyncio.run(init_db())
