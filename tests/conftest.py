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

from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_intel():
    """Provides a mocked LogicIntelligence engine."""
    mock = MagicMock()
    
    async def side_effect_eval(code):
        # Allow tests to trigger failure by using 'broken' or 'bad' in name or providing broken brackets
        # (Though orchestrator now catches brackets, this is a fallback)
        if "bad" in code.lower() or "broken" in code.lower() or "(" in code and ")" not in code:
            return {"score": 0, "reason": "Mocked rejection for poor quality."}
        return {"score": 85, "reason": "Mocked technical specification pass."}
        
    # Mock async methods
    mock.generate_embedding = AsyncMock(return_value=[0.1] * 768)
    mock.evaluate_quality = AsyncMock(side_effect=side_effect_eval)
    mock.expand_query = AsyncMock(side_effect=lambda x: x)
    # Mock other methods
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
