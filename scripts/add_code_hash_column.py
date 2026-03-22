import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    db_path = os.getenv("SQLITE_DB_PATH", "logichive.db")
    abs_path = os.path.abspath(db_path)
    logger.info(f"Migrating database at: {abs_path}")

    if not os.path.exists(abs_path):
        logger.error("Database file not found. Skipping migration.")
        return

    conn = sqlite3.connect(abs_path)
    cursor = conn.cursor()

    try:
        # Check if code_hash column exists
        cursor.execute("PRAGMA table_info(logichive_functions)")
        columns = [row[1] for row in cursor.fetchall()]

        if "code_hash" not in columns:
            logger.info("Adding 'code_hash' column to 'logichive_functions' table...")
            cursor.execute("ALTER TABLE logichive_functions ADD COLUMN code_hash TEXT")
            conn.commit()
            logger.info("Successfully added 'code_hash' column.")
        else:
            logger.info("'code_hash' column already exists.")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
