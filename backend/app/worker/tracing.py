"""
Structured Logging & Distributed Tracing for rKYC

Phase 1 구현:
- trace_id 기반 분산 추적
- JSON 구조화 로그
- 컴포넌트별 로거

P2-1 (OpenTelemetry 스타일):
- Span 기반 추적
- 자동 span 계층 구조
- Console + JSON 출력

Usage:
    from app.worker.tracing import get_logger, TracingContext, Span

    # 새 트레이스 시작
    trace_id = TracingContext.new_trace()

    # 로거 사용
    logger = get_logger("SignalAgent")
    logger.info("signal_extraction_start", corp_id="8001-3719240", doc_count=5)

    # Span 사용 (P2-1)
    with Span("llm_call", provider="anthropic") as span:
        result = llm.call(...)
        span.set_attribute("tokens_used", 1500)
"""

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Optional, Generator
from enum import Enum

# Context variable for trace ID (thread-safe, async-safe)
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
_job_id_var: ContextVar[str] = ContextVar("job_id", default="")
_corp_id_var: ContextVar[str] = ContextVar("corp_id", default="")


class TracingContext:
    """분산 추적 컨텍스트 관리"""

    @staticmethod
    def new_trace() -> str:
        """새 trace_id 생성 및 설정"""
        trace_id = str(uuid.uuid4())[:8]
        _trace_id_var.set(trace_id)
        return trace_id

    @staticmethod
    def get_trace_id() -> str:
        """현재 trace_id 반환"""
        return _trace_id_var.get() or "no-trace"

    @staticmethod
    def set_trace_id(trace_id: str) -> None:
        """trace_id 설정 (기존 트레이스 이어받기)"""
        _trace_id_var.set(trace_id)

    @staticmethod
    def set_job_context(job_id: str, corp_id: str = None) -> None:
        """Job 컨텍스트 설정"""
        _job_id_var.set(job_id)
        if corp_id:
            _corp_id_var.set(corp_id)

    @staticmethod
    def get_job_id() -> str:
        """현재 job_id 반환"""
        return _job_id_var.get()

    @staticmethod
    def get_corp_id() -> str:
        """현재 corp_id 반환"""
        return _corp_id_var.get()

    @staticmethod
    def clear() -> None:
        """컨텍스트 초기화"""
        _trace_id_var.set("")
        _job_id_var.set("")
        _corp_id_var.set("")


# ============================================================================
# P2-1: OpenTelemetry-style Span Tracking
# ============================================================================

# Context variable for current span
_current_span_var: ContextVar[Optional["Span"]] = ContextVar("current_span", default=None)


