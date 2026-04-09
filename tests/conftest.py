import pytest
import os

# Set environment variables for testing BEFORE any imports
os.environ["SQLITE_DB_PATH"] = "test_logichive.db"
os.environ["FAISS_INDEX_PATH"] = "test_faiss_index.bin"
os.environ["FAISS_MAPPING_PATH"] = "test_faiss_mapping.json"

# Add src to sys.path
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from storage.init_db import init_db
from storage.sqlite_api import vector_manager

from unittest.mock import MagicMock, AsyncMock, patch

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

    async def evaluate_quality(self, code: str):
        # Basic heuristic for "good" vs "bad" code for testing
        if len(code) < 10 or "error" in code.lower():
            return {"score": 10, "reason": "Fake: Code too short or contains 'error'"}
        return {"score": 90, "reason": "Fake: Looks good"}

    async def expand_query(self, query: str):
        return query

    async def rerank_results(self, query: str, results: list, limit: int = 5):
        return results[:limit]

    def construct_search_document(self, name: str, description: str, tags: list):
        return f"{name} {description} {' '.join(tags)}"

    def optimize_metadata(self, code: str):
        return {"description": "Automated description", "tags": ["auto"]}

    async def _call_llm_async(self, prompt: str, use_json: bool = False):
        """Simulates internal LLM calls used by plugins."""
        if "break" in prompt.lower():
            return None
        if "fail" in prompt.lower():
            return {}
        # Success response
        return {
            "name": "fake_func",
            "code": "def fake_func(): pass",
            "description": "A fake function generated for testing",
            "tags": ["fake"],
            "dependencies": []
        }


@pytest.fixture(scope="session", autouse=True)
def global_mock_ai():
    """Globally replaces AI components with deterministic Fakes if GEMINI_API_KEY is missing."""
    if not os.environ.get("GEMINI_API_KEY"):
        # We patch the Class itself to return a FakeLogicIntelligence instance
        # This is NOT MagicMock, it's a manual Fake fulfilling the user rule.
        patches = [
            patch("storage.sqlite_api.LogicIntelligence", side_effect=lambda *args, **kwargs: FakeLogicIntelligence()),
            patch("orchestrator.LogicIntelligence", side_effect=lambda *args, **kwargs: FakeLogicIntelligence()),
            patch("core.plugins.draft_generator.LogicIntelligence", side_effect=lambda *args, **kwargs: FakeLogicIntelligence()),
            patch("core.evaluation.plugins.ai.LogicIntelligence", side_effect=lambda *args, **kwargs: FakeLogicIntelligence()),
        ]

        for p in patches:
            p.start()
        yield
        for p in patches:
            p.stop()
    else:
        yield

@pytest.fixture
def fake_intel():
    """Provides a deterministic FakeLogicIntelligence instance."""
    return FakeLogicIntelligence()


@pytest.fixture
def mock_intel():
    """Provides a fresh MagicMock instance for integration tests (permits call tracking)."""
    from unittest.mock import MagicMock, AsyncMock
    mock = MagicMock()
    mock.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    mock.evaluate_quality = AsyncMock(return_value={"score": 85, "reason": "Mocked pass"})
    return mock


@pytest.fixture
async def test_db():
    """Fixtures that ensures a clean database FOR EACH TEST."""
    # Use session cleanup logic but trigger per-test
    db_path = os.environ.get("SQLITE_DB_PATH", "test_logichive.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    await init_db()
    yield
    # No immediate cleanup to allow debugging if needed, but next test will wipe it.


@pytest.fixture(autouse=True)
async def clear_cache():
    """Resets the vector manager state between tests and ensures it is marked as initialized for unit tests."""
    import faiss

    vector_manager.id_to_name = {}
    vector_manager.name_to_id = {}
    vector_manager._current_id = 0
    vector_manager.index = faiss.IndexFlatIP(768)
    vector_manager._initialized = (
        True  # Force initialized to skip loading during unit tests
    )
    yield
