from contextlib import asynccontextmanager

from fastmcp import FastMCP

import orchestrator
from core.exceptions import LogicHiveError, ValidationError
from orchestrator import do_delete_async, do_save_async


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Initializes and cleans up the background worker for environment pooling."""
    from core.execution.pool import PoolManager

    manager = PoolManager.get_instance()
    await manager.initialize()
    try:
        yield
    finally:
        await manager.shutdown()


# Initialize FastMCP server with lifespan management
mcp = FastMCP("LogicHive", lifespan=lifespan)


@mcp.tool()
async def search_functions(
    query: str,
    limit: int = 5,
    language: str = None,
    project: str = None,
    wait_for_previous: bool = False,
) -> str:
    """
    Search for high-quality, reusable code functions within the LogicHive vault using Hybrid Search.
    This is the primary tool for knowledge retrieval. Use it when you need to find existing
    implementations or avoid reinventing code.

    NOTE: This tool returns technical SUMMARIES (metadata) only. To see the full source code
    of a function, use the 'get_function' tool with the name and project found in these results.

    SEARCH MODES:
    1. Semantic Search: Natural language queries (e.g., "authentication helper").
    2. Exact Match: Function names (e.g., "normalize_llm_args").
    3. Tag Filter: Use "#tagname" (e.g., "#security").
    4. Language Filter: Specify the language (e.g., "python", "javascript") to restrict results.
    5. Project Filter: Restrict search to a specific project (e.g., "ayato-studio").

    Args:
        query: Search term, exact name, or #tag.
        limit: Max results. Default 5.
        language: Optional language to filter by (e.g., 'python', 'javascript').
        project: Optional project name to narrow the search.
        wait_for_previous: Set to true to wait for all previously requested tools in this turn to complete before starting. Set to false (or omit) to run in parallel. Use true when this tool depends on the output of previous tools.
    """
    try:
        results = await orchestrator.do_search_async(query, limit, language, project=project)
        if not results:
            return "No matching functions found."

        md = "### Search Results\n\n"
        for res in results:
            is_draft = res.get("is_draft", False)
            name = res["name"]
            if is_draft:
                name = f"⚠️ [AI-DRAFT] {name}"
            sim = res.get("similarity", 0)
            rel = res.get("reliability_score", 0) * 100
            desc = res.get("description", "No description")
            tags = ", ".join(res.get("tags", []))

            # Check for Environment Drift
            drift_warning = ""
            stored_env = res.get("env_fingerprint")
            if stored_env:
                from core.system_info import SystemFingerprint

                if SystemFingerprint.compare(stored_env, SystemFingerprint.get_current()):
                    drift_warning = " ⚠️ [DRIFT]"

            md += f"- **{name}{drift_warning}** (Match: {sim:.2f}, Reliability: {rel:.1f}%)\n"
            if is_draft:
                md += "  - *NOTE: This is a generated draft. Refine and Save to verify.*\n"
            md += f"  - *{desc}*\n"
            md += f"  - Tags: {tags}\n"
        return md
    except Exception as e:
        logger.error(f"MCP Server: Error in search_functions: {e}")
        return f"LogicHive Error: Failed to perform search. Detail: {str(e)}"


@mcp.tool()
async def get_function(name: str, project: str = "default", wait_for_previous: bool = False) -> str:
    """
    Fetch the full source code and metadata of a specific function by its exact name and project.
    Use this AFTER search_functions if you've identified a promising candidate name.

    Args:
        name: The precise, case-sensitive name of the function (e.g., "save_log").
        project: The project namespace (defaults to 'default').
        wait_for_previous: Set to true to wait for all previously requested tools in this turn to complete before starting. Set to false (or omit) to run in parallel. Use true when this tool depends on the output of previous tools.
    """
    try:
        f_data = await orchestrator.do_get_async(name, project=project)
        if not f_data:
            return f"Function '{name}' not found"

        lang = f_data.get("language", "python")
        code = f_data["code"]
        desc = f_data.get("description", "No description")
        tags = ", ".join(f_data.get("tags", []))
        deps = ", ".join(f_data.get("dependencies", []))

        # Environment Drift Check
        drift_header = ""
        stored_env = f_data.get("env_fingerprint")
        if stored_env:
            from core.system_info import SystemFingerprint

            warning = SystemFingerprint.generate_warning_msg(stored_env)
            if warning:
                drift_header = f"> [!WARNING]\n> {warning.replace(chr(10), chr(10) + '> ')}\n\n"

        return f"**Function: {name}**\n\n{drift_header}{desc}\n\n**Tags:** {tags}\n**Dependencies:** {deps}\n\n```{lang}\n{code}\n```"
    except Exception as e:
        logger.error(f"MCP Server: Error in get_function: {e}")
        return f"LogicHive Error: Failed to retrieve function. Detail: {str(e)}"


@mcp.tool()
async def save_function(
    name: str,
    code: str,
    description: str = "",
    language: str = "python",
    tags: list = [],
    dependencies: list[str] = [],
    test_code: str = "",
    project: str = "default",
    mock_imports: list[str] = [],
    timeout: int = 60,
    wait_for_previous: bool = False,
) -> str:
    """
    Saves a verified, high-quality code asset to the LogicHive vault for future reuse.
    The asset undergoes an automated Quality Gate check (AI grading & Static analysis).

    BEST PRACTICES FOR AI AGENTS:
    1. Strategy Priority (Purity > Utility):
       - PRIMARY: Extract pure logic from I/O code. Save only the "Logic Atom" (data processing, validation).
       - SECONDARY: If you must save I/O-heavy code (e.g. retry patterns), use 'mock_imports' to bypass network/file calls.
    2. Project Context: Always specify a 'project' name to avoid cluttering the global vault.
    3. Metadata is Critical: Provide a detailed 'description' (min 10 chars).
    4. Self-Test: Always include 'test_code'. Use mocks for I/O functions to ensure deterministic verification.
    5. Smart Mocking: Add heavy libraries (torch) or I/O libraries (aiohttp, httpx) to 'mock_imports'.
    REJECTION CRITERIA:
    - Syntax errors (instant Score 0 / Critical failure).
    - Vague descriptions or missing tags.
    - Poor AI-graded quality (logic flaws, security risks).
    - **Quality Theater**: Literal assertions (e.g., `assert True`) or tests that don't call the code.

    SUPPORTED LANGUAGES:
    - **Python** (High Fidelity): Full AST-based verification, assertion analysis, and runtime pool execution.
    - **JavaScript / TypeScript** (Standard): Structural assertion detection and pattern matching.
    - **C++ / Java** (Foundational): Keyword-based asset integrity checks.

    Args:
        name: Unique identifier for the function (e.g., "validate_email_utils").
        code: The source code implementation.
        description: Technical specification. Explain edge cases and logic.
        language: Programming language (lowercase, e.g., 'python', 'javascript').
        tags: Categorization labels for discovery.
        dependencies: External libraries required (e.g., ['pandas', 'pydantic']).
        test_code: Pytest/Unit test code for automated validation.
        project: Project name for logically grouping code (defaults to 'default').
        mock_imports: List of modules to mock during registration to avoid timeouts (e.g. ['torch']).
        timeout: Maximum execution time in seconds for the Quality Gate (Default 60s, Hard Limit 120s).
        wait_for_previous: Set to true to wait for all previously requested tools in this turn to complete before starting. Set to false (or omit) to run in parallel. Use true when this tool depends on the output of previous tools.
    """
    try:
        success = await do_save_async(
            name=name,
            code=code,
            description=description,
            tags=tags,
            language=language,
            dependencies=dependencies,
            test_code=test_code,
            project=project,
            mock_imports=mock_imports,
            timeout=timeout,
        )
        return "Saved successfully to LogicHive" if success else "Failed (Unknown Error)"
    except ValidationError as e:
        # Extract rich details for better transparency (User feedback Tip #1)
        details = e.details or {}
        score = details.get("score", 0)
        reason = details.get("reason", str(e))
        eval_details = details.get("eval_details", {})

        # Build a helpful report
        report = [f"Quality Gate REJECTED: {reason}", f"Final Score: {score:.1f}/100"]

        if eval_details:
            report.append("\nBreakdown:")
            for tool_name, res in eval_details.items():
                tool_score = res.get("score", 0)
                tool_reason = res.get("reason", "N/A")
                report.append(f"- {tool_name}: {tool_score:.1f} ({tool_reason})")

                # Show traceback or stderr if available (Crucial for debugging)
                inner_details = res.get("details", {}) or {}
                if inner_details.get("traceback"):
                    report.append(f"  [TRACEBACK]\n{inner_details['traceback']}")
                elif inner_details.get("stderr"):
                    report.append(f"  [STDERR]\n{inner_details['stderr']}")

        return "\n".join(report)
    except LogicHiveError as e:
        return f"LogicHive Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"


@mcp.tool()
async def debug_db(wait_for_previous: bool = False) -> str:
    """
    Debug tool to inspect LogicHive database configuration and table structure.

    Args:
        wait_for_previous: Set to true to wait for all previously requested tools in this turn to complete before starting. Set to false (or omit) to run in parallel. Use true when this tool depends on the output of previous tools.
    """
    import os
    import sqlite3

    from core.config import SQLITE_DB_PATH

    status = [f"SQLITE_DB_PATH: {SQLITE_DB_PATH}"]
    status.append(f"Exists: {os.path.exists(SQLITE_DB_PATH)}")

    if os.path.exists(SQLITE_DB_PATH):
        try:
            status.append(f"Size: {os.path.getsize(SQLITE_DB_PATH)} bytes")
            conn = sqlite3.connect(SQLITE_DB_PATH)
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            status.append(f"Tables: {tables}")
            conn.close()
        except Exception as e:
            status.append(f"Error reading DB: {e}")

    return "\n".join(status)


@mcp.tool()
async def delete_function(
    name: str, project: str = "default", wait_for_previous: bool = False
) -> str:
    """
    Deletes a function from the LogicHive vault for a specific project.
    The function is archived in the backup repository for safety.

    Args:
        name: The case-sensitive name of the function to delete.
        project: The project namespace (defaults to 'default').
        wait_for_previous: Set to true to wait for all previously requested tools in this turn to complete before starting. Set to false (or omit) to run in parallel. Use true when this tool depends on the output of previous tools.
    """
    success = await do_delete_async(name, project=project)
    if success:
        return f"Successfully deleted and archived function '{name}' in project '{project}'."
    else:
        return f"Failed to delete function '{name}' in project '{project}'."


@mcp.tool()
async def list_functions(
    project: str = None, tags: list[str] = None, limit: int = 50, wait_for_previous: bool = False
) -> str:
    """
    List high-quality code functions with optional filtering by project and tags.
    Use this to browse available assets when search_functions is too specific.

    Args:
        project: Optional project name to filter by.
        tags: Optional list of tags to filter by.
        limit: Max results. Default 50.
        wait_for_previous: Set to true to wait for all previously requested tools in this turn to complete before starting. Set to false (or omit) to run in parallel. Use true when this tool depends on the output of previous tools.
    """
    try:
        results = await orchestrator.do_list_async(project=project, tags=tags, limit=limit)
        if not results:
            return "No functions found in the vault."

        md = "### Vault Assets\n\n"
        for res in results:
            name = res["name"]
            project_name = res.get("project", "default")
            desc = res.get("description", "No description")
            tags_str = ", ".join(res.get("tags", []))
            rel = res.get("reliability_score", 0) * 100

            md += f"- **{name}** (Project: {project_name}, Reliability: {rel:.1f}%)\n"
            md += f"  - *{desc}*\n"
            md += f"  - Tags: {tags_str}\n"

        return md
    except Exception as e:
        logger.error(f"MCP Server: Error in list_functions: {e}")
        return f"LogicHive Error: Failed to list functions. Detail: {str(e)}"


@mcp.tool()
async def check_integrity(wait_for_previous: bool = False) -> str:
    """
    Performs a comprehensive integrity check of the LogicHive system,
    including DB status, Vector store synchronization, and Environment pools.

    Args:
        wait_for_previous: Set to true to wait for all previously requested tools in this turn to complete before starting. Set to false (or omit) to run in parallel. Use true when this tool depends on the output of previous tools.
    """
    import os

    from core.config import FAISS_INDEX_PATH, SQLITE_DB_PATH
    from storage.sqlite_api import sqlite_storage
    from storage.vector_store import vector_manager

    status = ["## LogicHive Integrity Report\n"]

    try:
        # 1. DB Check
        db_exists = os.path.exists(SQLITE_DB_PATH)
        status.append(
            f"### 1. Database\n- Path: `{SQLITE_DB_PATH}`\n- Status: {'✅ Connected' if db_exists else '❌ Missing'}"
        )

        if db_exists:
            count = await sqlite_storage.get_function_count()
            status.append(f"- Record Count: {count}")

        # 2. Vector Store Check
        faiss_exists = os.path.exists(FAISS_INDEX_PATH)
        status.append(
            f"### 2. Vector Store (FAISS)\n- Path: `{FAISS_INDEX_PATH}`\n- Status: {'✅ Loaded' if faiss_exists else '⚠️ Missing (Will rebuild on search)'}"
        )

        if faiss_exists and db_exists:
            # Check for sync (simplified count check)
            idx_size = vector_manager.index.ntotal if vector_manager.index else 0
            if idx_size != count:
                status.append(
                    f"- ⚠️ **Desync Detected**: DB({count}) vs FAISS({idx_size}). Rebuild recommended."
                )
            else:
                status.append(f"- Sync Status: ✅ Optimal ({idx_size} vectors)")

        # 3. Environment Pool Check
        from core.execution.pool import PoolManager

        pool = PoolManager.get_instance()
        status.append(
            f"### 3. Environment Pool\n- Base Dir: `{pool.base_dir}`\n- GPU Available: {'✅' if pool.has_gpu else '❌'}"
        )

        return "\n".join(status)
    except Exception as e:
        return f"Integrity Check Failed: {str(e)}"


if __name__ == "__main__":
    mcp.run()
