"""Custom exceptions for AI providers."""

from typing import Optional


class AIError(Exception):
    """Base exception for AI-related errors."""
    pass


class RateLimitError(AIError):
    """Raised when a provider returns 429 Too Many Requests."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        provider: Optional[str] = None
    ):
        super().__init__(message)
        self.retry_after = retry_after  # Seconds to wait before retrying
        self.provider = provider

    def should_retry_same_provider(self, max_wait: int = 60) -> bool:
        """Check if we should retry the same provider or move to next."""
        if self.retry_after is None:
            return False
        return self.retry_after <= max_wait


class QuotaExceededError(AIError):
    """Raised when a provider's quota is exhausted."""

    def __init__(
        self,
        message: str = "Quota exceeded",
        provider: Optional[str] = None
    ):
        super().__init__(message)
        self.provider = provider


class ProviderUnavailableError(AIError):
    """Raised when a provider is not reachable."""

    def __init__(
        self,
        message: str = "Provider unavailable",
        provider: Optional[str] = None
    ):
        super().__init__(message)
        self.provider = provider


class AllProvidersFailedError(AIError):
    """Raised when all providers (except template) have failed.

    This is a non-fatal error if template fallback succeeded.
    """

    def __init__(
        self,
        message: str = "All AI providers failed",
        errors: dict = None,
        template_used: bool = False
    ):
        super().__init__(message)
        self.errors = errors or {}
        self.template_used = template_used


class InvalidResponseError(AIError):
    """Raised when provider returns an invalid or unparseable response."""

    def __init__(
        self,
        message: str = "Invalid response from provider",
        provider: Optional[str] = None,
        raw_response: Optional[str] = None
    ):
        super().__init__(message)
        self.provider = provider
        self.raw_response = raw_response


class ConfigurationError(AIError):
    """Raised when there's a configuration issue."""
    pass
