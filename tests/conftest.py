import asyncio
import os

import pytest

# Set environment variables for testing BEFORE any imports
os.environ["SQLITE_DB_PATH"] = os.path.join("storage", "data", "test", "test_logichive.db")
os.environ["FAISS_INDEX_PATH"] = os.path.join("storage", "data", "test", "test_faiss_index.bin")
os.environ["FAISS_MAPPING_PATH"] = os.path.join(
    "storage", "data", "test", "test_faiss_mapping.json"
)

# Add src to sys.path
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import AsyncMock, MagicMock, patch


class FakeLogicIntelligence:
    """
    A deterministic fake for LogicIntelligence that avoids MagicMock.
    Returns stable results for testing without external API calls.
    """

    def __init__(self, api_key="fake_key"):
        self.api_key = api_key

    async def generate_embedding(self, text: str):
        # Deterministic dummy embedding: repeating a simple hash of the text
        import hashlib

        h = int(hashlib.md5(text.encode()).hexdigest(), 16)
        val = (h % 1000) / 1000.0
        return [val] * 768

    async def evaluate_quality(self, code: str, **kwargs):
        # Basic heuristic for "good" vs "bad" code for testing
        if len(code) < 10 or "error" in code.lower():
            return {"score": 10, "reason": "Fake: Code too short or contains 'error'"}
        return {"score": 90, "reason": "Fake: Looks good"}

    async def expand_query(self, query: str):
        # Deterministic expansion that avoids triggering global drafts
        return f"TECHNICAL_QUERY: {query}"

    async def rerank_results(self, query: str, results: list, limit: int = 5):
        return results[:limit]

    def construct_search_document(self, name: str, description: str, tags: list, code: str = ""):
        return f"{name} {description} {' '.join(tags)}"

    async def optimize_metadata(self, code: str):
        return {"description": "Automated description", "tags": ["auto"]}

    async def _call_llm_async(self, prompt: str, use_json: bool = False):
        """
        Simulates internal LLM calls used by plugins/consolidation.
        Uses keywords in prompt to trigger specific deterministic behaviors.
        """
        p_lower = prompt.lower()

        # Security/Vulnerability Triggers
        if "eval" in p_lower or "exec" in p_lower:
            return {"score": 0, "reason": "Fake: AI Auditor detected code injection risk."}
        if "secret_key" in p_lower or "api_key" in p_lower:
            return {"score": 20, "reason": "Fake: AI Auditor detected hardcoded credentials."}

        # Sophistry/Quality Theater Triggers
        if "pass" in p_lower and len(p_lower) < 50:
            return {
                "score": 10,
                "reason": "Fake: AI Auditor detected empty or stub implementation.",
            }

        # Error/Edge case triggers
        if "break" in p_lower:
            return None
        if "fail" in p_lower:
            return {}

        # Success response (Default)
        if use_json:
            return {
                "name": "fake_func",
                "code": 'def fake_func():\n    """Docstring."""\n    return True',
                "description": "A high-quality fake function generated for testing",
                "tags": ["fake", "unit-test"],
                "dependencies": [],
                "score": 98,
                "reason": "Fake: Verified production-grade logic.",
            }
        return "TECHNICAL_QUERY_EXPANSION"


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "use_real_intelligence: marker to skip the automatic patching of LogicIntelligence with FakeLogicIntelligence",
    )


@pytest.fixture(autouse=True)
def intelligence_isolation(request):
    """
    Autouse fixture that patches LogicIntelligence with its Fake implementation by default.
    Specific unit tests can opt-out using @pytest.mark.use_real_intelligence.
    """
    if "use_real_intelligence" in request.keywords:
        yield
        return

    patches = [
        patch("core.consolidation.LogicIntelligence", new=FakeLogicIntelligence),
        patch("orchestrator.LogicIntelligence", new=FakeLogicIntelligence),
        patch("core.plugins.draft_generator.LogicIntelligence", new=FakeLogicIntelligence),
        patch("core.evaluation.plugins.ai.LogicIntelligence", new=FakeLogicIntelligence),
    ]

    started_patches = []
    for p in patches:
        started_patches.append(p.start())

    yield

    for p in patches:
        p.stop()


@pytest.fixture(scope="session", autouse=True)
def global_test_config():
    """Placeholder for session-scoped setup (logic moved to sessionstart)."""
    yield


@pytest.fixture
def fake_intel():
    """Provides a deterministic FakeLogicIntelligence instance."""
    return FakeLogicIntelligence()


@pytest.fixture
def mock_intel():
    """Alias for integration_mock_intel to support existing tests."""
    mock = MagicMock()
    mock.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    mock.evaluate_quality = AsyncMock(return_value={"score": 85, "reason": "Mocked pass"})
    mock.optimize_metadata = AsyncMock(
        return_value={"description": "Optimized description", "tags": ["ai-tag"]}
    )
    return mock


@pytest.fixture
async def test_db():
    from core.db import close_db_connection
    from storage.init_db import init_db

    # Ensure any previous connection is closed/reset before initializing
    await close_db_connection()
    await init_db()
    # Give a tiny buffer for SQLite/aiosqlite state settle
    await asyncio.sleep(0.05)
    yield
    # CRITICAL: Close the singleton connection after each test to avoid thread reuse errors
    await close_db_connection()


@pytest.fixture(autouse=True)
async def clear_cache():
    """Resets the vector manager state between tests."""
    import os

    import faiss

    from storage.sqlite_api import vector_manager

    vector_manager.id_to_name = {}
    vector_manager.name_to_id = {}
    vector_manager._current_id = 0
    # Re-initialize to a fresh empty index
    vector_manager.index = faiss.IndexFlatIP(768)
    vector_manager._initialized = True

    # Also remove physical index files if they exist to prevent cross-contamination
    for f in [
        os.environ.get("FAISS_INDEX_PATH"),
        os.environ.get("FAISS_MAPPING_PATH"),
        os.environ.get("SQLITE_DB_PATH"),
    ]:
        if f and os.path.exists(f):
            try:
                # On Windows, we might need multiple attempts if the file is being closed
                import time

                for _ in range(3):
                    try:
                        os.remove(f)
                        break
                    except PermissionError:
                        time.sleep(0.1)
            except Exception:
                pass
    yield
