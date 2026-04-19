
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath("src"))

from core.embedding import embedding_service
from storage.sqlite_api import sqlite_storage
from storage.vector_store import vector_manager
from core.db import get_db_connection

async def sync_embeddings():
    print("--- LogicHive Embedding Recovery & Sync ---")
    
    # 1. Initialize DB and find records missing embeddings
    db = await get_db_connection()
    async with db.execute(
        "SELECT id, name, description, code, project FROM logichive_functions WHERE embedding IS NULL"
    ) as cursor:
        rows = await cursor.fetchall()

    if not rows:
        print("✅ No records missing embeddings found.")
    else:
        print(f"🔍 Found {len(rows)} records missing embeddings. Starting generation...")
        
        for row in rows:
            func_id = row[0]
            name = row[1]
            description = row[2] or ""
            code = row[3]
            project = row[4]
            
            # Construct search document (logic similar to orchestrator)
            doc = f"Name: {name}\nDescription: {description}\nCode: {code}"
            
            print(f"  - Generating embedding for '{name}'...")
            try:
                emb = embedding_service.get_embedding(doc)
                emb_json = json.dumps(emb)
                
                await db.execute(
                    "UPDATE logichive_functions SET embedding = ? WHERE id = ?",
                    (emb_json, func_id)
                )
                await db.commit()
                print(f"    ✅ Updated DB for '{name}'")
            except Exception as e:
                print(f"    ❌ Failed for '{name}': {e}")

    # 2. Force Rebuild FAISS Index
    print("\n--- FAISS Index Sync ---")
    try:
        # Initialize if needed (it reads from DB)
        # We need all rows to initialize
        async with db.execute("SELECT * FROM logichive_functions") as cursor:
            all_rows = await cursor.fetchall()
            # Convert sqlite3.Row to dict for vector_manager
            db_dicts = [dict(r) for r in all_rows]
            
        await vector_manager.ensure_initialized(db_dicts)
        
        # Even if initialized, we want to force a rebuild to pick up the new embeddings
        print("🔄 Forcing FAISS index rebuild...")
        await vector_manager.rebuild_index()
        print(f"✅ FAISS Sync Complete. Total vectors: {vector_manager.index.ntotal}")
    except Exception as e:
        print(f"❌ FAISS Rebuild failed: {e}")

if __name__ == "__main__":
    asyncio.run(sync_embeddings())
