import httpx
import time
import re
import ast
from typing import Tuple, List, Dict, Any

HUB_URL = "https://logichive-hub-344411298688.asia-northeast1.run.app"


# --- 1. scan_python_ast_security ---
def scan_python_ast_security(code: str) -> Tuple[bool, str]:
    """
    Static analysis to detect potentially dangerous Python code using AST.
    Blocks forbidden imports and dangerous function calls.
    """
    FORBIDDEN_IMPORTS = {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "pickle",
        "marshal",
        "shelve",
        "socket",
        "requests",
        "urllib",
        "http",
        "webbrowser",
        "ftplib",
        "telnetlib",
        "smtplib",
        "platform",
        "ctypes",
        "builtins",
        "importlib",
        "multiprocessing",
        "threading",
        "pysqlite3",
        "sqlite3",
    }
    FORBIDDEN_CALLS = {
        "eval",
        "exec",
        "compile",
        "breakpoint",
        "__import__",
        "system",
        "popen",
        "spawn",
        "fork",
        "kill",
    }
    FORBIDDEN_BUILTINS = {
        "open",
        "getattr",
        "setattr",
        "delattr",
        "hasattr",
        "globals",
        "locals",
        "vars",
        "dir",
        "help",
        "input",
    }

    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                        return False, f"Forbidden import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in FORBIDDEN_IMPORTS:
                    return False, f"Forbidden import from: {node.module}"
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if (
                        node.func.id in FORBIDDEN_CALLS
                        or node.func.id in FORBIDDEN_BUILTINS
                    ):
                        return False, f"Forbidden call: {node.func.id}"
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in FORBIDDEN_CALLS:
                        return False, f"Forbidden attribute call: {node.func.attr}"
        return True, "Code looks safe."
    except Exception as e:
        return False, f"Check failed: {str(e)}"


# --- 2. scan_api_secrets ---
def scan_api_secrets(text: str) -> Tuple[bool, str]:
    """
    Scans text for common API keys and secrets using regex patterns.
    """
    SECRET_PATTERNS = {
        "Google API Key": r"AIza[0-9A-Za-z_-]{35}",
        "GitHub Token": r"ghp_[a-zA-Z0-9]{36}",
        "OpenAI Key": r"sk-[a-zA-Z0-9]{48}",
    }
    for label, pattern in SECRET_PATTERNS.items():
        match = re.search(pattern, text)
        if match:
            return True, f"Detected potential {label}."
    return False, "No secrets found."


# --- 3. clean_text_trim_emojis ---
def clean_text_trim_emojis(text: str) -> str:
    """
    Cleans text by converting full-width spaces and removing emojis.
    """
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001f300-\U0001f9ff"
        "\U0001f600-\U0001f64f"
        "\U0001f680-\U0001f6ff"
        "\U0001f1e0-\U0001f1ff"
        "\u2600-\u26ff"
        "\u2700-\u27bf"
        "\u2300-\u23ff"
        "]+",
        flags=re.UNICODE,
    )
    if not text:
        return ""
    text = text.replace("\u3000", " ")
    text = EMOJI_PATTERN.sub("", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


# --- 4. run_shell_cmd_with_timing ---
import subprocess


def run_shell_cmd_with_timing(cmd: str) -> Dict[str, Any]:
    """
    Runs a shell command, measures execution time, and returns results.
    """
    start = time.time()
    try:
        cp = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        elapsed = time.time() - start
        return {
            "success": cp.returncode == 0,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
            "elapsed_seconds": round(elapsed, 4),
            "returncode": cp.returncode,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed_seconds": round(time.time() - start, 4),
        }


# --- 5. cleanup_temp_files ---
import os


def cleanup_temp_files(
    directory: str, extensions: List[str] = [".log", ".tmp"]
) -> Dict[str, Any]:
    """
    Recursively deletes temporary files with specified extensions.
    """
    deleted_count = 0
    errors = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                path = os.path.join(root, file)
                try:
                    os.remove(path)
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"Failed to delete {path}: {str(e)}")
    return {"deleted_count": deleted_count, "errors": errors}


# --- Registration Logic ---
def push_function(name: str, code: str, description: str):
    print(f"[INFO] Pushing '{name}'...")
    payload = {
        "name": name,
        "code": code,
        "description": description,
        "tags": ["utility", "test", "real-world"],
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(f"{HUB_URL}/api/v1/sync/push", json=payload)
        if resp.status_code == 200:
            print(f"[SUCCESS] {name} pushed.")
        else:
            print(f"[FAIL] {name}: {resp.status_code} - {resp.text}")


def main():
    import inspect

    functions = [scan_python_ast_security]

    for func in functions:
        name = func.__name__
        code = inspect.getsource(func)
        description = func.__doc__.strip() if func.__doc__ else "No description"
        push_function(name, code, description)


if __name__ == "__main__":
    main()
