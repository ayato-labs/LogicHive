from fastmcp import FastMCP
import orchestrator
from core.exceptions import LogicHiveError, ValidationError

# Initialize FastMCP server
mcp = FastMCP("LogicHive")


@mcp.tool()
async def search_functions(query: str, limit: int = 5) -> str:
    """
    Search for high-quality, reusable code functions within the LogicHive vault using Hybrid Search.
    This is the primary tool for knowledge retrieval. Use it when you need to find existing 
    implementations or avoid reinventing code.

    SEARCH MODES:
    1. Semantic Search: Natural language queries (e.g., "authentication helper").
    2. Exact Match: Function names (e.g., "normalize_llm_args").
    3. Tag Filter: Use "#tagname" (e.g., "#security").

    INTERPRETING RESULTS:
    - Results include a 'reliability_score' (0-100). Scores >= 80 are recommended for production.
    - 'similarity' (0.0-1.0) indicates how well it matches your semantic query.

    Args:
        query: Search term, exact name, or #tag.
        limit: Max results. Default 5. Use higher limits for broad semantic queries.
    """
    results = await orchestrator.do_search_async(query, limit)
    if not results:
        return "No matching functions found."

    formatted = f"### Search Results for: {query}\n\n"
    for r in results:
        lang_str = f" [{r.get('language', 'unknown')}]"
        # Use similarity if available (from semantic search)
        reliability = r.get("reliability_score", "N/A")
        if "similarity" in r:
            reliability = f"{reliability} | Similarity: {r['similarity']:.2f}"

        formatted += f"- **{r['name']}**{lang_str} (Reliability: {reliability})\n  {r.get('description', 'No description')}\n\n"
    return formatted


@mcp.tool()
async def get_function(name: str) -> str:
    """
    Fetch the full source code and metadata of a specific function by its exact name.
    Use this AFTER search_functions if you've identified a promising candidate name.

    Args:
        name: The precise, case-sensitive name of the function (e.g., "save_log").
    """
    f_data = await orchestrator.do_get_async(name)
    if not f_data:
        return f"Function '{name}' not found"

    lang = f_data.get("language", "python")
    code = f_data["code"]
    return f"```{lang}\n{code}\n```"


@mcp.tool()
async def save_function(
    name: str,
    code: str,
    description: str = "",
    language: str = "python",
    tags: list = [],
    dependencies: list[str] = [],
    test_code: str = "",
) -> str:
    """
    Saves a verified, high-quality code asset to the LogicHive vault for future reuse.
    The asset undergoes an automated Quality Gate check (AI grading & Static analysis).

    BEST PRACTICES FOR AI AGENTS:
    1. Metadata is Critical: Provide a detailed 'description' (min 10 chars) explaining 
       the "why" and "how".
    2. Taxonomize: Use relevant 'tags' to ensure future discoverability.
    3. Self-Test: Always include 'test_code' if possible to increase reliability score.

    REJECTION CRITERIA:
    - Syntax errors (instant Score 0).
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
    """
    try:
        success = await orchestrator.do_save_async(
            name=name,
            code=code,
            description=description,
            tags=tags,
            language=language,
            dependencies=dependencies,
            test_code=test_code,
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


if __name__ == "__main__":
    mcp.run()
