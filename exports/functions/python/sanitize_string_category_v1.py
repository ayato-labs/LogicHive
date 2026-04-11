def _sanitize_category(self, category: str) -> str:
    """
    Normalizes and sanitizes the category string to ensure database safety and consistency.
    Removes non-printable characters, strips whitespace, and enforces a length limit.
    """
    if not category or not isinstance(category, str):
        return "News"
    sanitized = "".join(ch for ch in category if ch.isprintable()).strip()
    if not sanitized:
        return "News"
    return sanitized[:50]
