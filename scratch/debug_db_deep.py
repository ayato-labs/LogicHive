
import asyncio
import sqlite3
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath("src"))

async def debug_db_standalone():
    from core.config import SQLITE_DB_PATH
    print(f"--- LogicHive DB Diagnostics ---")
    print(f"Target DB: {SQLITE_DB_PATH}")
    
    if not os.path.exists(SQLITE_DB_PATH):
        print("❌ ERROR: Database file does not exist.")
        return

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Tables check
        tables = [row["name"] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"Detected Tables: {tables}")
        
        # 2. Schema check for logichive_functions
        if "logichive_functions" in tables:
            print("\n[Schema: logichive_functions]")
            columns = cursor.execute("PRAGMA table_info(logichive_functions)").fetchall()
            for col in columns:
                print(f"  - {col['name']} ({col['type']})")
                
            # 3. Integrity Check
            print("\n[Integrity Check]")
            row_count = cursor.execute("SELECT COUNT(*) FROM logichive_functions").fetchone()[0]
            null_embeddings = cursor.execute("SELECT COUNT(*) FROM logichive_functions WHERE embedding IS NULL").fetchone()[0]
            print(f"  - Total Records: {row_count}")
            print(f"  - Records missing embeddings: {null_embeddings}")
            
            # 4. Content Peek
            print("\n[Content Sample]")
            rows = cursor.execute("SELECT name, reliability_score, language, version FROM logichive_functions LIMIT 5").fetchall()
            for r in rows:
                print(f"  - {r['name']} (v{r['version']}): Score={r['reliability_score']:.2f}, Lang={r['language']}")
        else:
            print("❌ ERROR: 'logichive_functions' table missing!")
            
        conn.close()
    except Exception as e:
        print(f"❌ ERROR: Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_db_standalone())
