import logging

from ...execution.base import ExecutionStatus
from ...execution.factory import ExecutorFactory
from ..base import BaseEvaluator, EvaluationResult

logger = logging.getLogger(__name__)


class RuntimeEvaluator(BaseEvaluator):
    """
    Evaluates code quality by actually executing it and running tests.
    Uses the Execution layer to create ephemeral environments.
    """

    @property
    def name(self) -> str:
        return "runtime"

    async def evaluate(self, code: str, language: str, **kwargs) -> EvaluationResult:
        """
        Executes the code and optional tests.
        Args:
            code: Source code to evaluate.
            language: Programming language.
            **kwargs:
                test_code: Optional test assertions to run.
                dependencies: List of packages required.
                timeout: Maximum execution time.
        """
        test_code = kwargs.get("test_code", "")
        dependencies = kwargs.get("dependencies", [])
        mock_imports = kwargs.get("mock_imports", [])
        timeout = kwargs.get("timeout", 45)

        if not test_code:
            return EvaluationResult(
                score=40.0,
                reason="No test code provided. Verification skipped.",
                details={"status": "missing_tests"}
            )

        # 2. Get Executor
        executor = ExecutorFactory.get_executor(language)
        if not executor:
            return EvaluationResult(
                score=0.0,
                reason=f"Infrastructure Error: No executor available for language '{language}'.",
                details={"status": "not_supported"}
            )

        # 3. Execute
        try:
            result = await executor.execute(
                code=code,
                test_code=test_code,
                dependencies=dependencies,
                timeout=timeout,
                mock_imports=mock_imports
            )

            # 4. Map ExecutionResult to EvaluationResult
            if result.status == ExecutionStatus.SUCCESS:
                return EvaluationResult(
                    score=100.0,
                    reason="Tests passed successfully in ephemeral environment.",
                    details={
                        "duration": result.duration,
                        "stdout": result.logs.stdout,
                        "status": result.status.value
                    }
                )

            elif result.status == ExecutionStatus.TIMEOUT:
                return EvaluationResult(
                    score=0.0,
                    reason=f"Critical Failure: Execution timed out after {timeout} seconds. Possible infinite loop.",
                    details={"status": result.status.value}
                )

            elif result.status == ExecutionStatus.FAILURE:
                reason_msg = "Critical Failure: Logic error or failing test."
                if result.error:
                    reason_msg += f" [{result.error.name}] {result.error.value}"

                return EvaluationResult(
                    score=0.0,
                    reason=reason_msg,
                    details={
                        "traceback": result.error.traceback if result.error else "",
                        "stderr": result.logs.stderr,
                        "status": result.status.value
                    }
                )

            else:
                # Infrastructure error
                return EvaluationResult(
                    score=10.0,
                    reason=f"Infrastructure Warning: Execution environment error. {result.logs.stderr}",
                    details={"status": result.status.value}
                )

        except Exception as e:
            logger.exception("RuntimeEvaluator: Unexpected error during evaluation")
            return EvaluationResult(
                score=0.0,
                reason=f"Critical Evaluator Error: {str(e)}",
                details={"error_type": type(e).__name__}
            )
