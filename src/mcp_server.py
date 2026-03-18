from fastmcp import FastMCP
import orchestrator
from core.exceptions import LogicHiveError, ValidationError

# Initialize FastMCP server
mcp = FastMCP("LogicHive")


@mcp.tool()
async def search_functions(query: str, limit: int = 5) -> str:
    """
    Search for high-quality code functions in the LogicHive vault using Hybrid Search.
    Supports:
    - Natural language (Semantic Search)
    - Keywords (Partial name match)
    - Tags (Use "#tagname" to search by tag)
    
    Args:
        query: Search term or #tag.
        limit: Max number of results to return.
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
    Retrieve the exact source code of a function by its name.
    Args:
        name: Precise name of the function to fetch.
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
    Save a new high-quality function to the LogicHive vault.
    
    IMPORTANT: 'description' and 'tags' are MANDATORY for saving assets.
    The AI agent calling this tool MUST provide a detailed technical description (at least 10 chars)
    and a list of relevant tags or the save will be rejected.
    
    Args:
        name: Name of the asset.
        code: Source code.
        description: MANDATORY. Detailed technical specification of the logic.
        language: Programming language (e.g. 'python', 'typescript').
        tags: MANDATORY. List of categorization tags.
        dependencies: External library dependencies (e.g. ['boto3']).
        test_code: Test code for background validation (Phase 1).
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
        return "Saved successfully to LogicHive" if success else "Failed (Unknown Error)"
    except ValidationError as e:
        return f"Quality Gate REJECTED: {str(e)}"
    except LogicHiveError as e:
        return f"LogicHive Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"


if __name__ == "__main__":
    mcp.run()
