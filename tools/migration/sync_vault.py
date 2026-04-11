import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from storage.sqlite_api import sqlite_storage
from storage.auto_backup import backup_manager

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def sync():
    print("\n" + "="*60)
    print(" LOGICHIVE 2-WAY GITHUB SYNC")
    print("="*60 + "\n")

    # 1. IMPORT: Re-index files from repository into Database
    print("[1/2] IMPORTING: Files -> Database...")
    assets_from_files = await backup_manager.get_all_backup_assets()
    import_count = 0
    for asset in assets_from_files:
        try:
            # Upsert will only update if content changed (hash check is inside upsert)
            success = await sqlite_storage.upsert_function(asset)
            if success:
                import_count += 1
        except Exception as e:
            logger.error(f"Failed to import {asset.get('name')}: {e}")
    
    print(f"-> Successfully processed {len(assets_from_files)} files. {import_count} assets updated/added in DB.")

    # 2. EXPORT: Dump Database into repository files
    print("\n[2/2] EXPORTING: Database -> Files...")
    db_assets = await sqlite_storage.get_all_functions()
    await backup_manager.bulk_export(db_assets)
    
    print(f"-> Successfully exported {len(db_assets)} assets to repository mirrors.")
    print("\n" + "="*60)
    print(" SYNC COMPLETED")
    print(" Hint: You can now commit the 'exports/' directory to GitHub.")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(sync())
