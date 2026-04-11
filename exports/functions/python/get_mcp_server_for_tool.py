def get_mcp_server_for_tool(tool_name: str, tool_to_client_map: dict[str, str]) -> str | None:
    """
    Identifies which MCP server owns a specific tool based on a registry map.
    Returns None if the tool is not found.
    """
    return tool_to_client_map.get(tool_name)
