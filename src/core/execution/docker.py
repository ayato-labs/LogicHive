import asyncio
import json
import logging
import time

from .base import (
    BaseExecutor,
    ExecutionError,
    ExecutionLogs,
    ExecutionResult,
    ExecutionStatus,
    Result,
)

logger = logging.getLogger(__name__)


class DockerPythonExecutor(BaseExecutor):
    """
    Hardened Python Executor that runs code inside isolated Docker containers.
    Provides maximum security and resource isolation.
    """

    def __init__(self, image: str = "python:3.11-slim"):
        self.image = image
        self.name = "python-docker"

    async def execute(
        self,
        code: str,
        test_code: str = "",
        dependencies: list[str] | None = None,
        timeout: int = 30,
        **kwargs,
    ) -> ExecutionResult:
        start_time = time.time()

        # 1. Prepare Docker execution script
        # We inject a simple JSON reporter to capture error details structured
        full_script = self._wrap_code(code, test_code)

        # 2. Build Docker Command
        cmd = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            "none",
            "--memory",
            "512m",
            "--cpus",
            "0.5",
            self.image,
            "python",
            "-c",
            full_script,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Note: We don't need stdin here as we pass the script via -c
            # but we use communicate to wait for completion
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout + 5.0,  # Give docker some grace period
            )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            duration = time.time() - start_time

            # 3. Parse Output
            # We look for a specific JSON boundary in stdout
            results = []
            error = None
            status = ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILURE

            # Simple logic to find the JSON result block injected by _wrap_code
            if "LOGICHIVE_RESULT_START" in stdout:
                try:
                    parts = stdout.split("LOGICHIVE_RESULT_START")
                    json_str = parts[1].split("LOGICHIVE_RESULT_END")[0]
                    raw_result = json.loads(json_str)

                    if raw_result.get("error"):
                        err_info = raw_result["error"]
                        error = ExecutionError(
                            name=err_info.get("name", "RuntimeError"),
                            value=err_info.get("value", ""),
                            traceback=err_info.get("traceback", ""),
                        )
                        status = ExecutionStatus.FAILURE

                    if "main_result" in raw_result:
                        results.append(Result(data=raw_result["main_result"]))
                except Exception as e:
                    logger.error(f"DockerPythonExecutor: Failed to parse result: {e}")

            if status == ExecutionStatus.FAILURE and not error:
                error = ExecutionError(
                    name="DockerError",
                    value=f"Container exited with code {process.returncode}",
                    traceback=stderr,
                )

            return ExecutionResult(
                status=status,
                logs=ExecutionLogs(stdout=stdout, stderr=stderr),
                results=results,
                error=error,
                duration=duration,
            )

        except asyncio.TimeoutError:
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                logs=ExecutionLogs(stderr="Execution timed out inside Docker."),
                duration=time.time() - start_time,
            )
        except Exception as e:
            logger.exception("DockerPythonExecutor: Unhandled exception")
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                logs=ExecutionLogs(stderr=str(e)),
                error=ExecutionError(name=type(e).__name__, value=str(e), traceback=""),
                duration=time.time() - start_time,
            )

    def _wrap_code(self, code: str, test_code: str) -> str:
        """Injects reporting logic to capture results from within the container."""
        import json

        # We use a literal block to avoid escaping hell
        return f"""
import json, traceback, sys

results = {{"main_result": None, "error": None}}

def run():
    global results
    try:
        # Execute Main Code
        exec({json.dumps(code)}, globals())
        
        # Execute Test Code
        if {json.dumps(test_code)}:
            exec({json.dumps(test_code)}, globals())
            results["main_result"] = "Tests Passed"
        else:
            results["main_result"] = "Execution Successful"
    except Exception as e:
        results["error"] = {{
            "name": type(e).__name__,
            "value": str(e),
            "traceback": traceback.format_exc()
        }}
        return False
    return True

success = run()
print("LOGICHIVE_RESULT_START" + json.dumps(results) + "LOGICHIVE_RESULT_END")
sys.exit(0 if success else 1)
"""
