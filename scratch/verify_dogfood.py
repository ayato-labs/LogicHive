import sqlite3
import os

db_path = "storage/data/logichive.db"
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Query the newly registered asset
query = "SELECT name, project, reliability_score, created_at, language, tags FROM functions WHERE name = 'calculate_code_hash_v4_hardened'"
cur.execute(query)
row = cur.fetchone()

if row:
    print("-" * 40)
    print("LOGICHIVE VAULT VERIFICATION")
    print("-" * 40)
    print(f"Function Name: {row[0]}")
    print(f"Project:       {row[1]}")
    print(f"Reliability:   {row[2] * 100:.1f}%")
    print(f"Timestamp:     {row[3]}")
    print(f"Language:      {row[4]}")
    print(f"Tags:          {row[5]}")
    print("-" * 40)
    print("STATUS: VERIFIED")
else:
    print("Error: Asset not found in database.")

conn.close()
