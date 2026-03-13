import aiosqlite
import os
import logging

logger = logging.getLogger(__name__)


async def get_db_connection() -> aiosqlite.Connection:
    """
    Returns an asynchronus SQLite connection with WAL mode and busy timeout enabled.
    Evaluates DB_PATH dynamically to support test environment overrides.
    """
    db_path = os.getenv("SQLITE_DB_PATH", "logichive.db")
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row

    # Enable WAL mode for concurrency
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA busy_timeout=5000;")

    return db
