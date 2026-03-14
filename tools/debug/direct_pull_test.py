import asyncio
import os
import sys

# Add LogicHive src to path
LOGICHIVE_ROOT = r"C:\Users\saiha\My_Service\programing\MCP\LogicHive"
sys.path.append(os.path.join(LOGICHIVE_ROOT, "src"))

# Force absolute paths
os.environ["SQLITE_DB_PATH"] = os.path.join(LOGICHIVE_ROOT, "storage", "data", "logichive.db")
os.environ["FS_DATA_DIR"] = os.path.join(LOGICHIVE_ROOT, "storage", "data")

from storage.sqlite_api import sqlite_storage
import orchestrator

async def pull_test():
    print("--- Pull Test (Direct Storage Access) ---")
    
    # 1. List all
    print("Listing all functions in vault...")
    functions = await sqlite_storage.get_all_functions()
    if not functions:
        print("  ❌ No functions found.")
    else:
        for f in functions:
            print(f"  - {f['name']} ({f['language']})")
            
    # 2. Try specific get via orchestrator
    for target in ["normalize_llm_args", "infer_path_from_content"]:
        print(f"\nRetrieving code for '{target}' via Orchestrator...")
        f_data = await orchestrator.do_get_async(target)
        if f_data:
            print(f"  ✅ Retrieval SUCCESS. Code length: {len(f_data['code'])} chars.")
            # Print first few lines
            print("  Snippet:")
            snippet = "\n".join(f_data['code'].splitlines()[:3])
            print(f"{snippet}\n...")
        else:
            print(f"  ❌ Failed to retrieve '{target}'.")

if __name__ == "__main__":
    asyncio.run(pull_test())
