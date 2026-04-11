import pytest

from orchestrator import do_save_async, do_search_async


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
        print(f"ISO_DEBUG Alpha Result: Name={res['name']}, Project={res['project']}, Code={res.get('code', 'N/A')}")
        assert res["project"] == "alpha"
        assert "Project B" not in (res.get("code") or "")

    # 3. Search in Project Beta
    results_beta = await do_search_async(query="iso_func", project="beta")
    assert len(results_beta) > 0
    for res in results_beta:
        print(f"ISO_DEBUG Beta Result: Name={res['name']}, Project={res['project']}, Code={res.get('code', 'N/A')}")
        assert res["project"] == "beta"
        assert "Project A" not in (res.get("code") or "")

    # 4. Global search - should return from 'default' (empty in this case)
    results_none = await do_search_async(query="iso_func", project="default")
    for res in results_none:
        # If any results leaked, verify they have project key
        assert "project" in res
        assert res["project"] == "default"
