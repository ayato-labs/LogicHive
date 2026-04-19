import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Handles persistence of meeting history (transcripts, minutes, and audio paths).
    Uses SQLite for metadata storage.
    """

    def __init__(self, db_path="data/history.db", timeout=5.0):
        self.db_path = Path(db_path)
        self.timeout = timeout
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes the database schema."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    title TEXT,
                    transcript TEXT,
                    minutes TEXT,
                    audio_path TEXT,
                    model_info TEXT
                )
            """)
            logger.info("History database initialized.")
        except sqlite3.OperationalError as e:
            logger.error(f"Database operational error during init: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
        finally:
            conn.close()

    def add_meeting(self, title, transcript, audio_path, model_info=""):
        """Adds a new meeting record. Returns the meeting ID."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            cursor = conn.execute(
                "INSERT INTO meetings (title, transcript, audio_path, model_info) VALUES (?, ?, ?, ?)",
                (title, transcript, audio_path, model_info),
            )
            conn.commit()
            meeting_id = cursor.lastrowid
            logger.info(f"Meeting record added with ID: {meeting_id}")
            return meeting_id
        except sqlite3.OperationalError as e:
            logger.error(f"Database is locked or busy (add_meeting): {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to add meeting record: {e}")
            return None
        finally:
            conn.close()

    def update_minutes(self, meeting_id, minutes):
        """Updates the minutes for a specific meeting."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            conn.execute("UPDATE meetings SET minutes = ? WHERE id = ?", (minutes, meeting_id))
            conn.commit()
            logger.info(f"Updated minutes for meeting ID: {meeting_id}")
        except sqlite3.OperationalError as e:
            logger.error(f"Database is locked or busy (update_minutes): {e}")
        except Exception as e:
            logger.error(f"Failed to update minutes: {e}")
        finally:
            conn.close()

    def get_all_meetings(self):
        """Returns all meetings sorted by timestamp descending."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM meetings ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            logger.error(f"Database is locked or busy (get_all_meetings): {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch meetings: {e}")
            return []
        finally:
            conn.close()

    def get_meeting(self, meeting_id):
        """Returns a single meeting record."""
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.OperationalError as e:
            logger.error(f"Database is locked or busy (get_meeting {meeting_id}): {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch meeting {meeting_id}: {e}")
            return None
        finally:
            conn.close()