class SpanStatus(str, Enum):
    """Span status (OpenTelemetry compatible)"""
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class SpanContext:
    """Span context for propagation"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None


@dataclass
class SpanData:
    """Recorded span data"""
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    start_time: str
    end_time: Optional[str]
    duration_ms: Optional[int]
    status: SpanStatus
    attributes: dict
    events: list
    component: Optional[str] = None


class Span:
    """
    OpenTelemetry-style Span for tracing.

    Usage:
        with Span("operation_name", component="LLMService") as span:
            span.set_attribute("key", "value")
            span.add_event("checkpoint", {"data": 123})
            # ... do work ...

    Features:
    - Automatic parent-child relationship
    - Duration tracking
    - Attribute and event recording
    - JSON log output on completion
    """

    def __init__(
        self,
        name: str,
        component: Optional[str] = None,
        parent: Optional["Span"] = None,
        **initial_attributes,
    ):
        self.name = name
        self.component = component
        self.span_id = str(uuid.uuid4())[:8]
        self.trace_id = TracingContext.get_trace_id() or TracingContext.new_trace()

        # Parent span (explicit or from context)
        if parent:
            self.parent_span_id = parent.span_id
        else:
            current_span = _current_span_var.get()
            self.parent_span_id = current_span.span_id if current_span else None

        self.start_time = datetime.now(UTC)
        self.end_time: Optional[datetime] = None
        self.status = SpanStatus.UNSET
        self.attributes: dict[str, Any] = dict(initial_attributes)
        self.events: list[dict] = []
        self._previous_span: Optional["Span"] = None
        self._logger = get_logger(component or "Span")

    def set_attribute(self, key: str, value: Any) -> "Span":
        """Set a span attribute"""
        self.attributes[key] = value
        return self

    def set_attributes(self, attributes: dict[str, Any]) -> "Span":
        """Set multiple span attributes"""
        self.attributes.update(attributes)
        return self

    def add_event(self, name: str, attributes: Optional[dict] = None) -> "Span":
        """Add an event to the span"""
        self.events.append({
            "name": name,
            "timestamp": datetime.now(UTC).isoformat(),
            "attributes": attributes or {},
        })
        return self

    def set_status(self, status: SpanStatus, description: Optional[str] = None) -> "Span":
        """Set the span status"""
        self.status = status
        if description:
            self.attributes["status_description"] = description
        return self

    def record_exception(self, exception: Exception) -> "Span":
        """Record an exception on the span"""
        self.status = SpanStatus.ERROR
        self.add_event("exception", {
            "type": type(exception).__name__,
            "message": str(exception),
        })
        self.attributes["error"] = True
        self.attributes["error_type"] = type(exception).__name__
        self.attributes["error_message"] = str(exception)
        return self

    def get_context(self) -> SpanContext:
        """Get span context for propagation"""
        return SpanContext(
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
        )

    def to_dict(self) -> dict:
        """Convert span to dictionary for logging"""
        duration_ms = None
        if self.end_time and self.start_time:
            duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)

        return {
            "span_name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": duration_ms,
            "status": self.status.value,
            "component": self.component,
            "attributes": self.attributes,
            "events": self.events,
        }

    def __enter__(self) -> "Span":
        """Enter span context"""
        self._previous_span = _current_span_var.get()
        _current_span_var.set(self)
        self._logger.debug(
            f"span_start:{self.name}",
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit span context"""
        self.end_time = datetime.now(UTC)

        if exc_type:
            self.record_exception(exc_val)
        elif self.status == SpanStatus.UNSET:
            self.status = SpanStatus.OK

        # Log span completion
        span_data = self.to_dict()
        if self.status == SpanStatus.ERROR:
            self._logger.error(f"span_end:{self.name}", **span_data)
        else:
            self._logger.info(f"span_end:{self.name}", **span_data)

        # Restore previous span
        _current_span_var.set(self._previous_span)

        return False  # Don't suppress exceptions


def get_current_span() -> Optional[Span]:
    """Get the current active span"""
    return _current_span_var.get()


@contextmanager
def start_span(
    name: str,
    component: Optional[str] = None,
    **attributes,
) -> Generator[Span, None, None]:
    """
    Convenience function to start a new span.

    Usage:
        with start_span("my_operation", provider="anthropic") as span:
            ...
    """
    span = Span(name, component=component, **attributes)
    with span:
        yield span


