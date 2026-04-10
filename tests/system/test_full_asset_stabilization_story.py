import pytest
from orchestrator import do_save_async, do_search_async, do_get_async
from pathlib import Path
import sys

# Add tools/audit to path
sys.path.append(str(Path(__file__).parent.parent.parent / "tools" / "audit"))
from stabilize_vault import stabilize_vault  # noqa: E402

@pytest.mark.asyncio
async def test_complete_asset_lifecycle_story(test_db):
    """
    User Story:
    1. Search for a function that doesn't exist.
    2. System generates a draft (via fallback).
    3. User (or agent) saves the draft.
    4. Auditor stabilizes the draft.
    5. Search now returns the verified result.
    """
    project = "story_project"
    query = "implement factorial calculation"
    
    # 1. Search for missing function
    # Note: do_search_async triggers DraftGenerator if score < 0.45 and it's a generation request
    results = await do_search_async(query, project=project, limit=1)
    
    # Verify we got a draft
    assert len(results) > 0
    draft = results[0]
    assert "[AI-DRAFT]" in draft["description"]
    
    # 2. Save the draft
    # The orchestrator do_save_async handles the metadata enrichment and embedding
    # We add a dummy test_code here manually as if the user/agent provided it
    draft_name = draft["name"]
    draft_code = draft["code"]
    test_code = """
def test_factorial():
    from math import factorial
    # This is a bit recursive since we're testing the fake, 
    # but in a real scenario the draft_code would have the implementation.
    # For testing, we ensure the sandbox can run what's provided.
    pass
test_factorial()
"""
    
    save_success = await do_save_async(
        name=draft_name,
        code=draft_code,
        description=draft["description"],
        tags=draft.get("tags", []),
        test_code=test_code,
        project=project
    )
    assert save_success
    
    # 3. Verify it's in the vault as draft
    func_in_db = await do_get_async(draft_name, project=project)
    assert "[AI-DRAFT]" in func_in_db["description"]
    
    # 4. Trigger Stabilization (Audit)
    await stabilize_vault(dry_run=False, project=project)
    
    # 5. Final Search - Should find the verified function
    final_results = await do_search_async(query, project=project, limit=5)
    
    # Extract the asset we saved from the search results
    top_match = next((res for res in final_results if res["name"] == draft_name), None)
    
    assert top_match is not None, f"Asset '{draft_name}' not found in search results"
    assert "[VERIFIED]" in top_match["description"]
    # AI(90)*0.3 + Static(100)*0.3 + Runtime(100)*0.4 = 97.0 / 100 = 0.97
    assert top_match["reliability_score"] >= 0.95
