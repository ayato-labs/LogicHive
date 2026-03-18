class LogicHiveError(Exception):
    """Base exception for LogicHive."""

    pass


class ValidationError(LogicHiveError):
    """Raised when code validation or quality gate fails."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}


class StorageError(LogicHiveError):
    """Raised when storage operations fail."""

    pass


class AIProviderError(LogicHiveError):
    """Raised when AI provider (Gemini/Ollama) fails."""


class DependencyExtractionError(LogicHiveError):
    """Raised when dependency extraction fails critically."""

    pass
