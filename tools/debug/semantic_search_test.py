import asyncio
import os
import sys

# Add LogicHive src to path
LOGICHIVE_ROOT = r"C:\Users\saiha\My_Service\programing\MCP\LogicHive"
sys.path.append(os.path.join(LOGICHIVE_ROOT, "src"))

# Force absolute paths
os.environ["SQLITE_DB_PATH"] = os.path.join(LOGICHIVE_ROOT, "storage", "data", "logichive.db")
os.environ["FS_DATA_DIR"] = os.path.join(LOGICHIVE_ROOT, "storage", "data")

import orchestrator

async def search_test():
    print("--- Semantic Search Test (RAG) ---")
    
    query = "How do I fix LLM argument hallucinations in tool calls?"
    print(f"Query: '{query}'")
    
    results = await orchestrator.do_search_async(query, limit=3)
    
    if not results:
        print("  ❌ No results found. (Is FAISS initialized?)")
    else:
        for i, r in enumerate(results):
            score = r.get('similarity', 'N/A')
            print(f"  {i+1}. {r['name']} (Similarity: {score})")
            print(f"     Description: {r['description']}")

if __name__ == "__main__":
    asyncio.run(search_test())
