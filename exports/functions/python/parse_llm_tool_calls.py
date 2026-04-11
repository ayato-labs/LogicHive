from typing import Any

def parse_llm_tool_calls(calls: list[Any]) -> list[dict[str, Any]]:
    """
    Strictly converts LLM-native tool calls (from SDK or RAW response) to an internal structured list.
    Handles both object-attribute style (SDK) and dictionary style (JSON) tool calls.
    Integrates argument normalization.
    """
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
