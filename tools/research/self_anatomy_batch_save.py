import asyncio
import os
import sys

# Add LogicHive src to path
LOGICHIVE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(os.path.join(LOGICHIVE_ROOT, "src"))

# Force absolute paths for this execution
os.environ["SQLITE_DB_PATH"] = os.path.join(LOGICHIVE_ROOT, "storage", "data", "logichive.db")
os.environ["FS_DATA_DIR"] = os.path.join(LOGICHIVE_ROOT, "storage", "data")

import orchestrator  # noqa: E402


async def save_to_vault(name, code, description, tags):
    print(f"Saving {name}...")
    success = await orchestrator.do_save_async(
        name=name, code=code, description=description, tags=tags, language="python"
    )
    if success:
        print(f"  ✅ {name} saved.")
    else:
        print(f"  ❌ {name} failed.")


async def batch_evolution():
    # 1. infer_path_from_content
    code_1 = """import re

def infer_path_from_content(content: str) -> str | None:
    \"\"\"
    Heuristically infers a file path from a leading comment in the code content.
    Looks for patterns like '# filename: path/to/file.py' or '# path: file.py'.
    \"\"\"
    match = re.search(
        r"^#\\s*(?:filename|file|path):\\s*([a-zA-Z0-9_./-]+)",
        content,
        re.MULTILINE,
    )
    if match:
        return match.group(1).strip()
    return None
"""
    await save_to_vault(
        "infer_path_from_content",
        code_1,
        "Infers file paths from source code comments using regex heuristics.",
        ["utility", "heuristics", "file_management"],
    )

    # 2. format_shell_output
    code_2 = """def format_shell_output(stdout: str, stderr: str, returncode: int) -> str:
    \"\"\"
    Standardizes the display of shell command results for AI consumption.
    Includes success/failure status and unified output block.
    \"\"\"
    output = str(stdout) + str(stderr)
    status = "SUCCESS" if returncode == 0 else f"FAILED (Exit {returncode})"
    return f"[{status}]\\n{output}"
"""
    # Note: the double backslash is needed for f-string escaping in the script generating script
    await save_to_vault(
        "format_shell_output",
        code_2.replace("\\n", "\\\\n"),
        "Standardizes shell command results into a readable format for AI agents.",
        ["utility", "shell", "formatting"],
    )

    # 3. get_mcp_server_for_tool
    code_3 = """def get_mcp_server_for_tool(tool_name: str, tool_to_client_map: dict[str, str]) -> str | None:
    \"\"\"
    Identifies which MCP server owns a specific tool based on a registry map.
    Returns None if the tool is not found.
    \"\"\"
    return tool_to_client_map.get(tool_name)
"""
    await save_to_vault(
        "get_mcp_server_for_tool",
        code_3,
        "Retrieves the target MCP server for a given tool name from a registry mapping.",
        ["mcp", "dispatch", "utility"],
    )

    # 4. normalize_container_path
    code_4 = """def normalize_container_path(path: str) -> str:
    \"\"\"
    Converts Windows-style paths to POSIX-style paths for compatibility with Docker containers.
    \"\"\"
    return path.replace("\\\\", "/")
"""
    await save_to_vault(
        "normalize_container_path",
        code_4.replace("\\\\", "\\\\\\\\"),
        "Converts Windows paths to POSIX-style paths for Docker container compatibility.",
        ["utility", "docker", "path"],
    )


if __name__ == "__main__":
    asyncio.run(batch_evolution())
