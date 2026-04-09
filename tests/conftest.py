import pytest
import os

# Set environment variables for testing BEFORE any imports
os.environ["SQLITE_DB_PATH"] = "test_logichive.db"
os.environ["FAISS_INDEX_PATH"] = "test_faiss_index.bin"
os.environ["FAISS_MAPPING_PATH"] = "test_faiss_mapping.json"

# Add src to sys.path
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

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
        # Deterministic expansion that avoids triggering global drafts
        return f"TECHNICAL_QUERY: {query}"

    async def rerank_results(self, query: str, results: list, limit: int = 5):
        return results[:limit]

    def construct_search_document(self, name: str, description: str, tags: list, code: str = ""):
        return f"{name} {description} {' '.join(tags)}"

    async def optimize_metadata(self, code: str):
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


def pytest_sessionstart(session):
    """
    Applied exactly once BEFORE any tests or module imports happen.
    Ensures absolute isolation and consistent mocking.
    Standard suite ALWAYS uses Fakes to ensure speed and stability.
    """
    import core.config
    core.config.QUALITY_GATE_THRESHOLD = 60

    # We patch the Class itself at the source to ensure ALL instances are Fakes
    # Standard practice for professional CI/CD: Tests must not depend on network/quotas.
    patches = [
        patch("core.consolidation.LogicIntelligence", new=FakeLogicIntelligence),
        patch("orchestrator.LogicIntelligence", new=FakeLogicIntelligence),
        patch("core.plugins.draft_generator.LogicIntelligence", new=FakeLogicIntelligence),
        patch("core.evaluation.plugins.ai.LogicIntelligence", new=FakeLogicIntelligence),
    ]
    for p in patches:
        p.start()


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
    """Provides a fresh MagicMock instance for integration tests (permits call tracking)."""
    from unittest.mock import MagicMock, AsyncMock
    mock = MagicMock()
    mock.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    mock.evaluate_quality = AsyncMock(return_value={"score": 85, "reason": "Mocked pass"})
    return mock


@pytest.fixture
async def test_db():
    """Fixtures that ensures a clean database FOR EACH TEST."""
    from storage.init_db import init_db
    db_path = os.environ.get("SQLITE_DB_PATH", "test_logichive.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    await init_db()
    yield


@pytest.fixture(autouse=True)
async def clear_cache():
    """Resets the vector manager state between tests."""
    import faiss
    from storage.sqlite_api import vector_manager
    import os

    vector_manager.id_to_name = {}
    vector_manager.name_to_id = {}
    vector_manager._current_id = 0
    # Re-initialize to a fresh empty index
    vector_manager.index = faiss.IndexFlatIP(768)
    vector_manager._initialized = True
    
    # Also remove physical index files if they exist to prevent cross-contamination
    for f in [os.environ.get("FAISS_INDEX_PATH"), os.environ.get("FAISS_MAPPING_PATH")]:
        if f and os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass
    yield
