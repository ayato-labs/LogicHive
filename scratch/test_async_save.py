import asyncio
import os
import sys

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

from orchestrator import do_save_async, do_get_verification_status
from core.config import SQLITE_DB_PATH

async def test_flow():
    print(f"Using DB: {SQLITE_DB_PATH}")
    
    test_code = """
def hello_world_async():
    \"\"\"Returns a friendly greeting.\"\"\"
    return "Hello from the new async LogicHive!"
"""
    
    print("Step 1: Save function (Async)...")
    result = await do_save_async(
        name="hello_world_async_test",
        code=test_code,
        project="dogfooding",
        description="A test function for async flow.",
        tags=["test", "async"]
    )
    
    print(f"Save Result: {result}")
    
    print("Step 2: Checking status immediately...")
    status = await do_get_verification_status("hello_world_async_test", "dogfooding")
    print(f"Immediate Status: {status['status']}")
    
    print("Step 3: Waiting for background quality gate (approx 10s)...")
    await asyncio.sleep(10)
    
    status = await do_get_verification_status("hello_world_async_test", "dogfooding")
    print(f"Final Status: {status['status']}")
    if status.get('report'):
        print("Report received.")

if __name__ == "__main__":
    asyncio.run(test_flow())
