import os
from pathlib import Path

import pytest

from storage.auto_backup import backup_manager
from storage.sqlite_api import sqlite_storage


@pytest.fixture
async def sync_env(test_db, tmp_path):
    """Sets up a clean environment for sync testing using a temporary directory."""
    # Override the export_dir in the singleton backup_manager
    original_export_dir = backup_manager.export_dir
    temp_export_dir = str(tmp_path / "exports")
    backup_manager.export_dir = temp_export_dir
    os.makedirs(temp_export_dir, exist_ok=True)
    # Create dummy .git to satisfy get_all_backup_assets check
    os.makedirs(os.path.join(temp_export_dir, ".git"), exist_ok=True)

    yield Path(temp_export_dir)

    # Restore original path
    backup_manager.export_dir = original_export_dir


@pytest.mark.asyncio
async def test_sync_bidirectional_idempotency(sync_env, mock_intel):
    """
    Verifies the flow: DB -> Export -> Files -> Modify File -> Import -> DB.
    Uses mock_intel (MagicMock) for LLM parts if any.
    """
    # ---------------------------------------------------------
    # 1. EXPORT PHASE (DB -> Files)
    # ---------------------------------------------------------
    asset = {
        "name": "sync_test",
        "project": "default",
        "code": "def hello(): pass",
        "description": "Original",
        "tags": ["sync"],
        "language": "python",
        "code_hash": "hash1",
    }
    await sqlite_storage.upsert_function(asset)

    # Export
    db_assets = await sqlite_storage.get_all_functions()
    await backup_manager.bulk_export(db_assets)

    # Verify file exists
    # Structure: exports/projects/{project}/functions/{lang}/{name}.{ext}
    file_path = sync_env / "projects" / "default" / "functions" / "python" / "sync_test.py"
    assert file_path.exists()
    assert "def hello(): pass" in file_path.read_text()

    # ---------------------------------------------------------
    # 2. MODIFY PHASE (Simulate External Edit)
    # ---------------------------------------------------------
    updated_code = "def hello(): print('sync worked')"
    file_path.write_text(updated_code)

    # ---------------------------------------------------------
    # 3. IMPORT PHASE (Files -> DB)
    # ---------------------------------------------------------
    assets_from_files = await backup_manager.get_all_backup_assets()

    # Filter for our specific test asset
    our_asset = next((a for a in assets_from_files if a["name"] == "sync_test"), None)
    assert our_asset is not None

    for a in assets_from_files:
        await sqlite_storage.upsert_function(a)

    # Verify DB is updated
    db_asset = await sqlite_storage.get_function_by_name("sync_test")
    assert db_asset["code"] == updated_code
    # check description and tags preserved (metadata json check)
    assert "sync" in db_asset["tags"]


@pytest.mark.asyncio
async def test_sync_new_file_discovery(sync_env):
    """Verifies that a new file created in the mirror is picked up by the DB."""
    # Manually create a file + metadata in the mirror
    func_dir = sync_env / "projects" / "new_proj" / "functions" / "python"
    meta_dir = sync_env / "projects" / "new_proj" / "metadata"
    func_dir.mkdir(parents=True)
    meta_dir.mkdir(parents=True)

    code = "def new_logic(): return True"
    (func_dir / "new_logic.py").write_text(code)

    import json

    meta = {"name": "new_logic", "description": "From external", "tags": ["external"]}
    (meta_dir / "new_logic.json").write_text(json.dumps(meta))

    # Import
    assets_from_files = await backup_manager.get_all_backup_assets()
    for a in assets_from_files:
        await sqlite_storage.upsert_function(a)

    # Verify in DB
    db_asset = await sqlite_storage.get_function_by_name("new_logic", project="new_proj")
    assert db_asset is not None
    assert db_asset["code"] == code
    assert db_asset["project"] == "new_proj"
    assert "external" in db_asset["tags"]
