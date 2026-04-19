def calculate_code_hash(code: str) -> str:
    import hashlib

    normalized_code = code.strip().replace("\r\n", "\n")
    return hashlib.sha256(normalized_code.encode("utf-8")).hexdigest()
