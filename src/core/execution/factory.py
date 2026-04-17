import importlib
import logging
import pkgutil

from .base import BaseExecutor

logger = logging.getLogger(__name__)


class ExecutorFactory:
    """Registry and factory for code executors with dynamic loading."""

    _executors: dict[str, BaseExecutor] = {}
    _loaded = False

    @classmethod
    def _load_plugins(cls):
        """Dynamically discovers and loads all executor plugins in the current package."""
        if cls._loaded:
            return

        try:
            # Package is src.core.execution
            package_name = __package__
            package = importlib.import_module(package_name)

            for loader, name, is_pkg in pkgutil.walk_packages(
                package.__path__, package.__name__ + "."
            ):
                if name.endswith("__init__") or name.endswith(".base") or name.endswith(".factory"):
                    continue
                try:
                    importlib.import_module(name)
                    logger.debug(f"ExecutorFactory: Loaded executor module {name}")
                except Exception as e:
                    logger.error(f"ExecutorFactory: Failed to load module {name}: {e}")
            cls._loaded = True
        except Exception as e:
            logger.error(f"ExecutorFactory: Plugin discovery failed: {e}")

    @classmethod
    def register(cls, language: str, executor: BaseExecutor):
        cls._executors[language.lower()] = executor
        logger.debug(f"ExecutorFactory: Registered executor for {language}")

    @classmethod
    def get_executor(cls, language: str) -> BaseExecutor | None:
        cls._load_plugins()
        lang = language.lower()
        
        from core.config import EXECUTION_DRIVER
        
        # If docker is requested and we have a docker variant, return it
        if EXECUTION_DRIVER == "docker":
            # For now, we only have docker for python
            if lang == "python":
                from .docker import DockerPythonExecutor
                return DockerPythonExecutor()
        
        return cls._executors.get(lang)
