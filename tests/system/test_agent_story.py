import pytest
from mcp_server import mcp

@pytest.mark.asyncio
async def test_agent_discovery_to_execution_story(test_db):
    """
    Simulates a full 'Story' for an AI Agent:
    1. Agent searches for a utility (Discovery)
    2. Agent retrieves the full code (Retrieval)
    3. Agent saves a modified version (Iteration)
    4. Agent verifies the result (Verification)
    """
    project = "agent_story"
    code = "def greet(name): return f'Hello, {name}!'"
    
    # 1. DISCOVERY: Save a function first so we can find it
    # We use the actual MCP tool call interface (internal access)
    from mcp_server import save_function
    await save_function(
        name="greet_utils",
        code=code,
        description="A simple greeting utility",
        tags=["utils", "text"],
        project=project
    )
    
    # 2. SEARCH: Find it back
    from mcp_server import search_functions
    # search_functions returns a Markdown string
    results_md = await search_functions(query="greeting", project=project)
    assert "greet_utils" in results_md
    assert "Match:" in results_md
    
    # 3. RETRIEVAL: Get full code
    from mcp_server import get_function
    # get_function returns Markdown with a code block
    full_func_md = await get_function(name="greet_utils", project=project)
    assert code in full_func_md
    assert "Function: greet_utils" in full_func_md
    
    # 4. ITERATION: Save a 'v2' and verify it runs
    updated_code = "def greet(name): return f'Hi, {name}!'"
    test_code = "assert greet('World') == 'Hi, World!'"
    
    await save_function(
        name="greet_utils",
        code=updated_code,
        project=project,
        test_code=test_code
    )
    
    # 5. VERIFY: Final retrieval via orchestrator to check raw data
    from mcp_server import orchestrator
    final_func = await orchestrator.do_get_async(name="greet_utils", project=project)
    assert final_func["version"] == 2
    assert final_func["reliability_score"] > 0.8 # Should be high (0.0 to 1.0)
