import pytest
import asyncio
from src.orchestrator import do_save_async, do_search_async, check_integrity
from src.core.execution.pool import PoolManager

@pytest.mark.usefixtures("test_db")
@pytest.mark.asyncio
async def test_story_agent_resilience_and_stability():
    """
    System: Comprehensive story of an agent trying to save bad code, 
    fixing it, and ensuring the server stays stable (no EOF).
    """
    # 1. Agent tries to save a function with a vulnerability (eval)
    # This simulates a "Hostile" or "Lazy" agent session.
    bad_code = "def shell_exec(cmd): eval(cmd)"
    try:
        await do_save_async(
            name="agent_tool_v1",
            code=bad_code,
            description="A utility that executes dynamic code",
            test_code="def test_stub(): assert True"
        )
        pytest.fail("Security Gate failed to block 'eval'")
    except Exception as e:
        assert "Security" in str(e) or "Gate" in str(e)
    
    # 2. Agent "learns" from the reason and fixes the code
    fixed_code = "def safe_calc(a, b): return a + b"
    await do_save_async(
        name="agent_tool_v2",
        code=fixed_code,
        description="A safe calculator",
        test_code="def test_calc(): assert safe_calc(1, 2) == 3"
    )
    
    # Assert success check (search)
    search_res = await do_search_async(query="agent_tool_v2")
    # search_res is a list of dicts, check if any has the correct name
    # We might need to fetch the full function to verify code if needed, 
    # but for this test, name existence is enough.
    found = False
    for r in search_res:
        if r.get("name") == "agent_tool_v2":
            found = True
            break
    assert found, f"agent_tool_v2 not found in search results: {search_res}"

    # 3. Verify Server Stability (Anti-EOF Resilience)
    # We simulate a trigger that used to cause blocking/timeout: Pool initialization.
    # We ensure that even if a heavy operation (cleanup) is requested, 
    # the orchestrator remains responsive within a tight deadline.
    pool = PoolManager()
    
    try:
        # Wrap the initialization in a timeout to prove it doesn't block the loop
        async with asyncio.timeout(5.0): # 5 seconds is safer for CI
            await pool.initialize()
        
        # Check integrity while pool might still be working in background
        integrity = await check_integrity()
        # Vector store might be 'Warning' if no embeddings are saved yet, which is fine.
        assert integrity["status"] in ("Healthy", "Warning")
        assert "pool_manager" in integrity["details"]
    except asyncio.TimeoutError:
        pytest.fail("EOF Resilience Test Failed: Pool initialization blocked the event loop for too long.")

@pytest.mark.usefixtures("test_db")
@pytest.mark.asyncio
async def test_story_mass_request_chaos():
    """System: Hammer the server with parallel requests to ensure no connection drops."""
    
    tasks = []
    for i in range(10): # Simultaneous parallel requests
        tasks.append(do_search_async(query=f"test_{i}"))
    
    # If any of these cause an EOF or crash, the gather will raise or fail
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for res in results:
        assert not isinstance(res, Exception), f"Server crashed or dropped connection: {res}"
