import pytest
import mcp_server
from orchestrator import sqlite_storage

@pytest.mark.asyncio
async def test_mcp_tools_e2e():
    """Tests the MCP tools as defined in mcp_server.py."""
    
    name = "e2e_tool_test"
    code = "def e2e_test(): return 'ok'"
    
    # 1. Test save_function tool
    result = await mcp_server.save_function(
        name=name,
        code=code,
        description="E2E test function",
        dependencies=["none"]
    )
    assert "Saved" in result
    
    # 2. Test search_functions tool
    search_result = await mcp_server.search_functions("e2e test function", limit=1)
    assert name in search_result
    
    # 3. Test get_function tool
    get_result = await mcp_server.get_function(name)
    assert code in get_result
    assert "```python" in get_result
    # Use lowercase check for robustness against LLM wording
    assert "dependencies" in get_result.lower(), "Markdown response must describe dependencies"

@pytest.mark.asyncio
async def test_mcp_quality_gate_rejection():
    """Tests that the MCP tool properly returns rejection messages."""
    
    name = "broken_e2e"
    code = "def broken("  # Syntax error
    
    result = await mcp_server.save_function(
        name=name,
        code=code
    )
    
    assert "Quality Gate REJECTED" in result
    # The user mandated that the error reason must be copy-pasteable for the client AI
    assert "syntax" in result.lower() or "error" in result.lower() or "invalid" in result.lower(), "Rejection message must contain the reason for the client AI to self-repair"
