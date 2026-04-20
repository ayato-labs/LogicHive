import asyncio
import os
import sys

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

from storage.vector_store import vector_manager

async def sync():
    print("Starting FAISS rebuild...")
    await vector_manager.ensure_initialized([]) # Initialize if not
    await vector_manager.rebuild_index()
    print("Rebuild complete.")

if __name__ == "__main__":
    asyncio.run(sync())
