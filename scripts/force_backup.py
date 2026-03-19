import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.abspath('src'))

from storage.sqlite_api import sqlite_storage
from storage.auto_backup import backup_manager
from core.config import GITHUB_TOKEN

import logging

# Configure logging to see AutoBackupManager output
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def force_backup():
    print("=== LogicHive: Force Backup Utility ===")
    print(f"Using Database: {sqlite_storage.db_path}")
    
    if not GITHUB_TOKEN:
        print("❌ ERROR: GITHUB_TOKEN is not set in your .env file.")
        print("Please add 'GITHUB_TOKEN=your_personal_access_token' to .env first.")
        return

    # 1. Fetch all assets from SQLite
    print("Fetching all functions from database...")
    functions = await sqlite_storage.list_all_functions()
    
    if not functions:
        print("⚠ WARNING: No functions found in database to backup.")
        return

    print(f"Found {len(functions)} assets. Starting export...")
    
    # 2. Export each asset locally
    success_count = 0
    for func in functions:
        try:
            print(f"  Exporting: {func['name']}...", end="", flush=True)
            await backup_manager.export_asset(func)
            print(" [OK]")
            success_count += 1
        except Exception as e:
            print(f" [FAILED: {e}]")
    
    # 3. Perform bulk sync
    print("\nStarting GitHub synchronization (API calls and Git push)...")
    await backup_manager.bulk_sync_to_git()
    
    print("\n=== Backup Summary ===")
    print(f"Local Exports: {success_count}/{len(functions)} successful.")
    print("Check the logs above for any synchronization errors.")
    print("Repository: https://github.com/Ayato-AI-for-Auto/logichive-vault-backup")

if __name__ == "__main__":
    asyncio.run(force_backup())

if __name__ == "__main__":
    asyncio.run(force_backup())
