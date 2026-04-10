import pytest
from orchestrator import do_save_async, do_get_async
from pathlib import Path
import sys

# Add tools/audit to path
sys.path.append(str(Path(__file__).parent.parent.parent / "tools" / "audit"))
from stabilize_vault import stabilize_vault  # noqa: E402

@pytest.mark.asyncio
async def test_draft_to_verified_integration_flow(test_db):
    """
    End-to-End integration test:
    1. Save a new function with [AI-DRAFT] tag via Orchestrator.
    2. Run the stabilize_vault audit tool.
    3. Verify that the function is promoted to [VERIFIED].
    """
    project = "integration_test_project"
    name = "integration_func"
    code = "def integration_add(a, b): return a + b"
    test_code = "assert integration_add(10, 20) == 30"
    
    # Step 1: Save via Orchestrator
    # We use a description that includes [AI-DRAFT]
    await do_save_async(
        name=name,
        code=code,
        description="[AI-DRAFT] Initial draft for integration test",
        test_code=test_code,
        project=project
    )
    
    # Confirm it is saved as draft
    initial = await do_get_async(name, project=project)
    assert "[AI-DRAFT]" in initial["description"]
    assert initial["reliability_score"] < 1.0
    
    # Step 2: Run Auditor
    # This simulates the background stabilizer process
    await stabilize_vault(dry_run=False, project=project)
    
    # Step 3: Verify Promotion
    final = await do_get_async(name, project=project)
    assert "[VERIFIED]" in final["description"]
    assert "[AI-DRAFT]" not in final["description"]
    assert final["reliability_score"] == 1.0

@pytest.mark.asyncio
async def test_failed_audit_integration_flow(test_db):
    """
    Integration test for a failing audit:
    1. Save a draft with failing test code.
    2. Run Auditor.
    3. Verify it remains as AI-DRAFT with error logs.
    """
    project = "fail_test_project"
    name = "fail_integration_func"
    code = "def broken_func(): return False"
    test_code = "assert broken_func() == True" # Will fail
    
    await do_save_async(
        name=name,
        code=code,
        description="[AI-DRAFT] This will fail audit",
        test_code=test_code,
        project=project
    )
    
    await stabilize_vault(dry_run=False, project=project)
    
    final = await do_get_async(name, project=project)
    assert "[AI-DRAFT]" in final["description"]
    assert "Validation Failed" in final["description"]
    assert final["reliability_score"] < 1.0
