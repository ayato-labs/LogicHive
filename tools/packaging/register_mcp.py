import json
import os
import platform
from pathlib import Path


def get_config_paths():
    """Returns a list of potential MCP config file paths based on OS."""
    home = Path.home()
    system = platform.system()

    paths = {
        "Antigravity": home / ".gemini" / "antigravity" / "mcp_config.json",
        "GeminiCLI": home / ".gemini" / "settings.json",
    }

    if system == "Windows":
        appdata = Path(os.getenv("APPDATA", home / "AppData/Roaming"))
        paths.update(
            {
                "Cursor": appdata
                / "Cursor"
                / "User"
                / "globalStorage"
                / "heavy.cursor.cursor"
                / "mcp_config.json",
                "CloudCode": appdata
                / "Code"
                / "User"
                / "globalStorage"
                / "googlecloudtools.cloudcode"
                / "mcp_config.json",
                "VSCode_Generic": appdata / "Code" / "User" / "globalStorage" / "mcp_config.json",
            }
        )
    elif system == "Darwin":  # macOS
        lib_app_support = home / "Library" / "Application Support"
        paths.update(
            {
                "Cursor": lib_app_support
                / "Cursor"
                / "User"
                / "globalStorage"
                / "heavy.cursor.cursor"
                / "mcp_config.json",
                "CloudCode": lib_app_support
                / "Code"
                / "User"
                / "globalStorage"
                / "googlecloudtools.cloudcode"
                / "mcp_config.json",
                "VSCode_Generic": lib_app_support
                / "Code"
                / "User"
                / "globalStorage"
                / "mcp_config.json",
            }
        )
    else:  # Linux
        config_dir = home / ".config"
        paths.update(
            {
                "Cursor": config_dir
                / "Cursor"
                / "User"
                / "globalStorage"
                / "heavy.cursor.cursor"
                / "mcp_config.json",
                "CloudCode": config_dir
                / "Code"
                / "User"
                / "globalStorage"
                / "googlecloudtools.cloudcode"
                / "mcp_config.json",
                "VSCode_Generic": config_dir
                / "Code"
                / "User"
                / "globalStorage"
                / "mcp_config.json",
            }
        )

    return paths


def inject_instructions():
    """Injects usage instructions into AI agent instruction files."""
    home = Path.home()
    gemini_md = home / ".gemini" / "GEMINI.md"
    instruction = "- LogicHiveっていうMCPを活用してください。"

    if gemini_md.exists():
        try:
            with open(gemini_md, encoding="utf-8") as f:
                content = f.read()
            if instruction not in content:
                with open(gemini_md, "a", encoding="utf-8") as f:
                    # Ensure newline if needed
                    if not content.endswith("\n"):
                        f.write("\n")
                    f.write(instruction + "\n")
                print(f"[SUCCESS] Injected instruction into {gemini_md}")
            else:
                print(f"[INFO] Instruction already present in {gemini_md}")
        except Exception as e:
            print(f"[WARNING] Failed to update {gemini_md}: {e}")
    else:
        # Create it if the directory exists
        if gemini_md.parent.exists():
            try:
                with open(gemini_md, "w", encoding="utf-8") as f:
                    f.write("# コーディングの時のルール\n")
                    f.write(instruction + "\n")
                print(f"[SUCCESS] Created and injected instruction into {gemini_md}")
            except Exception as e:
                print(f"[WARNING] Failed to create {gemini_md}: {e}")


def register():
    print("--- LogicHive: Multi-Agent MCP Registration (Dynamic) ---")

    # Calculate project root dynamically relative to this script
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent

    # Normalize path for JSON config (using forward slashes for cross-platform stability)
    root_str = str(project_root).replace("\\", "/")

    # Use platform-specific path separator for PYTHONPATH
    pythonpath = f"{root_str}{os.pathsep}{root_str}/src"

    server_config = {
        "command": "uv",
        "args": [
            "run",
            "--project",
            root_str,
            "--no-sync",
            "python",
            f"{root_str}/src/mcp_server.py",
        ],
        "env": {"PYTHONPATH": pythonpath},
    }

    paths = get_config_paths()

    count = 0
    for name, path in paths.items():
        if not path.parent.exists():
            continue

        print(f"[INFO] Checking {name} configuration at {path}...")

        # Load existing or create new
        content = {}
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    content = json.load(f)
            except Exception as e:
                print(f"[WARNING] Could not read {path}: {e}")
                continue

        if "mcpServers" not in content:
            content["mcpServers"] = {}

        # Inject server
        content["mcpServers"]["logic-hive"] = server_config

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2)
            print(f"[SUCCESS] Registered with {name}!")
            count += 1
        except Exception as e:
            print(f"[ERROR] Failed to write to {path}: {e}")

    # Step 2: Inject instructions into Agent guideline files
    inject_instructions()

    if count == 0:
        print("\n[NOTE] No active MCP environments were detected.")
        print(
            "Please ensure your AI agents (Cursor, VS Code + Cloud Code, Gemini CLI, etc.) are installed."
        )
    else:
        print(f"\n[READY] LogicHive registered in {count} environment(s).")
        print("Please restart your AI agents to apply changes.")


if __name__ == "__main__":
    register()
