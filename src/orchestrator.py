import ast
import asyncio
import logging
import re
import uuid
from typing import Any

from core.config import (
    DESCRIPTION_MIN_LENGTH,
    ENABLE_AUTO_BACKUP,
    GEMINI_API_KEY,
    GITHUB_TOKEN,
    QUALITY_GATE_THRESHOLD,
)
from core.consolidation import LogicIntelligence
from core.evaluation.manager import EvaluationManager
from core.exceptions import ValidationError
from core.hash_utils import calculate_code_hash
from storage.sqlite_api import sqlite_storage
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


async def _run_async_verification_pipeline(
    name: str,
    project: str,
    code: str,
    description: str,
    tags: list[str],
    language: str,
    dependencies: list[str],
    test_code: str,
    mock_imports: list[str],
    timeout: int | None,
):
    """Background task to run Quality Gate, metadata enrichment and embedding generation."""
    try:
        # 1. Quality Gate
        eval_manager = EvaluationManager()
        eval_res = await eval_manager.evaluate_all(
            code,
            language,
            description=description,
            tags=tags,
            test_code=test_code,
            dependencies=dependencies,
            mock_imports=mock_imports,
            timeout=timeout,
        )

        final_score = float(eval_res["score"])
        is_system_error = eval_res.get("is_system_error", False)
        status = "verified" if final_score >= QUALITY_GATE_THRESHOLD else "failed"
        if is_system_error:
            status = "error"

        # 2. Metadata Enrichment (if needed)
        intel = LogicIntelligence(GEMINI_API_KEY)
        if not description or len(description) < DESCRIPTION_MIN_LENGTH or not tags:
            enriched = await intel.optimize_metadata(code)
            description = enriched.get("description", description)
            tags = list(set(tags + enriched.get("tags", [])))

        # 3. Embedding
        search_doc = intel.construct_search_document(name, description, tags, code)
        embedding = await intel.generate_embedding(search_doc)

        # 4. Update DB with final results
        await sqlite_storage.update_verification_status(
            name,
            project,
            status=status,
            report=eval_res,
            reliability_score=final_score / 100.0,
        )

        # Update metadata if enriched
        # Note: We might need a more general update method if we want to save enriched description/tags
        # For now, let's just update the status/score/report.

        # 5. Sync to Vector Store (if verified)
        if status == "verified":
            await vector_manager.upsert_vector(
                name,
                embedding,
                metadata={"project": project, "language": language},
                project=project,
            )

        logger.info(f"Orchestrator: Async verification FINISHED for '{name}' with status: {status}")

    except Exception as e:
        logger.error(
            f"[TRACE] Orchestrator: Async verification FAILED for '{name}': {e}", exc_info=True
        )
        await sqlite_storage.update_verification_status(
            name, project, status="error", report={"error": str(e)}
        )


async def do_save_async(
    name: str,
    code: str,
    description: str = "",
    tags: list[str] = [],
    language: str = "python",
    dependencies: list[str] = [],
    test_code: str = "",
    project: str = "default",
    mock_imports: list[str] = [],
    timeout: int | None = None,
):
    """
    Asynchronously saves a function.
    1. Checks for hash-based deduplication.
    2. Saves with 'pending' status.
    3. Kicks off background verification and returns immediately.
    """
    # 1. Deduplication Check
    code_hash = calculate_code_hash(code)
    existing = await sqlite_storage.get_function_by_hash(code_hash, project)
    if existing:
        logger.info(
            f"Orchestrator: Deduplication hit for '{name}' (Existing: '{existing['name']}')"
        )
        raise ValidationError(
            f"Asset with identical logic is already registered as '{existing['name']}' in project '{project}'."
        )

    # 2. Immediate Save (Pending)
    from core.system_info import SystemFingerprint

    # Automatic Dependency Extraction (Immediate)
    if not dependencies:
        extracted = extract_dependencies(code, language=language)
        dependencies = extracted if extracted else []

    data = {
        "id": str(uuid.uuid4()),
        "name": str(name),
        "code": str(code),
        "description": str(description),
        "language": str(language),
        "tags": tags,
        "reliability_score": 0.0,
        "embedding": None,  # Will be updated by bg task
        "code_hash": str(code_hash),
        "dependencies": dependencies,
        "test_code": test_code,
        "project": project,
        "env_fingerprint": SystemFingerprint.get_current(),
        "verification_status": "pending",
        "verification_report": None,
    }

    # Initial save to DB
    logger.info(
        f"[TRACE] Orchestrator: Saving initial 'pending' record for '{name}' [project={project}]"
    )
    await sqlite_storage.upsert_function(data)
    save_result = await sqlite_storage.upsert_function(data)
    if not save_result:
        raise Exception("Failed to perform initial save to LogicHive vault.")

    # 3. Kick off Background Verification
    asyncio.create_task(
        _run_async_verification_pipeline(
            name,
            project,
            code,
            description,
            tags,
            language,
            dependencies,
            test_code,
            mock_imports,
            timeout,
        )
    )

    logger.info(f"Orchestrator: Save accepted for '{name}'. Verification is running in background.")
    return True


async def do_get_async(name: str, project: str = "default") -> dict[str, Any] | None:
    """Asynchronous implementation for getting a function."""
    return await sqlite_storage.get_function_by_name(name, project=project)


