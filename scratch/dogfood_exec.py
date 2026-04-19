import asyncio
import os
import sys

# Ensure src is in the path
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.exceptions import ValidationError
from orchestrator import do_save_async


async def run_dogfood():
    code = """
import hashlib

def calculate_code_hash(code: str) -> str:
    \"\"\"
    Calculates a SHA-256 hash for the given source code.
    Normalization: Basic whitespace stripping to avoid trivial mismatches.
    \"\"\"
    # Normalize: strip leading/trailing whitespace and ensure consistent line endings
    normalized_code = code.strip().replace("\\r\\n", "\\n")

    # Generate SHA-256 hash
    return hashlib.sha256(normalized_code.encode("utf-8")).hexdigest()
"""
    test_code = """
import hashlib

# 1. Basic check
code = "def hello():\\n    print('world')"
expected = hashlib.sha256(code.encode("utf-8")).hexdigest()
assert calculate_code_hash(code) == expected

# 2. Normalization check
code_lf = "def hello():\\n    print('world')"
code_crlf = "def hello():\\r\\n    print('world')"
assert calculate_code_hash(code_lf) == calculate_code_hash(code_crlf)

# 3. Whitespace check
code_ws = "  print('hello')  "
normalized = "print('hello')"
expected_ws = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
assert calculate_code_hash(code_ws) == expected_ws

# 4. Logic change check
assert calculate_code_hash("x=1") != calculate_code_hash("x=2")

print("Hardened Dogfooding verification successful!")
"""

    try:
        print("Starting Dogfooding Registration (Direct Script)...")
        success = await do_save_async(
            name="calculate_code_hash_v4_hardened",
            code=code,
            description="LogicHive core hash utility. Registered via direct script to verify infrastructure hardening (timeout=45s, env=relaxed).",
            language="python",
            tags=["security", "internal", "hardened"],
            project="logichive-dogfood",
            test_code=test_code,
            dependencies=[],
        )
        print(f"Result: {'SUCCESS' if success else 'FAILURE'}")
    except ValidationError as e:
        print(f"Quality Gate REJECTED: {e}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_dogfood())
