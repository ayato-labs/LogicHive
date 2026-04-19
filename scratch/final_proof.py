import os
import sqlite3

db_path = r"c:\Users\saiha\My_Service\programing\MCP\LogicHive\storage\data\logichive.db"
print(f"Checking DB at: {db_path}")
print(f"File exists: {os.path.exists(db_path)}")

if not os.path.exists(db_path):
    exit(1)

conn = sqlite3.connect(db_path)
try:
    # 1. Check Tables
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"Tables found: {tables}")

    # 2. Check for the asset
    # The table name was assumed to be 'functions' in previous plans
    # Let's verify table names first since previous script failed
    table_names = [t[0] for t in tables]
    target_table = (
        "functions" if "functions" in table_names else table_names[0] if table_names else None
    )

    if target_table:
        query = f"SELECT name, project, reliability_score FROM {target_table} WHERE name LIKE 'calculate_code_hash_v4_hardened%'"
        res = conn.execute(query).fetchall()
        print(f"Query Results: {res}")
        if res:
            print("Dogfooding PROVEN!")
        else:
            print("Asset not found. Listing last 5 saved assets instead:")
            res = conn.execute(
                f"SELECT name, project FROM {target_table} ORDER BY created_at DESC LIMIT 5"
            ).fetchall()
            print(res)
    else:
        print("No tables found in DB.")

finally:
    conn.close()
