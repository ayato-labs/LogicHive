import json
import os
from pathlib import Path


def register_mcp_server(
    name: str, command: str, args: list = None, env: dict = None, agent: str = "all"
):
    """
    Registers an MCP server for various AI agents by updating their configuration files.

    Args:
        name: Unique identifier for the MCP server.
        command: Command to execute the server (e.g., 'npx', 'python').
        args: List of command-line arguments.
        env: Dictionary of environment variables.
        agent: Target agent ('cursor', 'antigravity', 'claude', 'all').

    Returns:
        str: Summary of registration results across different paths.
    """
    home = Path.home()
    config_paths = {
        "cursor": [
            home / ".cursor" / "mcp.json",
        ],
        "antigravity": [
            home / ".gemini" / "antigravity" / "mcp_config.json",
        ],
        "claude": [
            Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json",
            home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
        ],
    }

    new_server = {"command": command, "args": args or [], "env": env or {}}

    results = []
    targets = config_paths.keys() if agent == "all" else [agent]

    for target in targets:
        paths = config_paths.get(target, [])
        for path in paths:
            try:
                # Ensure parent directory exists for critical configs
                if target in ["cursor", "antigravity"] and not path.parent.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)

                if path.exists():
                    with open(path, encoding="utf-8") as f:
                        content = f.read().strip()
                        config = json.loads(content) if content else {}
                else:
                    config = {}

                if "mcpServers" not in config:
                    config["mcpServers"] = {}

                # Update or Add the server
                config["mcpServers"][name] = new_server

                with open(path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)

                results.append(f"[SUCCESS] Registered '{name}' for {target} at {path}")
            except Exception as e:
                # If it's just a file not found on a secondary path, ignore it unless it's the only path
                if not path.exists() and target == "claude":
                    continue
                results.append(f"[ERROR] {target} at {path}: {str(e)}")

    return "\n".join(results) if results else "No valid configuration paths found."
