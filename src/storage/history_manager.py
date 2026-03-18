import logging
import uuid
import aiosqlite
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HistoryManager:
    """Manages versioning and history of logic assets."""

    async def archive_version(
        self, db: aiosqlite.Connection, existing_row: Dict[str, Any]
    ):
        """Moves the current version to the history table."""
        history_id = str(uuid.uuid4())

        await db.execute(
            """
            INSERT INTO logichive_function_history 
            (history_id, function_id, name, code, description, tags, language, version, code_hash, dependencies, test_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                history_id,
                existing_row["id"],
                existing_row["name"],
                existing_row["code"],
                existing_row["description"],
                existing_row["tags"],
                existing_row["language"],
                existing_row["version"],
                existing_row["code_hash"],
                existing_row.get("dependencies"),
                existing_row.get("test_code"),
            ),
        )
        logger.info(
            f"History: Archived version {existing_row['version']} of '{existing_row['name']}'"
        )


# Singleton instance
history_manager = HistoryManager()
