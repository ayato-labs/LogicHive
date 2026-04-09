import pytest
import mcp_server
from storage.sqlite_api import sqlite_storage

@pytest.mark.asyncio
async def test_mcp_end_to_end_user_flow(test_db, mock_intel):
    """
    Simulates a full user (or AI agent) workflow via the MCP tool interface.
    """
    project = "user-workspace-1"
    func_name = "calculate_area"
    code = "import math\ndef calculate_area(r): return math.pi * r**2"
    
    # 1. Save tool
    save_msg = await mcp_server.save_function(
        name=func_name,
        code=code,
        description="Calculates circle area",
        project=project
    )
    assert "success" in save_msg.lower()
    
    # 2. Search tool
    # Pre-configure mock for search success
    mock_intel.generate_embedding.return_value = [0.1] * 768
    search_msg = await mcp_server.search_functions("circle area", project=project)
    assert "Search Results" in search_msg
    assert func_name in search_msg
    
    # 3. Get tool
    get_msg = await mcp_server.get_function(func_name, project=project)
    assert "```python" in get_msg
    assert "math.pi" in get_msg
    
    # 4. Delete tool
    del_msg = await mcp_server.delete_function(func_name, project=project)
    msg_lower = del_msg.lower()
    assert "successfully" in msg_lower and "deleted" in msg_lower
    
    # 5. Verify deletion
    verify_search = await mcp_server.search_functions("circle area", project=project)
    # It might return a draft, but should NOT return our saved function
    assert func_name not in verify_search

@pytest.mark.asyncio
async def test_mcp_project_separation_workflow(test_db, mock_intel):
    """Verifies that tools strictly respect the project argument."""
    # Save in Proj X
    await mcp_server.save_function("shared_tool", "pass", project="proj-x")
    
    # Get in Proj Y should fail
    get_y = await mcp_server.get_function("shared_tool", project="proj-y")
    assert "not found" in get_y.lower()
    
    # Search in Proj Y should not see it
    search_y = await mcp_server.search_functions("shared", project="proj-y")
    assert "shared_tool" not in search_y
