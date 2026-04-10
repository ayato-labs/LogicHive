import pytest
from orchestrator import do_save_async, do_search_async, do_delete_async
from storage.sqlite_api import sqlite_storage

@pytest.mark.asyncio
async def test_full_project_isolation(test_db, mock_intel):
    """
    Integration test: Verifies that data remains strictly partitioned by 'project'.
    """
    common_name = "multi_proj_func"
    
    # 1. Save in Project Alpha
    await do_save_async(
        name=common_name,
        code="def alpha(): return 'A'",
        project="alpha",
        tags=["tag-a"]
    )
    
    # 2. Save in Project Beta (Same name, different code)
    await do_save_async(
        name=common_name,
        code="def beta(): return 'B'",
        project="beta",
        tags=["tag-b"]
    )
    
    # 3. Verify SQL Retrieval isolation
    func_a = await sqlite_storage.get_function_by_name(common_name, project="alpha")
    assert "alpha" in func_a["code"]
    
    func_b = await sqlite_storage.get_function_by_name(common_name, project="beta")
    assert "beta" in func_b["code"]
    
    # 4. Verify Vector Search isolation
    # Mock embedding for 'alpha'
    mock_intel.generate_embedding.return_value = [0.1] * 768
    results_a = await do_search_async("query", project="alpha")
    assert len(results_a) == 1
    assert results_a[0]["name"] == common_name
    
    # Search in 'default' project should not contain our project-specific function
    results_def = await do_search_async("query", project="default")
    # Instead of zero (to avoid noise from global drafts), ensure OUR function isn't there
    found_names_def = [res["name"] for res in results_def]
    assert common_name not in found_names_def
    
    # 5. Verify Deletion isolation
    await do_delete_async(common_name, project="alpha")
    # Alpha should be gone
    assert await sqlite_storage.get_function_by_name(common_name, project="alpha") is None
    # Beta should still exist
    assert await sqlite_storage.get_function_by_name(common_name, project="beta") is not None
