from fastmcp import FastMCP
import orchestrator

# Initialize FastMCP server
mcp = FastMCP("LogicHive")


@mcp.tool()
async def search_functions(query: str, limit: int = 5) -> str:
    """
    Search for high-quality code functions in the LogicHive vault using semantic search.
    Args:
        query: Natural language description of the logic needed.
        limit: Max number of results to return.
    """
    results = await orchestrator.do_search_async(query, limit)
    if not results:
        return "No matching functions found."

    formatted = f"### Search Results for: {query}\n\n"
    for r in results:
        lang_str = f" [{r.get('language', 'unknown')}]"
        # Use similarity if available (from semantic search)
        reliability = r.get('reliability_score', 'N/A')
        if 'similarity' in r:
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
    name: str, code: str, description: str = "", language: str = "python", tags: list = []
) -> str:
    """
    Save a new high-quality function to the LogicHive vault for future reuse.
    Args:
        name: Name of the asset.
        code: Source code.
        description: Brief explanation of what it does.
        language: Programming language (e.g. 'python', 'typescript').
        tags: Categorization tags.
    """
    # do_save_async now handles metadata optimization and embedding generation
    success = await orchestrator.do_save_async(
        name=name, 
        code=code, 
        description=description, 
        tags=tags, 
        language=language
    )
    return "Saved with AI optimization" if success else "Failed"


if __name__ == "__main__":
    mcp.run()
