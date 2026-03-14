import os
import sys
from pathlib import Path

# Add src to path
src_path = Path("C:/Users/saiha/My_Service/programing/MCP/LogicHive/src")
sys.path.insert(0, str(src_path))

try:
    from core.config import SQLITE_DB_PATH
    print(f"RESOLVED SQLITE_DB_PATH: {SQLITE_DB_PATH}")
    
    db_file = Path(SQLITE_DB_PATH)
    print(f"Exists: {db_file.exists()}")
    print(f"Parent: {db_file.parent}")
    print(f"Parent exists: {db_file.parent.exists()}")
    
    import sqlite3
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.execute("SELECT 1")
    conn.close()
    print("Database connection via absolute path: SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
