import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    MEMORY_LIMIT = "memory_limit"
    ERROR = "error"


@dataclass
class ExecutionLogs:
    stdout: str = ""
    stderr: str = ""


@dataclass
class ExecutionError:
    """E2B compatible Error structure."""

    name: str
    value: str
    traceback: str


@dataclass
class Result:
    """Rich media result (Jupyter-like)."""

    data: Any
    mime_type: str = "text/plain"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Standardized result for all LogicHive Executors."""

    status: ExecutionStatus
    logs: ExecutionLogs
    results: list[Result] = field(default_factory=list)
    error: ExecutionError | None = None
    duration: float = 0.0


class BaseExecutor(ABC):
    """
    Interface for code executors.
    Executors are responsible for environment orchestration and code execution.
    """

    @abstractmethod
    async def execute(
        self,
        code: str,
        test_code: str = "",
        dependencies: list[str] | None = None,
        timeout: int = 10,
        **kwargs,
    ) -> ExecutionResult:
        """
        Executes code in an isolated environment.

        Args:
            code: Source code to execute.
            test_code: Optional test code to run against the source.
            dependencies: List of external packages required.
            timeout: Maximum execution time in seconds.
            kwargs: Language specific execution parameters.
        """
        pass
