import pytest
import os
import sys
import aiosqlite
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

@pytest.fixture(scope="function")
async def test_db():
    """Provides a temporary SQLite database for testing."""
    db_path = "test_logichive.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    os.environ["SQLITE_DB_PATH"] = db_path
    
    # Initialize DB
    from storage.init_db import init_db
    await init_db()
    
    yield db_path
    
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture(scope="function")
def mock_intel(mocker):
    """Mocks LogicIntelligence to avoid real AI calls during unit tests."""
    # Patch the class where it's imported (orchestrator.py)
    mock = mocker.patch("orchestrator.LogicIntelligence")
    instance = mock.return_value
    
    # Setup default mock behaviors
    instance.optimize_metadata.return_value = {
        "description": "Mocked technical specification for test purposes.",
        "tags": ["mock", "test", "logic"]
    }
    instance.generate_embedding.return_value = [0.1] * 768
    instance.construct_search_document.return_value = "Mock Search Doc"
    
    return instance
