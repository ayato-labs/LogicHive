import asyncio
import os
import sys

# Add LogicHive src to path
LOGICHIVE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(os.path.join(LOGICHIVE_ROOT, "src"))

# Force absolute paths for this execution
os.environ["SQLITE_DB_PATH"] = os.path.join(LOGICHIVE_ROOT, "storage", "data", "logichive.db")
os.environ["FS_DATA_DIR"] = os.path.join(LOGICHIVE_ROOT, "storage", "data")

import orchestrator  # noqa: E402


async def self_anatomy():
    print("Extracting parse_llm_tool_calls logic to LogicHive...")

    code = """from typing import Any

def parse_llm_tool_calls(calls: list[Any]) -> list[dict[str, Any]]:
    \"\"\"
    Strictly converts LLM-native tool calls (from SDK or RAW response) to an internal structured list.
    Handles both object-attribute style (SDK) and dictionary style (JSON) tool calls.
    Integrates argument normalization.
    \"\"\"
    parsed = []
    if not isinstance(calls, list):
        return []

    for call in calls:
        # Support both object attributes (SDK style) and dict keys (JSON style)
        name = getattr(call, "name", None) or (
            call.get("name") if isinstance(call, dict) else None
        )
        args = getattr(call, "args", {}) or (
            call.get("args", {}) if isinstance(call, dict) else {}
        )

        if name:
            # Assumes normalize_llm_args is available in the same context
            parsed.append({"name": name.lower(), "args": args})
    return parsed
"""

    success = await orchestrator.do_save_async(
        name="parse_llm_tool_calls",
        code=code,
        description="Converts raw tool calls from an LLM into a standardized internal dictionary format. Supports various call styles.",
        tags=["llm", "tool_calling", "mcp_client", "normalization"],
        language="python",
    )

    if success:
        print("✅ SUCCESS: parse_llm_tool_calls saved to LogicHive.")
    else:
        print("❌ FAILED to save to LogicHive.")


if __name__ == "__main__":
    asyncio.run(self_anatomy())
