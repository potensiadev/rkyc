"""
LLM Exception Classes
Custom exceptions for LLM service error handling

P1-3: Error Handling 통합
- 통합 Error Taxonomy
- Error Severity 레벨
- Error Codes
- Central Error Handler
"""

from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, UTC


# ============================================================================
# Error Taxonomy (P1-3)
# ============================================================================


class ErrorCategory(str, Enum):
    """Error category for taxonomy"""
    PROVIDER = "provider"           # LLM provider issues
    NETWORK = "network"             # Network/connection issues
    VALIDATION = "validation"       # Response validation issues
    CONFIGURATION = "configuration" # Configuration/setup issues
    RATE_LIMIT = "rate_limit"       # Rate limiting
    POLICY = "policy"               # Content policy violations
    TIMEOUT = "timeout"             # Timeout issues
    CIRCUIT = "circuit"             # Circuit breaker issues
    CACHE = "cache"                 # Cache issues
    CONSENSUS = "consensus"         # Consensus engine issues
    UNKNOWN = "unknown"             # Unclassified errors


class ErrorSeverity(str, Enum):
    """Error severity level"""
    CRITICAL = "critical"   # System-level failure, needs immediate attention
    HIGH = "high"           # Major functionality impacted
    MEDIUM = "medium"       # Partial functionality impacted, fallback available
    LOW = "low"             # Minor issue, operation can continue
    INFO = "info"           # Informational, not a real error


class ErrorCode(str, Enum):
    """Standardized error codes"""
    # Provider errors (1xxx)
    PROVIDER_UNAVAILABLE = "LLM1001"
    PROVIDER_AUTHENTICATION = "LLM1002"
    PROVIDER_QUOTA_EXCEEDED = "LLM1003"
    PROVIDER_INTERNAL_ERROR = "LLM1004"
    ALL_PROVIDERS_FAILED = "LLM1005"

    # Network errors (2xxx)
    NETWORK_TIMEOUT = "LLM2001"
    NETWORK_CONNECTION = "LLM2002"
    NETWORK_DNS = "LLM2003"

    # Validation errors (3xxx)
    INVALID_RESPONSE_FORMAT = "LLM3001"
    INVALID_JSON = "LLM3002"
    MISSING_REQUIRED_FIELD = "LLM3003"
    EMPTY_RESPONSE = "LLM3004"

    # Configuration errors (4xxx)
    NO_API_KEY = "LLM4001"
    INVALID_MODEL = "LLM4002"
    INVALID_CONFIGURATION = "LLM4003"

    # Rate limit errors (5xxx)
    RATE_LIMIT_EXCEEDED = "LLM5001"
    TOKEN_LIMIT_EXCEEDED = "LLM5002"
    CONCURRENT_LIMIT_EXCEEDED = "LLM5003"

    # Policy errors (6xxx)
    CONTENT_POLICY_VIOLATION = "LLM6001"
    SAFETY_FILTER_TRIGGERED = "LLM6002"

    # Circuit breaker errors (7xxx)
    CIRCUIT_OPEN = "LLM7001"
    CIRCUIT_HALF_OPEN_FAILED = "LLM7002"

    # Cache errors (8xxx)
    CACHE_CONNECTION_FAILED = "LLM8001"
    CACHE_SERIALIZATION_FAILED = "LLM8002"

    # Consensus errors (9xxx)
    CONSENSUS_FAILED = "LLM9001"
    CONSENSUS_DISCREPANCY = "LLM9002"

    # Unknown (0xxx)
    UNKNOWN_ERROR = "LLM0001"


@dataclass
class ErrorContext:
    """Additional context for error tracking"""
    trace_id: Optional[str] = None
    job_id: Optional[str] = None
    corp_id: Optional[str] = None
    operation: Optional[str] = None
    attempt: int = 1
    max_attempts: int = 3
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict = field(default_factory=dict)


