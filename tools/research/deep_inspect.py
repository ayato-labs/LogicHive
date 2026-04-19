import os
import sqlite3
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

from core.db import DB_PATH

print(f"DB_PATH from core.db: {DB_PATH}")
print(f"Absolute DB_PATH: {os.path.abspath(DB_PATH)}")

db_path = os.path.abspath(DB_PATH)
if not os.path.exists(db_path):
    print("Database file NOT FOUND at this path.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n--- SCHEMA ---")
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='logichive_functions'")
row = cursor.fetchone()
if row:
    print(row[0])
else:
    print("Table 'logichive_functions' not found.")

print("\n--- DATA SAMPLES ---")
cursor.execute("SELECT name, description FROM logichive_functions LIMIT 3")
for row in cursor.fetchall():
    print(f"Name: {row[0]} | Desc: {repr(row[1])}")

conn.close()
