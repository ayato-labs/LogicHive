import pytest
import orchestrator
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_orchestrator_draft_fallback(test_db, mock_intel):
    """
    Verifies that search_async triggers DraftGenerator when results are weak.
    """
    # 1. Setup weak mock search results (Similarity < 0.45)
    weak_result = {
        "name": "unrelated",
        "code": "def unrelated(): pass",
        "description": "Unrelated code",
        "similarity": 0.2,  # Very low
        "is_draft": False,
    }

    # Mock search result from DB
    with patch(
        "storage.sqlite_api.sqlite_storage.find_similar_functions",
        AsyncMock(return_value=[weak_result]),
    ):
        # Mock Draft synthesis
        draft_content = {
            "name": "synthesized_draft",
            "code": "def target_func(): pass",
            "description": "Synthesized",
            "is_draft": True,
            "provenance": "MockDraft",
        }

        with patch(
            "core.plugins.draft_generator.DraftGenerator.generate_draft",
            AsyncMock(return_value=draft_content),
        ):
            results = await orchestrator.do_search_async("Search for something missing")

            # Verify that Draft is prepended
            assert len(results) >= 2
            assert results[0]["name"] == "synthesized_draft"
            assert results[0]["is_draft"] is True
            assert results[1]["name"] == "unrelated"
            assert results[1]["is_draft"] is False


@pytest.mark.asyncio
async def test_orchestrator_boundary_conditions(test_db, mock_intel):
    """HARDENING: Test similarity boundary values (0.45)."""

    async def run_scenario(sim_value):
        weak_result = {
            "name": "edge_case",
            "code": "pass",
            "description": "d",
            "similarity": sim_value,
            "is_draft": False,
        }
        with patch(
            "storage.sqlite_api.sqlite_storage.find_similar_functions",
            AsyncMock(return_value=[weak_result]),
        ):
            with patch(
                "core.plugins.draft_generator.DraftGenerator.generate_draft",
                AsyncMock(return_value={"is_draft": True}),
            ):
                return await orchestrator.do_search_async("query")

    # 1. Just below threshold (0.44) -> SHOULD trigger draft
    res_below = await run_scenario(0.44)
    assert any(r.get("is_draft") for r in res_below)

    # 2. Just above threshold (0.46) -> SHOULD NOT trigger draft
    res_above = await run_scenario(0.46)
    assert not any(r.get("is_draft") for r in res_above)


@pytest.mark.asyncio
async def test_orchestrator_no_results_fallback(test_db, mock_intel):
    """HARDENING: Test when DB returns absolutely nothing."""
    with patch(
        "storage.sqlite_api.sqlite_storage.find_similar_functions",
        AsyncMock(return_value=[]),
    ):
        with patch(
            "core.plugins.draft_generator.DraftGenerator.generate_draft",
            AsyncMock(return_value={"name": "empty_recovery", "is_draft": True}),
        ):
            results = await orchestrator.do_search_async("empty query")
            assert len(results) == 1
            assert results[0]["name"] == "empty_recovery"
            assert results[0]["is_draft"] is True
