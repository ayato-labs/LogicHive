import pytest

from core.plugins.draft_generator import DraftGenerator


@pytest.mark.asyncio
async def test_generate_draft_logic(fake_intel):
    """Verifies that the draft generator correctly synthesizes a function using FakeIntelligence."""
    generator = DraftGenerator(fake_intel)

    query = "Search query"
    context = [{"name": "exist_1", "code": "def exist_1(): pass", "description": "existing"}]

    res = await generator.generate_draft(query, context)

    assert res["is_draft"] is True
    assert "[AI-DRAFT]" in res["description"]
    assert res["name"] == "fake_func"  # From FakeLogicIntelligence
    assert res["provenance"] == "LogicHive Auto-Draft"


@pytest.mark.asyncio
async def test_generate_draft_failure(fake_intel):
    """Tests failure handling when AI returns empty dict."""
    generator = DraftGenerator(fake_intel)
    # Using 'fail' keyword to trigger empty response from FakeIntelligence
    res = await generator.generate_draft("fail", [])
    assert res == {}


@pytest.mark.asyncio
async def test_draft_generator_malformed_json(fake_intel):
    """Tests recovery from 'None' response (simulating malformed JSON)."""
    generator = DraftGenerator(fake_intel)
    # Using 'break' keyword to trigger None response from FakeIntelligence
    res = await generator.generate_draft("break", [])
    assert res == {}


@pytest.mark.asyncio
async def test_draft_generator_missing_fields_recovery(fake_intel):
    """
    Tests recovery when AI omits some fields.
    Note: Since FakeLogicIntelligence returns a complete dict, we verify
    that the generator still adds its decorations.
    """
    generator = DraftGenerator(fake_intel)
    res = await generator.generate_draft("RecoveryTest", [])

    assert "description" in res
    assert "[AI-DRAFT]" in res["description"]
    assert res.get("language") == "python"
