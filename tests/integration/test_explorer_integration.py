import pytest

from mcp_server import list_functions
from storage.sqlite_api import sqlite_storage


@pytest.mark.asyncio
async def test_mcp_list_functions_integration(test_db):
    """
    Verifies that the MCP tool correctly bridges to the storage.
    Since MCP tools in this project are just async functions, we call them directly.
    """
    # 1. Setup multiple assets
    assets = [
        {"name": "f1", "project": "pa", "tags": ["t1"], "code": "pass", "code_hash": "h1"},
        {"name": "f2", "project": "pa", "tags": ["t2"], "code": "pass", "code_hash": "h2"},
        {"name": "f3", "project": "pb", "tags": ["t1"], "code": "pass", "code_hash": "h3"},
    ]
    for a in assets:
        await sqlite_storage.upsert_function(a)

    # 2. Test project filter
    res_a = await list_functions(project="pa")
    assert "f1" in res_a
    assert "f2" in res_a
    assert "f3" not in res_a

    # 3. Test tag filter
    res_t1 = await list_functions(tags=["t1"])
    assert "f1" in res_t1
    assert "f3" in res_t1
    assert "f2" not in res_t1

    # 4. Test combined (Implicitly handled by storage)
    res_both = await list_functions(project="pb", tags=["t1"])
    assert "f3" in res_both
    assert "f1" not in res_both
