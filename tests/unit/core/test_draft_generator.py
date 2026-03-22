import pytest
from core.plugins.draft_generator import DraftGenerator
from unittest.mock import MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_generate_draft_logic():
    # Mock LogicIntelligence
    mock_intel = MagicMock()
    # Mock AI response
    mock_ai_res = {
        "name": "mock_func",
        "code": "def mock_func(): pass",
        "description": "A mocked function",
        "tags": ["test"],
        "dependencies": [],
    }
    mock_intel._call_llm_async = AsyncMock(return_value=mock_ai_res)

    generator = DraftGenerator(mock_intel)

    query = "Search query"
    context = [
        {"name": "exist_1", "code": "def exist_1(): pass", "description": "existing"}
    ]

    res = await generator.generate_draft(query, context)

    assert res["is_draft"] is True
    assert "[AI-DRAFT]" in res["description"]
    assert res["name"] == "mock_func"
    assert res["provenance"] == "LogicHive Auto-Draft"

    # Verify mock call
    mock_intel._call_llm_async.assert_called_once()
    args, kwargs = mock_intel._call_llm_async.call_args
    assert "Search query" in args[0]
    assert "exist_1" in args[0]


@pytest.mark.asyncio
async def test_generate_draft_failure():
    mock_intel = MagicMock()
    mock_intel._call_llm_async = AsyncMock(return_value={})

    generator = DraftGenerator(mock_intel)
    res = await generator.generate_draft("fail", [])

    assert res == {}


@pytest.mark.asyncio
async def test_draft_generator_malformed_json():
    """HARDENING: Test response to malformed JSON from LLM."""
    mock_intel = MagicMock()
    # Simulate a case where _call_llm_async returns None or invalid due to parsing error
    mock_intel._call_llm_async = AsyncMock(return_value=None)

    generator = DraftGenerator(mock_intel)
    res = await generator.generate_draft("break", [])

    assert res == {}


@pytest.mark.asyncio
async def test_draft_generator_prompt_composition():
    """HARDENING: Verify that context is actually injected into the prompt."""
    mock_intel = MagicMock()
    mock_intel._call_llm_async = AsyncMock(return_value={"code": "pass", "name": "n"})

    generator = DraftGenerator(mock_intel)
    context = [
        {"name": "SECRET_PATTERN_A", "code": "def a(): pass", "description": "desc"}
    ]

    await generator.generate_draft("query", context)

    args, _ = mock_intel._call_llm_async.call_args
    prompt = args[0]
    assert "SECRET_PATTERN_A" in prompt
    assert "def a(): pass" in prompt
    assert "LogicHive Draft Assistant" in prompt


@pytest.mark.asyncio
async def test_draft_generator_missing_fields_recovery():
    """HARDENING: Test recovery when LLM omits some required keys but provides code."""
    mock_intel = MagicMock()
    # Missing 'name' and 'description'
    mock_intel._call_llm_async = AsyncMock(
        return_value={"code": "def recovery(): pass"}
    )

    generator = DraftGenerator(mock_intel)
    res = await generator.generate_draft("MyNewFunc", [])

    assert res["code"] == "def recovery(): pass"
    assert "description" in res
    assert "[AI-DRAFT]" in res["description"]
    assert res.get("language") == "python"
