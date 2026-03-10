import aiosqlite
import os
import logging

logger = logging.getLogger(__name__)

# Default DB Path
DB_PATH = os.getenv("SQLITE_DB_PATH", "logichive.db")


async def get_db_connection() -> aiosqlite.Connection:
    """
    Returns an asynchronus SQLite connection with WAL mode and busy timeout enabled.
    """
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row

    # Enable WAL mode for concurrency
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA busy_timeout=5000;")

    return db
