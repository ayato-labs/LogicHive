import asyncio
import os
import sys

# Add LogicHive src to path
LOGICHIVE_ROOT = r"C:\Users\saiha\My_Service\programing\MCP\LogicHive"
sys.path.append(os.path.join(LOGICHIVE_ROOT, "src"))

# Force absolute paths for this execution
os.environ["SQLITE_DB_PATH"] = os.path.join(LOGICHIVE_ROOT, "storage", "data", "logichive.db")
os.environ["FS_DATA_DIR"] = os.path.join(LOGICHIVE_ROOT, "storage", "data")

import orchestrator

async def self_anatomy():
    print("Extracting llm_adapter.py logic to LogicHive...")
    
    code = """import re
from typing import Any

def normalize_llm_args(args: dict[str, Any]) -> dict[str, Any]:
    \"\"\"
    Physically remaps common LLM argument hallucinations to standardized keys.
    Prevents tool call failures due to slightly off key naming (e.g., 'file_path' instead of 'path').
    \"\"\"
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
"""
    
    success = await orchestrator.do_save_async(
        name="normalize_llm_args",
        code=code,
        description="Remaps common LLM tool call argument hallucinations to standardized keys. Essential for robust MCP tool execution.",
        tags=["llm", "mcp_client", "hallucination_fix", "utility"],
        language="python"
    )
    
    if success:
        print("✅ SUCCESS: normalize_llm_args saved to LogicHive.")
    else:
        print("❌ FAILED to save to LogicHive.")

if __name__ == "__main__":
    asyncio.run(self_anatomy())
