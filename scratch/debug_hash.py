import hashlib

def calculate_code_hash_v2(code: str) -> str:
    """Standardized SHA-256 code hashing utility for LogicHive assets."""
    # Normalize line endings
    normalized = code.replace("\r\n", "\n").replace("\r", "\n")
    
    # Strip leading/trailing whitespace and ensure single trailing newline
    normalized = normalized.strip() + "\n"
    
    # Create SHA-256 hash
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def test_calculate_code_hash_v2():
    code1 = "def foo():\n    pass\n"
    code2 = "def foo():\r\n    pass"
    
    h1 = calculate_code_hash_v2(code1)
    h2 = calculate_code_hash_v2(code2)
    
    print(f"Hash 1: {h1}")
    print(f"Hash 2: {h2}")
    
    assert h1 == h2
    assert len(h1) == 64
    assert isinstance(h1, str)
    print("Tests Passed locally!")

if __name__ == "__main__":
    try:
        test_calculate_code_hash_v2()
    except Exception as e:
        import traceback
        traceback.print_exc()
