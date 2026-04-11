import re
from typing import Any

def normalize_llm_args(args: dict[str, Any]) -> dict[str, Any]:
    """
    Physically remaps common LLM argument hallucinations to standardized keys.
    Prevents tool call failures due to slightly off key naming (e.g., 'file_path' instead of 'path').
    """
    if not isinstance(args, dict):
        return args
    hallucinations = {
        "file_path": "path",
        "filepath": "path",
        "file": "path",
        "code": "content",
        "source": "content",
        "text": "content",
    }
    for old, new in hallucinations.items():
        if old in args and new not in args:
            args[new] = args.pop(old)
    return args
