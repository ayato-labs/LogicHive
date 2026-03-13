import logging
import ast
import asyncio
from typing import Dict, List, Any, Optional
from storage.sqlite_api import sqlite_storage
from core.consolidation import LogicIntelligence
from core.config import GEMINI_API_KEY, QUALITY_GATE_THRESHOLD, DESCRIPTION_MIN_LENGTH
from core.exceptions import ValidationError, AIProviderError
from core.hash_utils import calculate_code_hash
from core.notifier import send_notification
from radon.complexity import cc_visit

logger = logging.getLogger(__name__)

# --- Helpers ---

def extract_python_dependencies(code: str) -> List[str]:
    """
    Deterministically extracts top-level imports from Python code using AST.
    Filters out obvious project-internal relative imports.
    """
    dependencies = set()
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get base package name (e.g., 'os' from 'os.path')
                    base = alias.name.split(".")[0]
                    dependencies.add(base)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    base = node.module.split(".")[0]
                    dependencies.add(base)
    except SyntaxError as e:
        logger.error(f"Orchestrator: Syntax error during dependency extraction: {e}")
        # For personal use, we assume code is generally correct, but syntax error is a hard failure.
        raise ValidationError(f"Python Syntax Error in provided code: {e}")
    except Exception as e:
        logger.error(f"Orchestrator: AST dependency extraction failed unexpectedly: {e}")
        # In personal mode, we might want to proceed but log the failure clearly.
        # However, per improvement plan, we should handle this more strictly.
        raise LogicHiveError(f"Critical failure during dependency extraction: {e}")
    
    # Filter out common standard libraries to keep the 'recipe' focused on external deps
    std_lib = {"os", "sys", "json", "math", "datetime", "typing", "asyncio", "logging", "ast", "pathlib", "uuid", "abc"}
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
    # 1. Static Analysis (Structural Integrity & Complexity)
    lang = language.lower()
    static_score = 100
    static_reason = ""

    if lang == "python":
        try:
            ast_tree = ast.parse(code)
            # 1a. Cyclomatic Complexity
            blocks = cc_visit(code)
            if blocks:
                avg_cc = sum(b.complexity for b in blocks) / len(blocks)
                if avg_cc > 10:
                    static_score -= min(30, (avg_cc - 10) * 5)
                    static_reason += f"High complexity (CC: {avg_cc:.1f}). "

            # 1b. Dependency Check (Pureness)
            for node in ast.walk(ast_tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if (
                            "." in alias.name
                        ):  # Simple heuristic for project-specific deep imports
                            static_score -= 5
                elif isinstance(node, ast.ImportFrom):
                    if node.level > 0:  # Relative imports
                        static_score -= 10
                        static_reason += "Avoid relative imports for atomic logic. "

        except SyntaxError as e:
            raise ValidationError(f"Python Syntax Error: {e}")

    # 2. Basic Structural Check (Unbalanced brackets check for all languages)
    # This prevents obviously broken code from even reaching the AI Gate.
    unbalanced = []
    pairs = {'(': ')', '[': ']', '{': '}'}
    stack = []
    for char in code:
        if char in pairs:
            stack.append(char)
        elif char in pairs.values():
            if not stack or pairs[stack.pop()] != char:
                unbalanced.append(char)
                break
    if stack or unbalanced:
        raise ValidationError(f"Quality Gate: Structural error detected (unbalanced brackets).")

    # 3. Calculate code hash for deduplication
    code_hash = calculate_code_hash(code)

    # 3. Check for unchanged asset
    existing = await sqlite_storage.get_function_by_name(name)
    if existing and existing.get("code_hash") == code_hash:
        logger.info(f"Orchestrator: Skipping save for '{name}' (unchanged hash)")
        return True
    # 4. LLM Quality Gate (Gatekeeper)
    intel = LogicIntelligence(GEMINI_API_KEY)

    # Strict Metadata Validation (Plan A / MVP)
    if not description or len(description.strip()) < DESCRIPTION_MIN_LENGTH:
        raise ValidationError(f"Quality Gate: 'description' is mandatory and must be at least {DESCRIPTION_MIN_LENGTH} characters long.")
    if not tags or not isinstance(tags, list) or len(tags) == 0:
        raise ValidationError("Quality Gate: 'tags' is mandatory and must contain at least one tag.")

    logger.info(f"Orchestrator: Evaluating quality for '{name}'...")
    try:
        quality = await intel.evaluate_quality(code)
        llm_score = quality.get("score", 0)
        llm_reason = quality.get("reason", "No reason provided.")
    except AIProviderError:
        # Fallback if AI fails: rely on static analysis for Python, else fail
        logger.warning(
            "Orchestrator: AI Provider failed. Falling back to static score."
        )
        if lang == "python":
            llm_score = static_score
            llm_reason = "AI Evaluation unavailable (Fallback to Python static analysis)."
        else:
            raise ValidationError("Quality Gate: AI Provider unavailable and no static analyzer for this language.")

    # Quality Gate 2.0: Weighted Score
    # Python: 50/50 split | Others: 100% LLM
    if lang == "python":
        final_score = (llm_score * 0.5) + (static_score * 0.5)
    else:
        final_score = float(llm_score)

    if final_score < QUALITY_GATE_THRESHOLD:
        reason = f"Weighted Score: {final_score:.1f}. LLM: {llm_reason}"
        if lang == "python" and static_reason:
             reason += f" | Static: {static_reason}"
        logger.warning(f"Orchestrator: Quality Gate REJECTED '{name}' ({reason})")
        raise ValidationError(
            f"Quality Gate rejected asset: {reason}", details={"score": final_score}
        )

    logger.info(
        f"Orchestrator: Quality Gate PASSED '{name}' (Score: {final_score:.1f})"
    )

    # 6. Generate Embedding for RAG
    search_doc = intel.construct_search_document(
        name, description, tags, code
    )
    embedding = await intel.generate_embedding(search_doc)

    # Automatic Dependency Extraction (Python)
    if lang == "python" and not dependencies:
        extracted = extract_python_dependencies(code)
        if extracted:
            logger.info(f"Orchestrator: Auto-extracted dependencies: {extracted}")
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

    if query_emb:
        logger.info("Orchestrator: Performing semantic search")
        return await sqlite_storage.find_similar_functions(query_emb, limit=limit)

    logger.info(f"Orchestrator: Falling back to static search for '{query}'")
    # Note: Traditional static search can use the original query or expanded.
    # For now, keeping it simple as vector search is the main path.
    return []  # Simplified for MVP


# --- End of Orchestrator ---
