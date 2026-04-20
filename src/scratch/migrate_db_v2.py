import os
import sqlite3

DB_PATH = r"c:\Users\saiha\My_Service\programing\MCP\LogicHive\storage\data\logichive.db"


def migrate():
    print(f"Migrating DB at {DB_PATH}...")
    if not os.path.exists(DB_PATH):
        print("DB file not found. Skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add verification_status
    try:
        cursor.execute(
            "ALTER TABLE logichive_functions ADD COLUMN verification_status TEXT DEFAULT 'pending'"
        )
        print("Added column: verification_status")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column verification_status already exists.")
        else:
            raise

    # Add verification_report
    try:
        cursor.execute("ALTER TABLE logichive_functions ADD COLUMN verification_report TEXT")
        print("Added column: verification_report")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column verification_report already exists.")
        else:
            raise

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()
