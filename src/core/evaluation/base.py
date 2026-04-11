from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class EvaluationResult:
    score: float  # 0.0 to 100.0
    reason: str
    details: dict[str, Any] | None = None


class BaseEvaluator(ABC):
    """
    Base interface for all LogicHive Evaluators.
    Evaluators analyze code assets and return a score and reasoning.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the evaluator."""
        pass

    @abstractmethod
    async def evaluate(self, code: str, language: str, **kwargs) -> EvaluationResult:
        """
        Performs the evaluation.
        Args:
            code: The source code to evaluate.
            language: The programming language.
            **kwargs: Additional context (e.g. metadata).
        Returns:
            EvaluationResult containing score and reason.
        """
        pass
