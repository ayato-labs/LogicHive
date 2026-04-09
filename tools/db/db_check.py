import sqlite3
import os

db_paths = [
    r"C:\Users\saiha\My_Service\programing\MCP\LogicHive\logichive.db",
    r"C:\Users\saiha\My_Service\programing\MCP\LogicHive\storage\data\logichive.db",
]

for path in db_paths:
    print(f"Testing {path}...")
    if not os.path.exists(path):
        print("  FAILED: File does not exist.")
        continue
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM sqlite_master;")
        res = cursor.fetchone()
        print(f"  SUCCESS: Connection established. Master count: {res[0]}")

        # Check for WAL mode
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        print(f"  Journal Mode: {mode}")

        conn.close()
    except Exception as e:
        print(f"  FAILED: {e}")

# Check for locks (try to open in exclusive mode if possible or check for .lock/.db-wal files)
for path in db_paths:
    wal = path + "-wal"
    shm = path + "-shm"
    if os.path.exists(wal):
        print(f"  ALERT: WAL file exists for {path}: {wal}")
