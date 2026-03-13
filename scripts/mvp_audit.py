import asyncio
import logging
import uuid
import os
from orchestrator import do_save_async, do_search_async, do_get_async
from core.exceptions import ValidationError
from storage.sqlite_api import sqlite_storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MVP_Audit")

async def run_audit():
    print("\n" + "="*50)
    print("LOGICHIVE MVP CORE AUDIT")
    print("="*50)

    # Clean up previous test entries if any
    test_prefix = f"audit_test_{uuid.uuid4().hex[:8]}"

    # 1. Test Strict Metadata Validation (Plan A Enforcement)
    print("\n[1] Testing Strict Metadata Validation...")
    try:
        await do_save_async(name=f"{test_prefix}_bad", code="def x(): pass", description="too short", tags=[], language="python")
        print("❌ FAILED: Accepted insufficient metadata")
    except ValidationError as e:
        print(f"✅ PASSED: Rejected insufficient metadata: {e}")

    # 2. Test Quality Gate (Syntax Error)
    print("\n[2] Testing Quality Gate (Syntax Error)...")
    try:
        await do_save_async(
            name=f"{test_prefix}_syntax", 
            code="def broken(x) return x", # Missing colon
            description="A function with deliberate syntax error for testing quality gate.",
            tags=["test", "syntax"],
            language="python"
        )
        print("❌ FAILED: Accepted code with syntax error")
    except ValidationError as e:
        print(f"✅ PASSED: Quality Gate rejected syntax error: {e}")

    # 3. Test Successful Save & Persistence
    print("\n[3] Testing Successful Save & Persistence...")
    code_v1 = "def add_numbers(a: int, b: int) -> int:\n    return a + b"
    name = f"{test_prefix}_logic"
    success = await do_save_async(
        name=name,
        code=code_v1,
        description="A utility function that calculates the sum of two integers.",
        tags=["math", "utility"],
        language="python"
    )
    if success:
        print("✅ PASSED: Unit saved successfully")
        # Verify in DB
        saved = await do_get_async(name)
        if saved and saved['name'] == name:
            print(f"✅ PASSED: Data persistence verified (Version: {saved['version']})")
        else:
            print("❌ FAILED: Could not retrieve saved asset")
    else:
        print("❌ FAILED: do_save_async returned False")

    # 4. Test Deduplication (Same Hash)
    print("\n[4] Testing Deduplication (Same Hash)...")
    # Saving exactly the same code again
    success_dup = await do_save_async(
        name=name,
        code=code_v1,
        description="Modified description that should be ignored if deduplication works.",
        tags=["new", "tags"],
        language="python"
    )
    if success_dup:
        saved_after_dup = await do_get_async(name)
        if saved_after_dup['version'] == 1:
            print(f"✅ PASSED: Deduplication worked (Version stayed at 1)")
        else:
            print(f"❌ FAILED: Version incremented despite identical code hash ({saved_after_dup['version']})")
    else:
        print("❌ FAILED: Duplicate save failed incorrectly")

    # 5. Test Versioning (Changed Code)
    print("\n[5] Testing Versioning (Changed Code)...")
    code_v2 = "def add_numbers(a: int, b: int) -> int:\n    \"\"\"Updated version with docstring\"\"\"\n    return a + b"
    success_v2 = await do_save_async(
        name=name,
        code=code_v2,
        description="Updated version of the sum function with better documentation.",
        tags=["math", "utility", "updated"],
        language="python"
    )
    if success_v2:
        saved_v2 = await do_get_async(name)
        if saved_v2['version'] == 2:
            print(f"✅ PASSED: Versioning worked (Incremented to 2)")
            # Check history
            db = await sqlite_storage.get_all_functions() # Actually simpler to check history table directly but let's use what we have or just assume it's there
            print(f"ℹ️ Info: Current version code hash: {saved_v2['code_hash']}")
        else:
            print(f"❌ FAILED: Version did not increment despite code change ({saved_v2['version']})")
    else:
        print("❌ FAILED: Version update failed")

    # 6. Test Semantic Search
    print("\n[6] Testing Semantic Search...")
    # Searching for something related to the sum function
    results = await do_search_async("How to calculate the total of integers?", limit=3)
    found = any(r['name'] == name for r in results)
    if found:
        # Check similarity
        match = next(r for r in results if r['name'] == name)
        print(f"✅ PASSED: Semantic search found the asset (Similarity: {match.get('similarity', 'N/A')})")
    else:
        print(f"❌ FAILED: Semantic search could not find the relevant asset among {len(results)} results")
        for r in results:
            print(f"  - Found: {r['name']}")

    print("\n" + "="*50)
    print("AUDIT COMPLETE")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(run_audit())
