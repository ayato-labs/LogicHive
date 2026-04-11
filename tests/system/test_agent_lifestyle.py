import os
from pathlib import Path

import pytest

from orchestrator import do_list_async, do_save_async, do_search_async
from storage.auto_backup import backup_manager
from storage.sqlite_api import sqlite_storage


@pytest.fixture
async def full_env(test_db, tmp_path):
    """Sets up a clean environment for system testing using a temporary directory."""
    original_export_dir = backup_manager.export_dir
    temp_export_dir = str(tmp_path / "exports_sys")
    backup_manager.export_dir = temp_export_dir
    os.makedirs(temp_export_dir, exist_ok=True)
    # Create dummy .git to satisfy get_all_backup_assets check
    os.makedirs(os.path.join(temp_export_dir, ".git"), exist_ok=True)

    yield Path(temp_export_dir)

    backup_manager.export_dir = original_export_dir

@pytest.mark.asyncio
async def test_full_agent_workflow(full_env):
    """
    Simulates a full end-to-end agent workflow:
    Save -> List -> Sync-Out -> Edit -> Sync-In -> Search
    """
    print("\n[Step 1] Agent saves a new logic asset...")
    name = "workflow_func"
    code = "def workflow_func(): return 'original'"
    await do_save_async(
        name=name,
        code=code,
        description="Original logic",
        tags=["workflow"],
        test_code="assert workflow_func() == 'original'"
    )

    # Verify in DB
    saved = await sqlite_storage.get_function_by_name(name)
    assert saved["code"] == code

    print("[Step 2] Agent lists assets to verify...")
    listed = await do_list_async(tags=["workflow"])
    assert any(f["name"] == name for f in listed)

    print("[Step 3] System performs 2-way sync (Export phase)...")
    db_assets = await sqlite_storage.get_all_functions()
    await backup_manager.bulk_export(db_assets)

    file_path = full_env / "projects" / "default" / "functions" / "python" / f"{name}.py"
    assert file_path.exists()

    print("[Step 4] Simulation: User/Tool edits the file externally...")
    new_code = "def workflow_func(): return 'optimized'"
    file_path.write_text(new_code)

    print("[Step 5] System performs 2-way sync (Import phase)...")
    assets_from_files = await backup_manager.get_all_backup_assets()
    for a in assets_from_files:
        await sqlite_storage.upsert_function(a)

    # Verify update
    re_saved = await sqlite_storage.get_function_by_name(name)
    assert re_saved["code"] == new_code

    print("[Step 6] Agent searches for the logic using semantic query...")
    # do_search_async uses FakeLogicIntelligence which expanding query to 'TECHNICAL_QUERY: ...'
    # and searching vector store. Since we updated the DB, and vector store removal is background,
    # we might need to manually trigger vector update for this test or wait.
    # Actually upsert_function updates vectors.

    # The FakeLogicIntelligence embedding is deterministic based on name/desc/tags.
    # Since we only updated code, and metadata optimization might have changed desc/tags,
    # we check if it hits.

    results = await do_search_async("workflow logic helper")
    assert len(results) > 0
    assert results[0]["name"] == name

    print("Agent Lifestyle Test: PASSED")
