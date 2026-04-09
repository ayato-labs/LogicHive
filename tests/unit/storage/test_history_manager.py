import pytest
import sqlite3
import aiosqlite
from storage.history_manager import HistoryManager

@pytest.mark.asyncio
async def test_archive_version_preserves_project():
    """
    Unit test for HistoryManager.
    Verifies that the project field is correctly stored in the history table.
    """
    manager = HistoryManager()
    
    # Setup in-memory DB for pure unit test
    async with aiosqlite.connect(":memory:") as db:
        # Create history table
        await db.execute("""
            CREATE TABLE logichive_function_history (
                history_id TEXT PRIMARY KEY,
                function_id TEXT,
                project TEXT,
                name TEXT,
                code TEXT,
                description TEXT,
                tags TEXT,
                language TEXT,
                version INTEGER,
                code_hash TEXT,
                dependencies TEXT,
                test_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        existing_row = {
            "id": "123",
            "project": "secret-project",
            "name": "my_func",
            "code": "pass",
            "description": "desc",
            "tags": "[]",
            "language": "python",
            "version": 1,
            "code_hash": "abc"
        }
        
        await manager.archive_version(db, existing_row)
        
        # Verify
        async with db.execute("SELECT project FROM logichive_function_history") as cursor:
            row = await cursor.fetchone()
            assert row[0] == "secret-project"
