import pytest
import os
import asyncio
from pathlib import Path

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

@pytest.fixture(scope="session", autouse=True)
def global_mock_ai():
    """Globally mocks AI components if GEMINI_API_KEY is missing, ensuring CI passes."""
    if not os.environ.get("GEMINI_API_KEY"):
        # Create a universal mock for LogicIntelligence
        mock_intel_inst = MagicMock()
        mock_intel_inst.generate_embedding = AsyncMock(return_value=[0.1] * 768)
        mock_intel_inst.evaluate_quality = AsyncMock(return_value={"score": 85, "reason": "Mocked pass"})
        mock_intel_inst.expand_query = AsyncMock(side_effect=lambda x: x)
        mock_intel_inst.rerank_results = AsyncMock(side_effect=lambda q, res, limit: res[:limit])
        mock_intel_inst.optimize_metadata = MagicMock(return_value={"description": "Mocked technical desc", "tags": ["mock"]})
        mock_intel_inst.construct_search_document = MagicMock(return_value="search doc")

        # Create a universal mock for EvaluationManager
        mock_eval_inst = MagicMock()
        mock_eval_inst.evaluate_all = AsyncMock(return_value={"score": 85.0, "reason": "Mocked validation pass", "details": {}})

        # Patch multiple potential import paths
        patches = [
            patch("orchestrator.LogicIntelligence", return_value=mock_intel_inst),
            patch("orchestrator.EvaluationManager", return_value=mock_eval_inst),
            patch("core.consolidation.LogicIntelligence", return_value=mock_intel_inst),
            patch("api.server.EvaluationManager", return_value=mock_eval_inst),
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
    """Provides a mocked LogicIntelligence engine for specific test overrides."""
    mock = MagicMock()
    
    async def side_effect_eval(code):
        if "bad" in code.lower() or "broken" in code.lower() or ("(" in code and ")" not in code):
            return {"score": 0, "reason": "Mocked rejection for poor quality."}
        return {"score": 85, "reason": "Mocked technical specification pass."}
        
    mock.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    mock.evaluate_quality = AsyncMock(side_effect=side_effect_eval)
    mock.expand_query = AsyncMock(side_effect=lambda x: x)
    mock.rerank_results = AsyncMock(side_effect=lambda q, res, limit: res[:limit])
    mock.optimize_metadata = MagicMock(return_value={"description": "Mocked technical desc", "tags": ["mock"]})
    mock.construct_search_document = MagicMock(return_value="search doc")
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
    import numpy as np
    vector_manager.id_to_name = {}
    vector_manager.name_to_id = {}
    vector_manager._current_id = 0
    vector_manager.index = faiss.IndexFlatIP(768)
    vector_manager._initialized = True # Force initialized to skip loading during unit tests
    yield
