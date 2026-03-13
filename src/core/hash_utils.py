import hashlib


def calculate_code_hash(code: str) -> str:
    """
    Calculates a SHA-256 hash for the given source code.
    Normalization: Basic whitespace stripping to avoid trivial mismatches.
    """
    # Normalize: strip leading/trailing whitespace and ensure consistent line endings
    normalized_code = code.strip().replace("\r\n", "\n")

    # Generate SHA-256 hash
    return hashlib.sha256(normalized_code.encode("utf-8")).hexdigest()
