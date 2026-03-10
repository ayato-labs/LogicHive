# Pure Stateless Orchestrator for LogicHive Hub (Personal MVP)
import logging
from typing import Dict, List, Any, Optional
from storage.sqlite_api import sqlite_storage
from core.consolidation import LogicIntelligence
from core.hash_utils import calculate_code_hash
from core.config import GEMINI_API_KEY
import asyncio

logger = logging.getLogger(__name__)

# --- MCP / REST API Implementation Wrappers ---

async def do_save_async(
    name: str, 
    code: str, 
    description: str = "", 
    tags: List[str] = [], 
    language: str = "python"
):
    """
    Asynchronous implementation for saving a function.
    Includes on-the-fly RAG optimization (metadata generation + embedding).
    """
    # 1. Calculate code hash for deduplication
    code_hash = calculate_code_hash(code)
    
    # 2. Check for unchanged asset
    existing = await sqlite_storage.get_function_by_name(name)
    if existing and existing.get("code_hash") == code_hash:
        logger.info(f"Orchestrator: Skipping save for '{name}' (unchanged hash)")
        return True

    # 3. AI Enrichment (BYOK)
    intel = LogicIntelligence(GEMINI_API_KEY)
    
    logger.info(f"Orchestrator: Optimizing metadata for '{name}'...")
    optimized = await intel.optimize_metadata(code, description, tags)
    
    enriched_desc = optimized.get("description", description)
    enriched_tags = optimized.get("tags", tags)
    
    # 4. Generate Embedding for RAG
    search_doc = intel.construct_search_document(name, enriched_desc, enriched_tags, code)
    embedding = await intel.generate_embedding(search_doc)
    
    # 5. Prepare final data
    data = {
        "name": name,
        "code": code,
        "description": enriched_desc,
        "language": language,
        "tags": enriched_tags,
        "reliability_score": 1.0,
        "embedding": embedding,
        "code_hash": code_hash
    }
    
    return await sqlite_storage.upsert_function(data)


async def do_get_async(name: str) -> Optional[Dict[str, Any]]:
    """Asynchronous implementation for getting a function."""
    return await sqlite_storage.get_function_by_name(name)


async def do_search_async(query: str, limit: int = 5):
    """Asynchronous implementation for searching functions."""
    intel = LogicIntelligence(GEMINI_API_KEY)
    query_emb = await intel.generate_embedding(query)
    
    if query_emb:
        logger.info(f"Orchestrator: Performing semantic search for '{query}'")
        return await sqlite_storage.find_similar_functions(query_emb, limit=limit)
    
    logger.info(f"Orchestrator: Falling back to static search for '{query}'")
    return await sqlite_storage.find_functions_static(query, limit=limit)


# --- Synchronous Wrappers (Legacy/Compatibility) ---

def do_save_impl(*args, **kwargs):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return "Manual save required (Loop already running)"
    return "Saved" if loop.run_until_complete(do_save_async(*args, **kwargs)) else "Failed"

def do_get_impl(name):
    return asyncio.get_event_loop().run_until_complete(do_get_async(name))

def do_search_impl(query, limit=5):
    return asyncio.get_event_loop().run_until_complete(do_search_async(query, limit))
