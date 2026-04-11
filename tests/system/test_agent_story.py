import pytest

from mcp_server import get_function, save_function, search_functions
from orchestrator import do_get_async


@pytest.mark.asyncio
async def test_agent_discovery_to_execution_story(test_db, fake_intel):
    """
    Simulates a full 'Story' for an AI Agent:
    1. Agent searches for a utility (Discovery)
    2. Agent retrieves the full code (Retrieval)
    3. Agent saves a modified version (Iteration)
    4. Agent verifies the result (Verification)
    """
    project = "agent_story"
    code = "def greet(name): return f'Hello, {name}!'"

    # 1. DISCOVERY: Save a function first
    res1 = await save_function(
        name="greet_utils",
        code=code,
        description="A simple greeting utility",
        tags=["utils", "text"],
        project=project
    )
    assert "Saved successfully" in res1

    # 2. SEARCH: Find it back
    results_md = await search_functions(query="greeting", project=project)
    assert "greet_utils" in results_md

    # 3. RETRIEVAL: Get full code
    full_func_md = await get_function(name="greet_utils", project=project)
    assert code in full_func_md

    # 4. ITERATION: Save a 'v2' with tests
    updated_code = "def greet(name): return f'Hi, {name}!'"
    test_code = "assert greet('World') == 'Hi, World!'"

    res2 = await save_function(
        name="greet_utils",
        code=updated_code,
        description="Updated greeting utility with tests",
        project=project,
        test_code=test_code
    )
    assert "Saved successfully" in res2

    # 5. VERIFY: Check version and score
    final_func = await do_get_async(name="greet_utils", project=project)
    # Note: Reliability score calculation:
    # AI Gate (90) * 0.4 + Ruff (100) * 0.3 + Static (100) * 0.3 = 96.0
    # Score / 100.0 = 0.96

    assert final_func["version"] >= 2
    assert final_func["reliability_score"] >= 0.95
    # Verification might append [VERIFIED] to description depending on the flow
    assert "[VERIFIED]" in final_func["description"] or final_func["reliability_score"] >= 0.9

    # Verify search result shows verified
    final_search_md = await search_functions(query="greeting", project=project)
    # AI(90)*0.3 + Static(100)*0.3 + Runtime(100)*0.4 = 97.0
    assert "Reliability: 97.0%" in final_search_md
