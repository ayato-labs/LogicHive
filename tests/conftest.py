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

# Global mock instances for session-wide access
_SESSION_MOCK_INTEL = MagicMock()
_SESSION_MOCK_EVAL = MagicMock()


@pytest.fixture(scope="session", autouse=True)
def global_mock_ai():
    """Globally mocks AI components if GEMINI_API_KEY is missing, ensuring CI passes."""
    if not os.environ.get("GEMINI_API_KEY"):
        # Configure universal mock for LogicIntelligence
        _SESSION_MOCK_INTEL.generate_embedding = AsyncMock(return_value=[0.1] * 768)
        _SESSION_MOCK_INTEL.evaluate_quality = AsyncMock(
            return_value={"score": 85, "reason": "Mocked pass"}
        )
        _SESSION_MOCK_INTEL.expand_query = AsyncMock(side_effect=lambda x: x)
        _SESSION_MOCK_INTEL.rerank_results = AsyncMock(
            side_effect=lambda q, res, limit: res[:limit]
        )
        _SESSION_MOCK_INTEL.optimize_metadata = MagicMock(
            return_value={"description": "Mocked technical desc", "tags": ["mock"]}
        )
        _SESSION_MOCK_INTEL.construct_search_document = MagicMock(
            return_value="search doc"
        )

        # Configure universal mock for EvaluationManager
        # Smarter mock for EvaluationManager to support quality gate rejections in tests
        async def mock_evaluate_all(code, language, **kwargs):
            # Instant rejection for obvious syntax errors (unbalanced brackets/tags)
            if (
                code.count("(") != code.count(")")
                or code.count("{") != code.count("}")
                or code.count("<") != code.count(">")
            ):
                from core.exceptions import ValidationError

                raise ValidationError(f"Mocked syntax error rejection ({language})")
            return {"score": 85.0, "reason": "Mocked validation pass", "details": {}}

        _SESSION_MOCK_EVAL.evaluate_all = AsyncMock(side_effect=mock_evaluate_all)

        # Patch multiple potential import paths using SAME instances
        patches = [
            patch("orchestrator.LogicIntelligence", return_value=_SESSION_MOCK_INTEL),
            patch("orchestrator.EvaluationManager", return_value=_SESSION_MOCK_EVAL),
            patch(
                "core.consolidation.LogicIntelligence", return_value=_SESSION_MOCK_INTEL
            ),
            patch(
                "core.evaluation.manager.EvaluationManager",
                return_value=_SESSION_MOCK_EVAL,
            ),
        ]

        for p in patches:
            p.start()

        yield

        for p in patches:
            p.stop()
    else:
        yield


@pytest.fixture
def mock_intel():
    """Provides the SAME session-scoped mock instance for call tracking in tests."""
    return _SESSION_MOCK_INTEL


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
