import os
import sqlite3

db_path = "storage/data/logichive.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM logichive_functions").fetchone()[0]
    names = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM logichive_functions ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
    ]
    print(f"Total Logic Cells: {count}")
    print(f"Latest additions: {names}")
    conn.close()
else:
    print(f"Database not found at {db_path}")
