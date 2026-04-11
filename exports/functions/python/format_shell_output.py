def format_shell_output(stdout: str, stderr: str, returncode: int) -> str:
    """
    Standardizes the display of shell command results for AI consumption.
    Includes success/failure status and unified output block.
    """
    output = str(stdout) + str(stderr)
    status = "SUCCESS" if returncode == 0 else f"FAILED (Exit {returncode})"
    return f"[{status}]\\n{output}"
