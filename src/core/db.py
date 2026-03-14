import aiosqlite
import os
import logging

logger = logging.getLogger(__name__)


from core.config import SQLITE_DB_PATH

async def get_db_connection() -> aiosqlite.Connection:
    """
    Returns an asynchronus SQLite connection with WAL mode and busy timeout enabled.
    Evaluates DB_PATH dynamically to support test environment overrides.
    """
    db = await aiosqlite.connect(SQLITE_DB_PATH)
    db.row_factory = aiosqlite.Row

    # Enable WAL mode for concurrency
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA busy_timeout=5000;")

    return db