class JSONLogFormatter(logging.Formatter):
    """JSON 형식 로그 포맷터"""

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 형식으로 변환"""
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "trace_id": TracingContext.get_trace_id(),
            "component": getattr(record, "component", record.name),
            "event": getattr(record, "event", record.getMessage()),
        }

        # Job 컨텍스트 추가
        job_id = TracingContext.get_job_id()
        if job_id:
            log_entry["job_id"] = job_id

        corp_id = TracingContext.get_corp_id()
        if corp_id:
            log_entry["corp_id"] = corp_id

        # 추가 필드 (extra kwargs)
        extra_fields = getattr(record, "extra_fields", {})
        if extra_fields:
            log_entry.update(extra_fields)

        # 에러 정보 추가
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class StructuredLogger:
    """구조화된 로거 래퍼"""

    def __init__(self, component: str, logger: logging.Logger = None):
        """
        Args:
            component: 컴포넌트 이름 (예: "SignalAgent", "LLMService")
            logger: 기존 로거 (None이면 새로 생성)
        """
        self.component = component
        self._logger = logger or logging.getLogger(f"rkyc.{component}")

    def _log(self, level: int, event: str, **kwargs) -> None:
        """공통 로깅 메서드"""
        extra = {
            "component": self.component,
            "event": event,
            "extra_fields": kwargs,
        }
        self._logger.log(level, event, extra=extra)

    def debug(self, event: str, **kwargs) -> None:
        """DEBUG 레벨 로그"""
        self._log(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs) -> None:
        """INFO 레벨 로그"""
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs) -> None:
        """WARNING 레벨 로그"""
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, exc_info: bool = False, **kwargs) -> None:
        """ERROR 레벨 로그"""
        extra = {
            "component": self.component,
            "event": event,
            "extra_fields": kwargs,
        }
        self._logger.error(event, extra=extra, exc_info=exc_info)

    def critical(self, event: str, exc_info: bool = False, **kwargs) -> None:
        """CRITICAL 레벨 로그"""
        extra = {
            "component": self.component,
            "event": event,
            "extra_fields": kwargs,
        }
        self._logger.critical(event, extra=extra, exc_info=exc_info)

    # Timing helpers
    def timed_operation(self, operation: str):
        """시간 측정 컨텍스트 매니저"""
        return TimedOperation(self, operation)


class TimedOperation:
    """작업 시간 측정 컨텍스트 매니저"""

    def __init__(self, logger: StructuredLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time: Optional[float] = None

    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.debug(f"{self.operation}_start")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        elapsed_ms = int((time.time() - self.start_time) * 1000)

        if exc_type:
            self.logger.error(
                f"{self.operation}_failed",
                elapsed_ms=elapsed_ms,
                error=str(exc_val),
                exc_info=True,
            )
        else:
            self.logger.info(
                f"{self.operation}_complete",
                elapsed_ms=elapsed_ms,
            )

        return False  # Don't suppress exceptions


# Logger cache
_loggers: dict[str, StructuredLogger] = {}
_setup_done = False


def setup_structured_logging(
    level: str = "INFO",
    json_output: bool = True,
) -> None:
    """
    구조화된 로깅 설정

    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
        json_output: JSON 형식 출력 여부
    """
    global _setup_done

    if _setup_done:
        return

    # Root logger 설정
    root_logger = logging.getLogger("rkyc")
    root_logger.setLevel(getattr(logging, level.upper()))

    # 기존 핸들러 제거
    root_logger.handlers.clear()

    # 핸들러 추가
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    if json_output:
        handler.setFormatter(JSONLogFormatter())
    else:
        # 기본 텍스트 포맷 (개발용)
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        ))

    root_logger.addHandler(handler)

    # 다른 라이브러리 로그 레벨 조정
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.WARNING)

    _setup_done = True


def get_logger(component: str) -> StructuredLogger:
    """
    컴포넌트별 로거 반환 (싱글톤)

    Args:
        component: 컴포넌트 이름

    Returns:
        StructuredLogger 인스턴스
    """
    if component not in _loggers:
        _loggers[component] = StructuredLogger(component)

    return _loggers[component]


# 자주 사용되는 이벤트 상수
class LogEvents:
    """표준화된 로그 이벤트 이름"""

    # LLM 관련
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_SUCCESS = "llm_call_success"
    LLM_CALL_FAILED = "llm_call_failed"
    LLM_FALLBACK = "llm_fallback"
    LLM_CACHE_HIT = "llm_cache_hit"
    LLM_CACHE_MISS = "llm_cache_miss"

    # Agent 관련
    AGENT_START = "agent_start"
    AGENT_SUCCESS = "agent_success"
    AGENT_FAILED = "agent_failed"
    AGENT_TIMEOUT = "agent_timeout"
    AGENT_SKIPPED = "agent_skipped"

    # Pipeline 관련
    PIPELINE_START = "pipeline_start"
    PIPELINE_PHASE_START = "pipeline_phase_start"
    PIPELINE_PHASE_COMPLETE = "pipeline_phase_complete"
    PIPELINE_COMPLETE = "pipeline_complete"
    PIPELINE_FAILED = "pipeline_failed"

    # Consensus 관련
    CONSENSUS_START = "consensus_start"
    CONSENSUS_MATCH = "consensus_match"
    CONSENSUS_DISCREPANCY = "consensus_discrepancy"
    CONSENSUS_COMPLETE = "consensus_complete"

    # Cache 관련
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_SET = "cache_set"
    CACHE_INVALIDATE = "cache_invalidate"

    # P2-1: Span 관련
    SPAN_START = "span_start"
    SPAN_END = "span_end"
    SPAN_ERROR = "span_error"
    SPAN_EVENT = "span_event"

    # Circuit Breaker 관련
    CIRCUIT_OPEN = "circuit_open"
    CIRCUIT_CLOSE = "circuit_close"
    CIRCUIT_HALF_OPEN = "circuit_half_open"
    CIRCUIT_REJECTED = "circuit_rejected"

    # Orchestrator 관련
    ORCHESTRATOR_START = "orchestrator_start"
    ORCHESTRATOR_LAYER_START = "orchestrator_layer_start"
    ORCHESTRATOR_LAYER_SUCCESS = "orchestrator_layer_success"
    ORCHESTRATOR_LAYER_FAILED = "orchestrator_layer_failed"
    ORCHESTRATOR_COMPLETE = "orchestrator_complete"
    ORCHESTRATOR_DEGRADATION = "orchestrator_degradation"
