import logging
import ast
import asyncio
import re
from typing import Dict, List, Any, Optional
from storage.sqlite_api import sqlite_storage
from core.consolidation import LogicIntelligence
from core.config import GEMINI_API_KEY, QUALITY_GATE_THRESHOLD, DESCRIPTION_MIN_LENGTH
from core.exceptions import ValidationError, AIProviderError
from core.hash_utils import calculate_code_hash
from core.notifier import send_notification
from radon.complexity import cc_visit

from core.evaluation.manager import EvaluationManager
logger = logging.getLogger(__name__)

# --- Helpers ---

def extract_dependencies(code: str, language: str = "python") -> List[str]:
    """
    Extracts dependencies based on language.
    Python uses AST, while others use optimized regex.
    """
    dependencies = set()
    lang = language.lower()

    if lang == "python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base = alias.name.split(".")[0]
                        dependencies.add(base)
                elif isinstance(node, ast.ImportFrom):
                    if node.level == 0 and node.module:
                        base = node.module.split(".")[0]
                        dependencies.add(base)
        except Exception as e:
            logger.warning(f"Orchestrator: AST extraction failed, falling back to regex: {e}")
            # Fallback to regex for Python if AST fails
            matches = re.findall(r"^(?:import|from)\s+([a-zA-Z0-9_]+)", code, re.MULTILINE)
            dependencies.update(matches)
    
    elif lang in ["typescript", "javascript", "tsx", "jsx"]:
        # Regex for ES6 imports: from 'pkg' or from "pkg" (robust whitespace)
        es6_matches = re.findall(r"from\s+['\"]([^'\"./][^'\"]*)['\"]", code)
        # Regex for CommonJS: require('pkg')
        cjs_matches = re.findall(r"require\s*\(\s*['\"]([^'\"./][^'\"]*)['\"]\s*\)", code)
        # Simple import 'pkg'
        simple_matches = re.findall(r"import\s+['\"]([^'\"./][^'\"]*)['\"]", code)
        
        all_matches = es6_matches + cjs_matches + simple_matches
        for pkg in all_matches:
            # Extract scope if present (e.g. @types/node -> @types/node, but lodash/fp -> lodash)
            if pkg.startswith("@"):
                parts = pkg.split("/")
                if len(parts) >= 2:
                    dependencies.add(f"{parts[0]}/{parts[1]}")
                else:
                    dependencies.add(pkg)
            else:
                dependencies.add(pkg.split("/")[0])

    # Clean up standard libs/internal refs
    std_lib = {"os", "sys", "json", "math", "datetime", "typing", "asyncio", "logging", "ast", "pathlib", "abc", "fs", "path", "http", "https", "crypto"}
    return sorted(list(dependencies - std_lib))


# --- MCP / REST API Implementation Wrappers ---


async def do_save_async(
    name: str,
    code: str,
    description: str = "",
    tags: List[str] = [],
    language: str = "python",
    dependencies: List[str] = [],
    test_code: str = "",
):
    """
    Includes LLM Quality Gate 2.0 (LLM + Static Analysis), RAG optimization, and versioning.
    """
    # --- 1. Evaluate Logic Asset (New Plugin System) ---
    eval_manager = EvaluationManager()
    eval_res = await eval_manager.evaluate_all(code, language, description=description, tags=tags)
    
    final_score = eval_res["score"]
    reason = eval_res["reason"]

    if final_score < QUALITY_GATE_THRESHOLD:
        logger.warning(f"Orchestrator: Quality Gate REJECTED '{name}' (Score: {final_score:.1f}, Reason: {reason})")
        raise ValidationError(
            f"Quality Gate rejected asset: {reason}", details={"score": final_score}
        )

    logger.info(
        f"Orchestrator: Quality Gate PASSED '{name}' (Score: {final_score:.1f})"
    )

    # Calculate code hash for deduplication
    code_hash = calculate_code_hash(code)

    # Check for unchanged asset
    existing = await sqlite_storage.get_function_by_name(name)
    if existing and existing.get("code_hash") == code_hash:
        logger.info(f"Orchestrator: Skipping save for '{name}' (unchanged hash)")
        return True

    # 3. LLM Metadata Enrichment / Embedding prep
    intel = LogicIntelligence(GEMINI_API_KEY)

    # 6. Generate Embedding for RAG
    search_doc = intel.construct_search_document(
        name, description, tags, code
    )
    embedding = await intel.generate_embedding(search_doc)

    # Automatic Dependency Extraction
    if not dependencies:
        extracted = extract_dependencies(code, language=language)
        if extracted:
            logger.info(f"Orchestrator: Auto-extracted dependencies ({language}): {extracted}")
            dependencies = extracted

    # 7. Final data preparation and save
    data = {
        "name": str(name),
        "code": str(code),
        "description": str(description),
        "language": str(language),
        "tags": tags,
        "reliability_score": float(final_score) / 100.0,
        "embedding": embedding,
        "code_hash": str(code_hash),
        "dependencies": dependencies,
        "test_code": test_code,
    }

    save_result = await sqlite_storage.upsert_function(data)
    return save_result




async def do_get_async(name: str) -> Optional[Dict[str, Any]]:
    """Asynchronous implementation for getting a function."""
    return await sqlite_storage.get_function_by_name(name)


async def do_search_async(query: str, limit: int = 5):
    """Asynchronous implementation for searching functions with Query Expansion."""
    intel = LogicIntelligence(GEMINI_API_KEY)

    query_emb = await intel.generate_embedding(query)

    logger.info(f"Orchestrator: Performing hybrid search for '{query}'")
    return await sqlite_storage.find_similar_functions(query_emb, query_text=query, limit=limit)


# --- End of Orchestrator ---
