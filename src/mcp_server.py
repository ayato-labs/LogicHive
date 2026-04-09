from fastmcp import FastMCP
import orchestrator
from orchestrator import do_save_async, do_delete_async
from core.exceptions import LogicHiveError, ValidationError

# Initialize FastMCP server
mcp = FastMCP("LogicHive")


@mcp.tool()
async def search_functions(
    query: str, limit: int = 5, language: str = None, project: str = None
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
    """
    results = await orchestrator.do_search_async(
        query, limit, language, project=project
    )
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

        md += f"- **{name}** (Match: {sim:.2f}, Reliability: {rel:.1f}%)\n"
        if is_draft:
            md += "  - *NOTE: This is a generated draft. Refine and Save to verify.*\n"
        md += f"  - *{desc}*\n"
        md += f"  - Tags: {tags}\n"
    return md


@mcp.tool()
async def get_function(name: str, project: str = "default") -> str:
    """
    Fetch the full source code and metadata of a specific function by its exact name and project.
    Use this AFTER search_functions if you've identified a promising candidate name.

    Args:
        name: The precise, case-sensitive name of the function (e.g., "save_log").
        project: The project namespace (defaults to 'default').
    """
    f_data = await orchestrator.do_get_async(name, project=project)
    if not f_data:
        return f"Function '{name}' not found"

    lang = f_data.get("language", "python")
    code = f_data["code"]
    desc = f_data.get("description", "No description")
    tags = ", ".join(f_data.get("tags", []))
    deps = ", ".join(f_data.get("dependencies", []))

    return f"**Function: {name}**\n\n{desc}\n\n**Tags:** {tags}\n**Dependencies:** {deps}\n\n```{lang}\n{code}\n```"


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
) -> str:
    """
    Saves a verified, high-quality code asset to the LogicHive vault for future reuse.
    The asset undergoes an automated Quality Gate check (AI grading & Static analysis).

    BEST PRACTICES FOR AI AGENTS:
    1. Project Context: Always specify a 'project' name to avoid cluttering the global vault.
    2. Metadata is Critical: Provide a detailed 'description' (min 10 chars).
    3. Taxonomize: Use relevant 'tags' to ensure future discoverability.
    4. Self-Test: Always include 'test_code' if possible to increase reliability score.

    REJECTION CRITERIA:
    - Syntax errors (instant Score 0 / Critical failure).
    - Vague descriptions or missing tags.
    - Poor AI-graded quality (logic flaws, security risks).

    Args:
        name: Unique identifier for the function (e.g., "validate_email_utils").
        code: The source code implementation.
        description: Technical specification. Explain edge cases and logic.
        language: Programming language (lowercase, e.g., 'python', 'typescript').
        tags: Categorization labels for discovery.
        dependencies: External libraries required (e.g., ['pandas', 'pydantic']).
        test_code: Pytest/Unit test code for automated validation.
        project: Project name for logically grouping code (defaults to 'default').
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
        )
        return (
            "Saved successfully to LogicHive" if success else "Failed (Unknown Error)"
        )
    except ValidationError as e:
        return f"Quality Gate REJECTED: {str(e)}"
    except LogicHiveError as e:
        return f"LogicHive Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"


@mcp.tool()
async def debug_db() -> str:
    """
    Debug tool to inspect LogicHive database configuration and table structure.
    """
    from core.config import SQLITE_DB_PATH
    import os
    import sqlite3

    status = [f"SQLITE_DB_PATH: {SQLITE_DB_PATH}"]
    status.append(f"Exists: {os.path.exists(SQLITE_DB_PATH)}")

    if os.path.exists(SQLITE_DB_PATH):
        try:
            status.append(f"Size: {os.path.getsize(SQLITE_DB_PATH)} bytes")
            conn = sqlite3.connect(SQLITE_DB_PATH)
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            status.append(f"Tables: {tables}")
            conn.close()
        except Exception as e:
            status.append(f"Error reading DB: {e}")

    return "\n".join(status)


@mcp.tool()
async def delete_function(name: str, project: str = "default") -> str:
    """
    Deletes a function from the LogicHive vault for a specific project.
    The function is archived in the backup repository for safety.

    Args:
        name: The case-sensitive name of the function to delete.
        project: The project namespace (defaults to 'default').
    """
    success = await do_delete_async(name, project=project)
    if success:
        return f"Successfully deleted and archived function '{name}' in project '{project}'."
    else:
        return f"Failed to delete function '{name}' in project '{project}'."


if __name__ == "__main__":
    mcp.run()
