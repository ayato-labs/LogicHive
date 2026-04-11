import sys
from pathlib import Path

import pytest

# Ensure root is in path to reach tools/audit
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir / "tools" / "audit"))
from stabilize_vault import stabilize_vault  # noqa: E402


@pytest.mark.asyncio
async def test_stabilize_vault_promotion_logic(test_db):
    """
    Verifies that a successful sandbox run promotes a draft to VERIFIED.
    """
    from storage.sqlite_api import sqlite_storage

    # 1. Create a successful draft
    name = "success_draft"
    await sqlite_storage.upsert_function({
        "name": name,
        "project": "test_project",
        "code": "def func(x): return x + 1",
        "test_code": "assert func(1) == 2",
        "description": "[AI-DRAFT] Will pass",
        "language": "python",
        "embedding": [0.1] * 768
    })

    # 2. Run stabilization (Not dry-run)
    await stabilize_vault(dry_run=False, project="test_project")

    # 3. Verify promotion
    func = await sqlite_storage.get_function_by_name(name, project="test_project")
    assert "[VERIFIED]" in func["description"]
    assert "[AI-DRAFT]" not in func["description"]
    assert func["reliability_score"] == 1.0

@pytest.mark.asyncio
async def test_stabilize_vault_failure_flagging(test_db):
    """
    Verifies that a failing sandbox run flags the draft with error details.
    """
    from storage.sqlite_api import sqlite_storage

    # 1. Create a failing draft
    name = "fail_draft"
    await sqlite_storage.upsert_function({
        "name": name,
        "project": "test_project",
        "code": "def func(x): return x + 1",
        "test_code": "assert func(1) == 99", # Will fail
        "description": "[AI-DRAFT] Will fail",
        "language": "python",
        "embedding": [0.1] * 768
    })

    # 2. Run stabilization
    await stabilize_vault(dry_run=False, project="test_project")

    # 3. Verify flagging
    func = await sqlite_storage.get_function_by_name(name, project="test_project")
    assert "[AI-DRAFT]" in func["description"]
    assert "Validation Failed" in func["description"]
    assert func["reliability_score"] < 1.0

@pytest.mark.asyncio
async def test_stabilize_vault_skip_no_tests(test_db):
    """
    Verifies that drafts without test code are skipped.
    """
    from storage.sqlite_api import sqlite_storage

    # 1. Create a draft without tests
    name = "skip_draft"
    await sqlite_storage.upsert_function({
        "name": name,
        "project": "test_project",
        "code": "def func(): pass",
        "test_code": "", # Empty
        "description": "[AI-DRAFT] No tests",
        "language": "python",
        "embedding": [0.1] * 768
    })

    # 2. Run stabilization
    await stabilize_vault(dry_run=False, project="test_project")

    # 3. Verify no change
    func = await sqlite_storage.get_function_by_name(name, project="test_project")
    assert "[AI-DRAFT]" in func["description"]
    assert "[VERIFIED]" not in func["description"]
