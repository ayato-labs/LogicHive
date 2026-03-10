import pytest
import mcp_server

@pytest.mark.asyncio
async def test_mcp_save_tool(test_db, mock_intel):
    """Verifies the MCP save tool wrapper."""
    result = await mcp_server.save_function(
        name="mcp_test",
        code="print('hello')",
        description="test tool"
    )
    assert "Saved with AI optimization" in result

@pytest.mark.asyncio
async def test_mcp_get_tool_success(test_db, mock_intel):
    """Verifies the MCP get tool wrapper returns formatted markdown."""
    await mcp_server.save_function("tool_get_test", "x = 1")
    result = await mcp_server.get_function("tool_get_test")
    assert "```python" in result
    assert "x = 1" in result

@pytest.mark.asyncio
async def test_mcp_search_tool(test_db, mock_intel):
    """Verifies the MCP search tool wrapper returns formatted results."""
    await mcp_server.save_function("search_asset", "y = 2")
    result = await mcp_server.search_functions("test query")
    assert "### Search Results" in result
    assert "search_asset" in result
