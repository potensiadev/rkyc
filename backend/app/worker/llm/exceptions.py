"""
LLM Exception Classes
Custom exceptions for LLM service error handling
"""


class LLMError(Exception):
    """Base exception for LLM-related errors"""

    def __init__(self, message: str, provider: str = None, model: str = None):
        self.message = message
        self.provider = provider
        self.model = model
        super().__init__(self.message)


class AllProvidersFailedError(LLMError):
    """Raised when all LLM providers in the fallback chain have failed"""

    def __init__(self, message: str = "All LLM providers exhausted", errors: list = None):
        super().__init__(message)
        self.errors = errors or []


class ContentPolicyError(LLMError):
    """
    Raised when content violates provider policy.
    This error should NOT be retried.
    """

    def __init__(self, message: str, provider: str = None):
        super().__init__(message, provider)


class RateLimitError(LLMError):
    """
    Raised when rate limit is exceeded.
    This error should be retried with exponential backoff.
    """

    def __init__(self, message: str, provider: str = None, retry_after: int = None):
        super().__init__(message, provider)
        self.retry_after = retry_after


class InvalidResponseError(LLMError):
    """Raised when LLM response cannot be parsed or is invalid"""

    def __init__(self, message: str, provider: str = None, raw_response: str = None):
        super().__init__(message, provider)
        self.raw_response = raw_response


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out"""

    def __init__(self, message: str = "Request timed out", provider: str = None):
        super().__init__(message, provider)


# Backwards compatibility alias (deprecated)
TimeoutError = LLMTimeoutError
