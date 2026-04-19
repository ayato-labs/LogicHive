import asyncio
import logging
from orchestrator import do_save_async

# Configure logging
logging.basicConfig(level=logging.INFO)

async def dogfood():
    print("--- Local Dogfooding Registration ---")
    
    code = \"\"\"
import hashlib

def calculate_code_hash(code: str) -> str:
    '''
    Calculates a SHA-256 hash for source code with basic normalization.
    Standardized fingerprinting for logic deduplication.
    '''
    # Normalize: strip leading/trailing whitespace and ensure consistent line endings
    normalized_code = code.strip().replace(\"\\r\\n\", \"\\n\")
    return hashlib.sha256(normalized_code.encode(\"utf-8\")).hexdigest()
\"\"\"

    test_code = \"\"\"
def test_code_hashing():
    c1 = \"print('hello')\"
    c2 = \"  print('hello')  \\r\\n\"
    h1 = calculate_code_hash(c1)
    h2 = calculate_code_hash(c2)
    
    # Normalization check
    assert h1 == h2, \"Hashes should match after normalization\"
    
    # Identity check
    assert h1 != calculate_code_hash(\"print('world')\"), \"Different code must have different hash\"
    
    # Determinism check
    assert h1 == calculate_code_hash(c1), \"Hash must be deterministic\"
\"\"\"

    try:
        success = await do_save_async(
            name="code_fingerprinter_dogfood",
            code=code,
            description="Stable SHA-256 fingerprinting for source code. (Dogfooding)",
            tags=["core", "hashing"],
            test_code=test_code,
            project="logichive-core"
        )
        if success:
            print("SUCCESS: Registered code_fingerprinter_dogfood")
        else:
            print("FAILED: Registration returned False")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(dogfood())
