import sys
import io
import os
from pathlib import Path

# Fix Windows console encoding for AI output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Fix path to include backend
sys.path.append(str(Path(__file__).parent.parent.parent / "LogicHive-Hub-Private" / "backend"))

import asyncio
from hub.sandbox import sandbox

async def verify_sandbox():
    print("--- Verifying LogicHive Sandbox ---")
    
    code = """
def add(a, b):
    return a + b
"""
    
    test_code = """
def test_add():
    from solution import add
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
"""
    
    print("Running test in sandbox...")
    result = sandbox.execute_test(code, test_code)
    
    print("\nResult:")
    import json
    print(json.dumps(result, indent=2))
    
    if result.get("success"):
        print("\n✅ Sandbox Verification SUCCESSFUL!")
    else:
        print(f"\n❌ Sandbox Verification FAILED: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(verify_sandbox())
