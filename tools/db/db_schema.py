import sqlite3

db_path = "logichive.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- FULL SCHEMA ---")
cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
for row in cursor.fetchall():
    print(f"Table: {row[0]}")
    print(row[1])
    print("-" * 20)

print("\n--- COLUMN OVERVIEW ---")
cursor.execute("PRAGMA table_info(logichive_functions)")
for col in cursor.fetchall():
    print(
        f"ID: {col[0]} | Name: {col[1]} | Type: {col[2]} | NotNull: {col[3]} | Default: {col[4]} | PK: {col[5]}"
    )

conn.close()