class LLMError(Exception):
    """
    Base exception for LLM-related errors

    P1-3: Extended with taxonomy support
    """

    # Default values for taxonomy
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    code: ErrorCode = ErrorCode.UNKNOWN_ERROR
    retryable: bool = True

    def __init__(
        self,
        message: str,
        provider: str = None,
        model: str = None,
        context: Optional[ErrorContext] = None,
    ):
        self.message = message
        self.provider = provider
        self.model = model
        self.context = context or ErrorContext()
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/API response"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "retryable": self.retryable,
            "provider": self.provider,
            "model": self.model,
            "context": {
                "trace_id": self.context.trace_id,
                "job_id": self.context.job_id,
                "corp_id": self.context.corp_id,
                "operation": self.context.operation,
                "attempt": self.context.attempt,
                "timestamp": self.context.timestamp,
            },
        }


class AllProvidersFailedError(LLMError):
    """Raised when all LLM providers in the fallback chain have failed"""

    category = ErrorCategory.PROVIDER
    severity = ErrorSeverity.CRITICAL
    code = ErrorCode.ALL_PROVIDERS_FAILED
    retryable = False

    def __init__(
        self,
        message: str = "All LLM providers exhausted",
        errors: list = None,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(message, context=context)
        self.errors = errors or []

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["errors"] = self.errors
        return result


class ContentPolicyError(LLMError):
    """
    Raised when content violates provider policy.
    This error should NOT be retried.
    """

    category = ErrorCategory.POLICY
    severity = ErrorSeverity.HIGH
    code = ErrorCode.CONTENT_POLICY_VIOLATION
    retryable = False

    def __init__(self, message: str, provider: str = None, context: Optional[ErrorContext] = None):
        super().__init__(message, provider, context=context)


class RateLimitError(LLMError):
    """
    Raised when rate limit is exceeded.
    This error should be retried with exponential backoff.
    """

    category = ErrorCategory.RATE_LIMIT
    severity = ErrorSeverity.MEDIUM
    code = ErrorCode.RATE_LIMIT_EXCEEDED
    retryable = True

    def __init__(
        self,
        message: str,
        provider: str = None,
        retry_after: int = None,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(message, provider, context=context)
        self.retry_after = retry_after

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["retry_after"] = self.retry_after
        return result


class InvalidResponseError(LLMError):
    """Raised when LLM response cannot be parsed or is invalid"""

    category = ErrorCategory.VALIDATION
    severity = ErrorSeverity.MEDIUM
    code = ErrorCode.INVALID_RESPONSE_FORMAT
    retryable = True

    def __init__(
        self,
        message: str,
        provider: str = None,
        raw_response: str = None,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(message, provider, context=context)
        self.raw_response = raw_response

    def to_dict(self) -> dict:
        result = super().to_dict()
        # Truncate raw response for safety
        result["raw_response"] = self.raw_response[:500] if self.raw_response else None
        return result


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out"""

    category = ErrorCategory.TIMEOUT
    severity = ErrorSeverity.MEDIUM
    code = ErrorCode.NETWORK_TIMEOUT
    retryable = True

    def __init__(
        self,
        message: str = "Request timed out",
        provider: str = None,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(message, provider, context=context)


class NoAPIKeyConfiguredError(LLMError):
    """
    Raised when no API keys are configured for any LLM provider.

    P0-004 fix: Added to clearly distinguish configuration errors
    from runtime failures.
    """

    category = ErrorCategory.CONFIGURATION
    severity = ErrorSeverity.CRITICAL
    code = ErrorCode.NO_API_KEY
    retryable = False

    def __init__(
        self,
        message: str = "No API keys configured for LLM providers",
        providers: list[str] = None,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(message, context=context)
        self.providers = providers or []

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["providers"] = self.providers
        return result


class CircuitBreakerError(LLMError):
    """Raised when circuit breaker is open"""

    category = ErrorCategory.CIRCUIT
    severity = ErrorSeverity.MEDIUM
    code = ErrorCode.CIRCUIT_OPEN
    retryable = False  # Don't retry immediately, wait for cooldown

    def __init__(
        self,
        message: str,
        provider: str = None,
        cooldown_remaining: int = 0,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(message, provider, context=context)
        self.cooldown_remaining = cooldown_remaining

    def to_dict(self) -> dict:
        result = super().to_dict()
        result["cooldown_remaining"] = self.cooldown_remaining
        return result


class CacheError(LLMError):
    """Raised when cache operations fail"""

    category = ErrorCategory.CACHE
    severity = ErrorSeverity.LOW
    code = ErrorCode.CACHE_CONNECTION_FAILED
    retryable = True

    def __init__(
        self,
        message: str,
        operation: str = None,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(message, context=context)
        self.cache_operation = operation


class ConsensusError(LLMError):
    """Raised when consensus engine fails"""

    category = ErrorCategory.CONSENSUS
    severity = ErrorSeverity.MEDIUM
    code = ErrorCode.CONSENSUS_FAILED
    retryable = True

    def __init__(
        self,
        message: str,
        discrepancy_fields: list[str] = None,
        context: Optional[ErrorContext] = None,
    ):
        super().__init__(message, context=context)
        self.discrepancy_fields = discrepancy_fields or []


# ============================================================================
# Central Error Handler (P1-3)
# ============================================================================


class LLMErrorHandler:
    """
    Central error handler for consistent error processing.

    Features:
    - Error classification
    - Logging with structured data
    - Error aggregation for reporting
    """

    def __init__(self, logger=None):
        self._logger = logger
        self._error_counts: dict[str, int] = {}

    @property
    def logger(self):
        if self._logger is None:
            from app.worker.tracing import get_logger
            self._logger = get_logger("LLMErrorHandler")
        return self._logger

    def handle(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        reraise: bool = True,
    ) -> Optional[LLMError]:
        """
        Handle an error with consistent logging and classification.

        Args:
            error: The exception to handle
            context: Additional context
            reraise: Whether to reraise the error

        Returns:
            Classified LLMError or None
        """
        # Classify the error
        llm_error = self.classify(error, context)

        # Update error counts
        error_key = f"{llm_error.category.value}:{llm_error.code.value}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

        # Log based on severity
        error_dict = llm_error.to_dict()

        if llm_error.severity == ErrorSeverity.CRITICAL:
            self.logger.error("llm_error_critical", **error_dict)
        elif llm_error.severity == ErrorSeverity.HIGH:
            self.logger.error("llm_error_high", **error_dict)
        elif llm_error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning("llm_error_medium", **error_dict)
        else:
            self.logger.info("llm_error_low", **error_dict)

        if reraise:
            raise llm_error

        return llm_error

    def classify(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
    ) -> LLMError:
        """
        Classify any exception into an LLMError.

        Args:
            error: The exception to classify
            context: Additional context

        Returns:
            Classified LLMError
        """
        # Already an LLMError
        if isinstance(error, LLMError):
            if context:
                error.context = context
            return error

        # Classify based on error message/type
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        if "timeout" in error_str or "timeout" in error_type:
            return LLMTimeoutError(str(error), context=context)

        if "rate_limit" in error_str or "429" in error_str:
            return RateLimitError(str(error), context=context)

        if "content_policy" in error_str or "safety" in error_str:
            return ContentPolicyError(str(error), context=context)

        if "api_key" in error_str or "authentication" in error_str:
            return NoAPIKeyConfiguredError(str(error), context=context)

        if "json" in error_str or "parse" in error_str:
            return InvalidResponseError(str(error), context=context)

        if "circuit" in error_str:
            return CircuitBreakerError(str(error), context=context)

        if "cache" in error_str or "redis" in error_str:
            return CacheError(str(error), context=context)

        # Default to base LLMError
        return LLMError(str(error), context=context)

    def get_error_stats(self) -> dict:
        """Get error statistics"""
        return {
            "counts": dict(self._error_counts),
            "total": sum(self._error_counts.values()),
        }

    def reset_stats(self) -> None:
        """Reset error statistics"""
        self._error_counts.clear()


# Singleton error handler
_error_handler: Optional[LLMErrorHandler] = None


def get_error_handler() -> LLMErrorHandler:
    """Get singleton error handler"""
    global _error_handler
    if _error_handler is None:
        _error_handler = LLMErrorHandler()
    return _error_handler


# Backwards compatibility alias (deprecated)
TimeoutError = LLMTimeoutError
