import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.abspath('src'))

from storage.sqlite_api import sqlite_storage
from storage.auto_backup import backup_manager
from core.config import GITHUB_TOKEN

async def force_backup():
    print("=== LogicHive: Force Backup Utility ===")
    
    if not GITHUB_TOKEN:
        print("❌ ERROR: GITHUB_TOKEN is not set in your .env file.")
        print("Please add 'GITHUB_TOKEN=your_personal_access_token' to .env first.")
        return

    # 1. Fetch all assets from SQLite
    print("Fetching all functions from database...")
    functions = await sqlite_storage.find_similar_functions(query="", limit=1000)
    
    if not functions:
        print("No functions found in database to backup.")
        return

    print(f"Found {len(functions)} assets. Starting export...")
    
    # 2. Export each asset locally
    for func in functions:
        print(f"  Exporting: {func['name']}...")
        await backup_manager.export_asset(func)
    
    # 3. Perform bulk sync
    print("\nStarting GitHub synchronization...")
    await backup_manager.bulk_sync_to_git()
    
    print("\n✅ Force backup process completed.")
    print("Check your private repository: https://github.com/settings/tokens (Ensure 'repo' scope is enabled if it fails)")

if __name__ == "__main__":
    asyncio.run(force_backup())
