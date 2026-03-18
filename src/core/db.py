import aiosqlite
import logging
import asyncio
from functools import wraps

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


def retry_on_db_lock(max_retries: int = 5, base_delay: float = 0.1):
    """
    Decorator to retry async database operations on 'database is locked' errors
    using exponential backoff.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except aiosqlite.OperationalError as e:
                    if "database is locked" in str(e).lower() and retries < max_retries:
                        delay = base_delay * (2**retries)
                        logger.warning(
                            f"Database locked. Retrying '{func.__name__}' in {delay:.2f}s... "
                            f"(Attempt {retries + 1}/{max_retries})"
                        )
                        await asyncio.sleep(delay)
                        retries += 1
                    else:
                        raise

        return wrapper

    return decorator
