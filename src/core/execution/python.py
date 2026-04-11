import logging
import asyncio
import tempfile
import os
import json
import time
import traceback
from pathlib import Path
from typing import List, Optional
from .base import BaseExecutor, ExecutionResult, ExecutionStatus, ExecutionLogs, ExecutionError, Result
from .factory import ExecutorFactory

logger = logging.getLogger(__name__)


class EphemeralPythonExecutor(BaseExecutor):
    """
    Executes Python code in an ephemeral environment using `uv`.
    Focuses on security through isolation and rich E2B-compatible telemetry.
    """

    def __init__(self):
        self.name = "python"

    def _kill_process_tree(self, pid: int):
        """Kills a process and all its children cross-platform."""
        import psutil
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            parent.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    async def execute(
        self,
        code: str,
        test_code: str = "",
        dependencies: Optional[List[str]] = None,
        timeout: int = 20,
        memory_limit_mb: int = 256,
        **kwargs,
    ) -> ExecutionResult:
        start_time = time.time()
        dependencies = dependencies or []
        
        # 1. Prepare Workspace
        with tempfile.TemporaryDirectory(prefix="logichive_exec_") as tmpdir:
            tmp_path = Path(tmpdir)
            script_file = tmp_path / "solution.py"
            harness_file = tmp_path / "harness.py"
            result_file = tmp_path / "result.json"

            # Write the actual solution code
            script_file.write_text(code, encoding="utf-8")

            # Create Harness
            harness_content = self._generate_harness(code, test_code, result_file)
            harness_file.write_text(harness_content, encoding="utf-8")

            # 2. Build uv run command
            cmd = ["uv", "run", "--quiet", "--offline", "--no-project"]
            for dep in dependencies:
                cmd.extend(["--with", dep])
            cmd.extend(["python", str(harness_file)])

            # 3. Execute with isolated environment
            process_env = {
                k: v for k, v in os.environ.items() 
                if k in ["PATH", "SYSTEMROOT", "SystemDrive", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "USERNAME"]
            }
            process_env["PYTHONPATH"] = ""
            process_env["PYTHONNOUSERSITE"] = "1"
            
            memory_exceeded = False
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir,
                    env=process_env,
                )

                async def monitor_resources():
                    nonlocal memory_exceeded
                    import psutil
                    while process.returncode is None:
                        try:
                            parent = psutil.Process(process.pid)
                            # Sum up memory of parent and all recursive children
                            total_mem = parent.memory_info().rss
                            for child in parent.children(recursive=True):
                                try:
                                    total_mem += child.memory_info().rss
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    continue
                            
                            if (total_mem / 1024 / 1024) > memory_limit_mb:
                                logger.warning(f"Executor: Memory limit exceeded ({total_mem / 1024 / 1024:.1f}MB > {memory_limit_mb}MB). Killing process tree.")
                                memory_exceeded = True
                                self._kill_process_tree(process.pid)
                                break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            break
                        await asyncio.sleep(0.2)

                monitor_task = asyncio.create_task(monitor_resources())
                
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(), timeout=timeout
                    )
                    stdout = stdout_bytes.decode("utf-8", errors="replace")
                    stderr = stderr_bytes.decode("utf-8", errors="replace")
                except asyncio.TimeoutError:
                    self._kill_process_tree(process.pid)
                    await process.wait()
                    return ExecutionResult(
                        status=ExecutionStatus.TIMEOUT,
                        logs=ExecutionLogs(stderr="Execution timed out."),
                        duration=time.time() - start_time,
                    )
                finally:
                    monitor_task.cancel()

                if memory_exceeded:
                    return ExecutionResult(
                        status=ExecutionStatus.MEMORY_LIMIT,
                        logs=ExecutionLogs(stderr=f"Memory limit exceeded ({memory_limit_mb}MB)."),
                        duration=time.time() - start_time,
                    )

                # 4. Parse Results
                duration = time.time() - start_time
                status = ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILURE
                
                # Try to load structured results from the harness
                results = []
                error = None
                
                if result_file.exists():
                    try:
                        raw_result = json.loads(result_file.read_text(encoding="utf-8"))
                        if "main_result" in raw_result:
                            results.append(Result(
                                data=raw_result["main_result"],
                                metadata={"is_main_result": True}
                            ))
                        if raw_result.get("error"):
                            err_info = raw_result["error"]
                            error = ExecutionError(
                                name=err_info.get("name", "UnknownError"),
                                value=err_info.get("value", ""),
                                traceback=err_info.get("traceback", "")
                            )
                            status = ExecutionStatus.FAILURE
                    except Exception as e:
                        logger.error(f"Executor: Failed to parse harness results: {e}")

                # If harness didn't catch error but exit code is non-zero, treat as infrastructure error or crash
                if status == ExecutionStatus.FAILURE and not error:
                    error = ExecutionError(
                        name="RuntimeError",
                        value=f"Process exited with code {process.returncode}",
                        traceback=stderr
                    )

                return ExecutionResult(
                    status=status,
                    logs=ExecutionLogs(stdout=stdout, stderr=stderr),
                    results=results,
                    error=error,
                    duration=duration
                )

            except Exception as e:
                logger.exception("Executor: Subprocess call failed")
                return ExecutionResult(
                    status=ExecutionStatus.ERROR,
                    logs=ExecutionLogs(stderr=str(e)),
                    error=ExecutionError(name=type(e).__name__, value=str(e), traceback=traceback.format_exc()),
                    duration=time.time() - start_time
                )

    def _generate_harness(self, code: str, test_code: str, result_file: Path) -> str:
        """
        Generates a robust harness that executes the code and exports results as JSON.
        Modeled after Jupyter/E2B behavior.
        """
        # We escape the result path for the string template
        res_path = str(result_file).replace("\\", "\\\\")
        
        harness = f"""
import json
import traceback
import sys

# Result structure
results = {{
    "main_result": None,
    "error": None
}}

def block_network(*args, **kwargs):
    raise Exception("NETWORK_ACCESS_DENIED: LogicHive sandbox prevents network calls during verification.")

def apply_sandbox():
    import socket
    socket.socket = block_network
    socket.getaddrinfo = block_network
    # Also block common high-level libs if already imported
    for mod in ["urllib", "requests", "http.client"]:
        if mod in sys.modules:
            del sys.modules[mod]

def run_user_code():
    global results
    try:
        # 0. Apply runtime sandbox
        apply_sandbox()
        
        # 1. Execute the main code (defines functions/classes)
        # We use a custom dict to capture defined symbols if needed, 
        # but here we just exec in global scope.
        exec({json.dumps(code)}, globals())
        
        # 2. Execute test code if provided
        if {json.dumps(test_code)}:
            # Tests are expected to raise AssertionError on failure
            exec({json.dumps(test_code)}, globals())
            results["main_result"] = "Tests Passed"
        else:
            # If no tests, we just check if it imports/defines correctly
            results["main_result"] = "Execution Successful"
            
    except Exception as e:
        type_name = type(e).__name__
        results["error"] = {{
            "name": type_name,
            "value": str(e),
            "traceback": traceback.format_exc()
        }}
        # We print to stderr so it shows up in logs too
        sys.stderr.write(traceback.format_exc())
        return False
    return True

success = run_user_code()

# Write results to the dedicated file
with open("{res_path}", "w", encoding="utf-8") as f:
    json.dump(results, f)

# Exit with non-zero if tests or execution failed
sys.exit(0 if success else 1)
"""
        return harness


# Auto-register
ExecutorFactory.register("python", EphemeralPythonExecutor())
"""
Implement EphemeralPythonExecutor
"""
