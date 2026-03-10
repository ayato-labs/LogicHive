import sqlite3

conn = sqlite3.connect('logichive.db')
cursor = conn.cursor()

try:
    print("Adding UNIQUE index to logichive_functions(name, organization_id)...")
    # Adding a UNIQUE index serves as a conflict target for ON CONFLICT
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_func_name_org ON logichive_functions(name, organization_id)")
    conn.commit()
    print("SUCCESS: Unique index added.")
except Exception as e:
    print(f"FAILED: {e}")
finally:
    conn.close()
