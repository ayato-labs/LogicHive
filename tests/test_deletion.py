import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.abspath('src'))

import orchestrator
from storage.sqlite_api import sqlite_storage

async def test_deletion():
    from core.config import ENABLE_AUTO_BACKUP
    print(f"=== LogicHive: Deletion & Archiving Test (AutoBackup: {ENABLE_AUTO_BACKUP}) ===")
    
    # 1. First, ensure there's a test function
    test_name = "deletion_test_func"
    print(f"Creating test function '{test_name}'...")
    await orchestrator.do_save_async(
        name=test_name,
        code='''def hello_world():
    """
    This is a test function for the deletion and archiving mechanism.
    It returns a friendly greeting.
    """
    msg = "Hello from LogicHive deletion test!"
    print(msg)
    return msg
''',
        language="python",
        description="A robust test function designed to pass quality gates for the deletion and archiving verification test.",
        tags=["test", "utility"]
    )
    
    # Wait for background backup
    await asyncio.sleep(5)
    
    # 2. Delete it
    print(f"\nDeleting test function '{test_name}'...")
    success = await orchestrator.do_delete_async(test_name)
    
    if success:
        print("✅ Orchestrator reported success.")
    else:
        print("❌ Orchestrator reported failure.")

    # 3. Verify local DB
    functions = await sqlite_storage.list_all_functions()
    found = any(f["name"] == test_name for f in functions)
    if not found:
        print("✅ Verified: Removed from SQLite.")
    else:
        print("❌ Error: Still exists in SQLite.")

    # Wait for background archiving
    print("Waiting for background archiving to finish...")
    await asyncio.sleep(10)
    
    # 4. Verify exports folder
    archive_dir = os.path.join("exports", "archives")
    if os.path.exists(archive_dir):
        print(f"✅ Verified: Archives directory exists.")
    else:
        print(f"❌ Error: Archives directory NOT found.")

if __name__ == "__main__":
    asyncio.run(test_deletion())
