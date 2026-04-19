import asyncio
import logging
import os
import sys

# Add src to path
sys.path.append(os.path.abspath("src"))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from core.config import GITHUB_TOKEN  # noqa: E402
from storage.auto_backup import backup_manager  # noqa: E402


async def restore_backup():
    print("=== LogicHive: Automatic Restoration (Rehydrate) ===")

    if not GITHUB_TOKEN:
        print("❌ ERROR: GITHUB_TOKEN is not set in your .env file.")
        return

    print("Starting restoration process from GitHub...")
    results = await backup_manager.restore_from_git()

    print("\n=== Restoration Summary ===")
    print(f"✅ Successfully restored: {results['success']}")
    print(f"❌ Failed to restore: {results['failed']}")

    if results["errors"]:
        print("\nErrors encountered:")
        for err in results["errors"]:
            print(f"- {err}")

    if results["success"] > 0:
        print("\nDatabase and Vector Index have been synchronized with the backup repository.")
    else:
        print("\nNo data was restored.")


if __name__ == "__main__":
    asyncio.run(restore_backup())
