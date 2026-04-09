import logging
from typing import Dict, Type, Optional
from .base import BaseExecutor

logger = logging.getLogger(__name__)


class ExecutorFactory:
    """Registry and factory for code executors."""

    _executors: Dict[str, BaseExecutor] = {}

    @classmethod
    def register(cls, language: str, executor: BaseExecutor):
        cls._executors[language.lower()] = executor
        logger.debug(f"ExecutorFactory: Registered executor for {language}")

    @classmethod
    def get_executor(cls, language: str) -> Optional[BaseExecutor]:
        return cls._executors.get(language.lower())