async def do_search_async(
    query: str, limit: int = 5, language: str | None = None, project: str = "default"
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
        query_emb,
        query_text=query,
        limit=limit * 3,
        language=language,
        project=project,
        include_code=False,
    )

    # 2. Re-rank using LLM
    logger.info(f"Orchestrator: Re-ranking {len(initial_results)} candidates...")
    reranked_results = await intel.rerank_results(query, initial_results, limit=limit)

    # 3. Fallback: Auto-Draft Generation (Experimental)
    # Trigger ONLY if top match is weak AND it looks like a generation request
    top_score = reranked_results[0].get("similarity", 0) if reranked_results else 0
    generation_keywords = ["create", "generate", "make", "implement", "write", "how to"]
    is_generation_request = any(k in query.lower() for k in generation_keywords)

    if top_score < 0.45 and is_generation_request:
        logger.info(
            f"Orchestrator: Weak results (Score: {top_score:.2f}) and Generation intent detected. Triggering..."
        )
        from core.plugins.draft_generator import DraftGenerator

        generator = DraftGenerator(intel)
        draft = await generator.generate_draft(
            query, initial_results, language=language or "python"
        )
        if draft:
            # Ensure draft has consistency metadata
            draft["similarity"] = 0.4
            draft["project"] = project or "default"
            # Prepend draft to results
            return [draft] + reranked_results

    return reranked_results


async def do_list_async(
    project: str | None = None, tags: list[str] | None = None, limit: int = 50
) -> list[dict[str, Any]]:
    """Lists functions with optional filtering."""
    return await sqlite_storage.get_functions(project=project, tags=tags, limit=limit)


async def check_integrity() -> dict[str, Any]:
    """
    Checks the health of various components (Database, Vector Index, Pool).
    """
    from core.execution.pool import pool_manager
    from storage.sqlite_api import sqlite_storage
    from storage.vector_store import vector_manager

    details = {}

    # 1. DB Check
    db_health = await sqlite_storage.check_health()
    details["database"] = db_health

    # 2. Vector Store Check
    vector_health = await vector_manager.check_health()
    details["vector_store"] = vector_health

    # 3. Pool Check
    pool_health = await pool_manager.check_health()
    details["pool_manager"] = pool_health

    status = "Healthy"
    if any(h.get("status") == "Error" for h in details.values()):
        status = "Error"
    elif any(h.get("status") == "Warning" for h in details.values()):
        status = "Warning"

    return {"status": status, "details": details}


async def _run_async_verification_pipeline(
    name: str,
    project: str,
    code: str,
    description: str,
    tags: list[str],
    language: str,
    dependencies: list[str],
    test_code: str,
    mock_imports: dict[str, Any] | None = None,
    timeout: int = 60,
):
    """
    Background task to run the Quality Gate pipeline.
    """
    try:
        logger.info(f"Orchestrator: Starting background verification for {name} [{project}]")

        # 1. Initialize evaluation
        from core.evaluation import EvaluationManager

        eval_mgr = EvaluationManager()

        # 2. Run Quality Gate (this is the heavy part)
        report = await eval_mgr.evaluate_all(
            code, language, name=name, project=project, description=description, tags=tags
        )

        status = "verified" if report.get("success") else "failed"
        score = report.get("score", 0.0)

        # 3. Update DB
        await sqlite_storage.update_verification_status(
            name=name,
            project=project,
            status=status,
            report=report,
            reliability_score=score,
        )

        logger.info(
            f"Orchestrator: Background verification for {name} completed with status: {status}"
        )

    except Exception as e:
        logger.error(f"Orchestrator: Background verification failed for {name}: {e}", exc_info=True)
        await sqlite_storage.update_verification_status(
            name=name, project=project, status="error", report={"error": str(e)}
        )


async def do_get_verification_status(name: str, project: str = "default") -> dict[str, Any]:
    """Retrieves the verification status and report for a function."""
    logger.info(
        f"[TRACE] Orchestrator: Fetching verification status for '{name}' [project={project}]"
    )
    func = await sqlite_storage.get_function_by_name(name, project)
    if not func:
        logger.warning(f"[TRACE] Orchestrator: Asset '{name}' not found during status check.")
        return {
            "status": "not_found",
            "message": f"Asset '{name}' not found in project '{project}'.",
        }

    return {
        "name": name,
        "project": project,
        "status": func.get("verification_status", "unknown"),
        "report": func.get("verification_report"),
    }


async def do_delete_async(name: str, project: str = "default") -> bool:
    """
    Asynchronously deletes a function and its vector matches.
    """
    logger.info(f"[TRACE] Orchestrator: Initiating deletion of '{name}' [project={project}]")
    try:
        # 1. Delete from SQLite (this should also handle history if needed)
        success = await sqlite_storage.delete_function(name, project)

        # 2. Delete from Vector Store
        from storage.vector_store import vector_manager

        await vector_manager.remove_vector(name, project)

        logger.info(f"[TRACE] Orchestrator: Deletion of '{name}' successful: {success}")
        return success
    except Exception as e:
        logger.error(f"[TRACE] Orchestrator: Failed to delete '{name}': {e}", exc_info=True)
        # We re-raise to avoid swallowing the error as per user request
        raise


# --- End of Orchestrator ---
