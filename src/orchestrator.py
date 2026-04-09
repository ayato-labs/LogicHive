import logging
import ast
import re
import asyncio
from typing import Any, Optional

from storage.sqlite_api import sqlite_storage
from core.consolidation import LogicIntelligence
from core.config import GEMINI_API_KEY, QUALITY_GATE_THRESHOLD, ENABLE_AUTO_BACKUP
from core.exceptions import ValidationError
from core.hash_utils import calculate_code_hash
from core.evaluation.manager import EvaluationManager
from storage.vector_store import vector_manager

logger = logging.getLogger(__name__)

# --- Helpers ---


def extract_dependencies(code: str, language: str = "python") -> list[str]:
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
            logger.warning(
                f"Orchestrator: AST extraction failed, falling back to regex: {e}"
            )
            # Fallback to regex for Python if AST fails
            matches = re.findall(
                r"^(?:import|from)\s+([a-zA-Z0-9_]+)", code, re.MULTILINE
            )
            dependencies.update(matches)

    elif lang in ["typescript", "javascript", "tsx", "jsx"]:
        # Regex for ES6 imports: from 'pkg' or from "pkg" (robust whitespace)
        es6_matches = re.findall(r"from\s+['\"]([^'\"./][^'\"]*)['\"]", code)
        # Regex for CommonJS: require('pkg')
        cjs_matches = re.findall(
            r"require\s*\(\s*['\"]([^'\"./][^'\"]*)['\"]\s*\)", code
        )
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
    std_lib = {
        "os",
        "sys",
        "json",
        "math",
        "datetime",
        "typing",
        "asyncio",
        "logging",
        "ast",
        "pathlib",
        "abc",
        "fs",
        "path",
        "http",
        "https",
        "crypto",
    }
    return sorted(list(dependencies - std_lib))


async def do_delete_async(name: str, project: str = "default") -> bool:
    """
    Orchestrates deletion from DB, Vector index, and archiving in Backup.
    """
    try:
        # 1. Local DB deletion
        db_success = await sqlite_storage.delete_function(name, project=project)
        if not db_success:
            return False

        # 2. Vector index deletion (background)
        asyncio.create_task(vector_manager.remove_vector(name, project=project))

        # 3. Backup Archiving (background)
        # ユーザーがバックアップを有効にしており、かつトークンが存在する場合のみ実行
        if ENABLE_AUTO_BACKUP and GITHUB_TOKEN:
            from storage.auto_backup import backup_manager

            asyncio.create_task(backup_manager.archive_asset(name, project=project))

        return True
    except Exception as e:
        logger.error(f"Orchestrator: Deletion failed for '{name}': {e}")
        return False


# --- MCP / REST API Implementation Wrappers ---


async def do_save_async(
    name: str,
    code: str,
    description: str = "",
    tags: list[str] = [],
    language: str = "python",
    dependencies: list[str] = [],
    test_code: str = "",
    project: str = "default",
):
    """
    Includes LLM Quality Gate 2.0 (LLM + Static Analysis), RAG optimization, and versioning.
    """
    # --- 1. Evaluate Logic Asset (New Plugin System) ---
    eval_manager = EvaluationManager()
    eval_res = await eval_manager.evaluate_all(
        code, language, description=description, tags=tags
    )

    final_score = eval_res["score"]
    reason = eval_res["reason"]

    if final_score < QUALITY_GATE_THRESHOLD:
        logger.warning(
            f"Orchestrator: Quality Gate REJECTED '{name}' (Score: {final_score:.1f}, Reason: {reason})"
        )
        raise ValidationError(
            f"Quality Gate rejected asset: {reason}", details={"score": final_score}
        )

    logger.info(
        f"Orchestrator: Quality Gate PASSED '{name}' (Score: {final_score:.1f})"
    )

    # Calculate code hash for deduplication
    code_hash = calculate_code_hash(code)

    # Check for unchanged asset
    existing = await sqlite_storage.get_function_by_name(name, project=project)
    if existing and existing.get("code_hash") == code_hash:
        logger.info(
            f"Orchestrator: Skipping save for '{name}' in project '{project}' (unchanged hash)"
        )
        return True

    # 3. LLM Metadata Enrichment / Embedding prep
    intel = LogicIntelligence(GEMINI_API_KEY)

    # Enrich description and tags if needed
    # Note: intel.optimize_metadata is currently not implemented in LogicIntelligence.
    # We will keep existing description/tags for now.
    # if not description or not tags:
    #     enriched = await intel.optimize_metadata(name, code, description, tags)
    #     description = enriched.get("description", description)
    #     tags = enriched.get("tags", tags)

    # 6. Generate Embedding for RAG
    search_doc = intel.construct_search_document(name, description, tags, code)
    embedding = await intel.generate_embedding(search_doc)

    # Automatic Dependency Extraction
    if not dependencies:
        extracted = extract_dependencies(code, language=language)
        if extracted:
            logger.info(
                f"Orchestrator: Auto-extracted dependencies ({language}): {extracted}"
            )
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
        "project": project,
    }

    save_result = await sqlite_storage.upsert_function(data)

    # 8. Trigger Background Auto-Backup (Fire-and-forget)
    # ユーザーがバックアップを有効にしており、かつトークンが存在する場合のみ実行
    if save_result and ENABLE_AUTO_BACKUP and GITHUB_TOKEN:
        from storage.auto_backup import backup_manager

        asyncio.create_task(backup_manager.process_backup(data))

    return save_result


async def do_get_async(name: str, project: str = "default") -> Optional[dict[str, Any]]:
    """Asynchronous implementation for getting a function."""
    return await sqlite_storage.get_function_by_name(name, project=project)


async def do_search_async(
    query: str, limit: int = 5, language: Optional[str] = None, project: Optional[str] = None
):
    """Asynchronous implementation for searching functions with Query Expansion and Re-ranking."""
    intel = LogicIntelligence(GEMINI_API_KEY)

    expanded_query = await intel.expand_query(query)
    query_emb = await intel.generate_embedding(expanded_query)

    logger.info(
        f"Orchestrator: Performing hybrid search for '{query}' (Lang: {language}, Project: {project})"
    )

    # 1. Fetch more candidates than requested for re-ranking (limit * 3)
    # Note: passing project to vector_manager for future-proofing internal filtering
    initial_results = await sqlite_storage.find_similar_functions(
        query_emb, query_text=query, limit=limit * 3, language=language, project=project
    )

    # 2. Re-rank using LLM
    logger.info(f"Orchestrator: Re-ranking {len(initial_results)} candidates...")
    reranked_results = await intel.rerank_results(query, initial_results, limit=limit)

    # 3. Fallback: Auto-Draft Generation (Experimental)
    # Trigger if results are empty or top match is weak (similarity < 0.45)
    top_score = reranked_results[0].get("similarity", 0) if reranked_results else 0
    if top_score < 0.45:
        logger.info(
            f"Orchestrator: Weak results (Score: {top_score:.2f}). Triggering Auto-Draft Generator..."
        )
        from core.plugins.draft_generator import DraftGenerator

        generator = DraftGenerator(intel)
        draft = await generator.generate_draft(
            query, initial_results, language=language or "python"
        )
        if draft:
            # Prepend draft to results (or return only draft if requested)
            return [draft] + reranked_results

    return reranked_results


# --- End of Orchestrator ---
