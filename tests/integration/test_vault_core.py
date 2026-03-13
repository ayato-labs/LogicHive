import pytest
import asyncio
from storage.sqlite_api import sqlite_storage
from core.exceptions import ValidationError, LogicHiveError

@pytest.mark.asyncio
async def test_save_and_get_function(test_db, mock_intel):
    """Verifies that a function can be saved with AI optimization and retrieved."""
    name = "calculate_sum"
    code = "def calculate_sum(a, b): return a + b"
    
    # Reset mock call count
    mock_intel.optimize_metadata.reset_mock()
    
    # Save
    success = await orchestrator.do_save_async(name, code, "Adds two numbers")
    assert success is True
    
    # Get
    data = await orchestrator.do_get_async(name)
    assert data["name"] == name
    assert data["code"] == code
    assert "Mocked technical" in data["description"]
    assert "mock" in data["tags"]

@pytest.mark.asyncio
async def test_duplicate_save_skips_ai(test_db, mock_intel):
    """Verifies that saving the same code twice skips redundant AI calls via hash check."""
    name = "hash_test"
    code = "def hash_test(): pass"
    
    mock_intel.optimize_metadata.reset_mock()
    
    # First save
    await orchestrator.do_save_async(name, code)
    assert mock_intel.optimize_metadata.call_count == 1
    
    # Second save (unchanged)
    await orchestrator.do_save_async(name, code)
    # AI optimization should NOT be called again
    assert mock_intel.optimize_metadata.call_count == 1

@pytest.mark.asyncio
async def test_semantic_search_integration(test_db, mock_intel):
    """Verifies that semantic search returns results via the mocked embedding path."""
    mock_intel.generate_embedding.reset_mock()
    
    await orchestrator.do_save_async("logic_a", "def a(): pass")
    # 1 call for save
    
    await orchestrator.do_search_async("Find some logic")
    # 1 call for query expansion + 1 call for query embedding in search
    
    assert mock_intel.generate_embedding.call_count >= 2
    assert mock_intel.expand_query.call_count == 1

@pytest.mark.asyncio
async def test_save_invalid_python_fails(test_db, mock_intel):
    """Verifies that invalid Python code is rejected via AST validation."""
    name = "bad_code"
    code = "def invalid(:" # Missing closing paren and indent
    
    with pytest.raises(ValidationError):
        await orchestrator.do_save_async(name, code, language="python")
    
    # Verify it was not saved
    data = await orchestrator.do_get_async(name)
    assert data is None

@pytest.mark.asyncio
async def test_save_invalid_multi_lang_fails(test_db, mock_intel):
    # 1. C-like bracket mismatch
    c_code = "void main() { int x = 1;" # Missing closing brace
    with pytest.raises(ValidationError):
        await orchestrator.do_save_async("bad_c", c_code, language="cpp")
    
    # 2. Markup tag mismatch (unbalanced angle brackets)
    html_code = "<div><span>Logic</span" # Missing closing '>'
    with pytest.raises(ValidationError):
        await orchestrator.do_save_async("bad_html", html_code, language="html")
    
    # 3. Valid C-like
    good_c = "void main() { return; }"
    success_good = await orchestrator.do_save_async("good_c", good_c, language="cpp")
    assert success_good is True
