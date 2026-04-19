import asyncio
import json
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.system_info import SystemFingerprint
from storage.sqlite_api import sqlite_storage


async def verify_fingerprint():
    print("--- LogicHive Environmental Fingerprinting Verification ---\n")

    # 1. Capture current fingerprint
    current = SystemFingerprint.get_current()
    print(f"Current System Fingerprint:\n{json.dumps(current, indent=2)}\n")

    # 2. Test Saving with fingerprint
    func_name = "fingerprint_test_func"
    data = {
        "name": func_name,
        "code": "def hello(): return 'world'",
        "description": "A function to test fingerprinting.",
        "project": "test_env",
        "code_hash": "hash123",
        "env_fingerprint": current,
        "embedding": [0.1] * 1536,
    }

    print(f"Saving function '{func_name}' with current fingerprint...")
    await sqlite_storage.upsert_function(data)

    # 3. Retrieve and verify
    retrieved = await sqlite_storage.get_function_by_name(func_name, project="test_env")
    stored_fingerprint = retrieved.get("env_fingerprint")
    print(f"Stored Fingerprint Match: {stored_fingerprint == current}")

    # 4. Simulate Drift
    print("\n--- Simulating Drift ---")
    drifted_fingerprint = dict(current)
    drifted_fingerprint["os"] = "MacOS" if current["os"] == "Windows" else "Windows"
    drifted_fingerprint["python_version"] = "2.7.18"  # Very old

    warning = SystemFingerprint.generate_warning_msg(drifted_fingerprint)
    print("Generated Warning (Drift Detected):")
    print(warning)

    if "Python Version Drift" in warning and "OS mismatch" in warning:
        print("\n✅ Drift Detection logic is WORKING.")
    else:
        print("\n❌ Drift Detection logic FAILED.")

    # Cleanup
    await sqlite_storage.delete_function(func_name, project="test_env")


if __name__ == "__main__":
    asyncio.run(verify_fingerprint())
