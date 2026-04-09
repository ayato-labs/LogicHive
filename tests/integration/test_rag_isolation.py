import pytest
from orchestrator import do_save_async, do_search_async
from storage.sqlite_api import sqlite_storage

@pytest.mark.asyncio
async def test_rag_project_isolation(test_db):
    """
    Verifies that search results are strictly isolated by project.
    """
    # 1. Save same function name in two different projects
    code_a = "def test(): return 'Project A'"
    code_b = "def test(): return 'Project B'"
    
    await do_save_async(name="iso_func", code=code_a, project="alpha")
    await do_save_async(name="iso_func", code=code_b, project="beta")
    
    # 2. Search in Project Alpha
    results_alpha = await do_search_async(query="iso_func", project="alpha")
    assert len(results_alpha) > 0
    # Every result in alpha must be project 'alpha'
    for res in results_alpha:
        assert res["project"] == "alpha"
        assert "Project B" not in (res.get("code") or "")
        
    # 3. Search in Project Beta
    results_beta = await do_search_async(query="iso_func", project="beta")
    assert len(results_beta) > 0
    for res in results_beta:
        assert res["project"] == "beta"
        
    # 4. Global search (no project) - should return from 'default' (or empty if not found in default)
    results_none = await do_search_async(query="iso_func", project=None)
    # If project is None, it should default to 'default' or some global scope
    # Our implementation uses project-based filtering if project is provided.
    # If project is None, VectorIndexManager currently might search everything OR default.
    # We hardened it to use the filter.
    for res in results_none:
        assert res["project"] == "default"
