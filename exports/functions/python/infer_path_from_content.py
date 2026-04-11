import re

def infer_path_from_content(content: str) -> str | None:
    """
    Heuristically infers a file path from a leading comment in the code content.
    Looks for patterns like '# filename: path/to/file.py' or '# path: file.py'.
    """
    match = re.search(
        r"^#\s*(?:filename|file|path):\s*([a-zA-Z0-9_./-]+)",
        content,
        re.MULTILINE,
    )
    if match:
        return match.group(1).strip()
    return None
