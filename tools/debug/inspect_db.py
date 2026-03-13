import sqlite3
import os

db_path = "logichive.db"
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found.")
    exit(1)

print(f"Checking {db_path}...")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

try:
    cursor.execute(
        "SELECT name, description, reliability_score FROM logichive_functions"
    )
    rows = cursor.fetchall()
    print(f"Found {len(rows)} functions.")
    for row in rows:
        desc = row["description"]
        desc_status = "EMPTY" if not desc else f"EXISTS (length: {len(desc)})"
        print(
            f"Function: {row['name']} | Reliability: {row['reliability_score']} | Description: {desc_status}"
        )
        if desc:
            print(f"  Summary: {desc[:100]}...")
except Exception as e:
    print(f"Error querying DB: {e}")
finally:
    conn.close()
