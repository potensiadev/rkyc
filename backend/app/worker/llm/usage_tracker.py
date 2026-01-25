"""
LLM Usage Tracker for Cost Monitoring and Analytics

Sprint 1 Enhancement (ADR-009):
- Per-provider usage tracking
- Per-agent usage attribution
- Cost calculation based on token pricing
- Structured logging for Grafana integration
"""

import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """LLM Provider identifiers"""
    CLAUDE = "claude"
    GPT = "gpt"
    GEMINI = "gemini"
    PERPLEXITY = "perplexity"
    OPENAI_EMBEDDING = "openai_embedding"


# Token pricing (USD per 1M tokens) - Updated 2026-01
TOKEN_PRICING = {
    # Claude Opus 4.5
    "claude-opus-4-5-20251101": {"input": 15.0, "output": 75.0},
    # GPT-5.2 Pro
    "gpt-5.2-pro-2025-12-11": {"input": 10.0, "output": 30.0},
    # Gemini 3 Pro Preview
    "gemini/gemini-3-pro-preview": {"input": 2.5, "output": 10.0},
    # Perplexity Sonar Pro
    "sonar-pro": {"input": 3.0, "output": 15.0},
    # OpenAI Embedding
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    # Default fallback
    "default": {"input": 5.0, "output": 15.0},
}


@dataclass
class LLMUsageLog:
    """Single LLM API call usage record"""
    # Identifiers
    trace_id: str
    provider: str
    model: str
    agent_name: str  # Which agent made this call (e.g., "profiling", "signal_direct")

    # Token counts
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Timing
    latency_ms: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Cost
    cost_usd: float = 0.0

    # Context
    corp_id: Optional[str] = None
    job_id: Optional[str] = None
    stage: Optional[str] = None  # Pipeline stage (e.g., "PROFILING", "SIGNAL")

    # Status
    success: bool = True
    error_message: Optional[str] = None

    def calculate_cost(self) -> float:
        """Calculate cost based on token counts and pricing"""
        pricing = TOKEN_PRICING.get(self.model, TOKEN_PRICING["default"])
        input_cost = (self.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.output_tokens / 1_000_000) * pricing["output"]
        self.cost_usd = round(input_cost + output_cost, 6)
        return self.cost_usd

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage"""
        return asdict(self)

    def to_log_line(self) -> str:
        """Format as structured log line for Grafana Loki"""
        return (
            f"llm_usage "
            f"provider={self.provider} "
            f"model={self.model} "
            f"agent={self.agent_name} "
            f"input_tokens={self.input_tokens} "
            f"output_tokens={self.output_tokens} "
            f"latency_ms={self.latency_ms} "
            f"cost_usd={self.cost_usd:.6f} "
            f"success={self.success} "
            f"corp_id={self.corp_id or 'none'} "
            f"job_id={self.job_id or 'none'} "
            f"stage={self.stage or 'none'}"
        )


@dataclass
class UsageSummary:
    """Aggregated usage statistics"""
    period_start: str
    period_end: str

    # Totals
    total_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0

    # By provider
    by_provider: dict = field(default_factory=dict)

    # By agent
    by_agent: dict = field(default_factory=dict)

    # By stage
    by_stage: dict = field(default_factory=dict)

    # Success rate
    success_count: int = 0
    failure_count: int = 0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_calls if self.total_calls > 0 else 0.0


class LLMUsageTracker:
    """
    Centralized LLM usage tracking

    Features:
    - Real-time usage logging
    - In-memory aggregation
    - Periodic summary generation
    - Thread-safe operations
    """

    def __init__(self, max_history: int = 10000):
        self._lock = threading.Lock()
        self._usage_logs: list[LLMUsageLog] = []
        self._max_history = max_history

        # Running totals for quick access
        self._totals = {
            "calls": 0,
            "tokens": 0,
            "cost_usd": 0.0,
        }

        # Per-provider stats
        self._provider_stats = defaultdict(lambda: {
            "calls": 0, "tokens": 0, "cost_usd": 0.0, "errors": 0
        })

        # Per-agent stats
        self._agent_stats = defaultdict(lambda: {
            "calls": 0, "tokens": 0, "cost_usd": 0.0
        })

        logger.info("[UsageTracker] Initialized with max_history=%d", max_history)

    def log_usage(
        self,
        provider: str,
        model: str,
        agent_name: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        trace_id: Optional[str] = None,
        corp_id: Optional[str] = None,
        job_id: Optional[str] = None,
        stage: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> LLMUsageLog:
        """
        Log a single LLM API call

        Args:
            provider: LLM provider (claude, gpt, gemini, perplexity)
            model: Model identifier
            agent_name: Which agent made this call
            input_tokens: Input token count
            output_tokens: Output token count
            latency_ms: Response latency in milliseconds
            trace_id: Optional trace ID for correlation
            corp_id: Optional corporation ID
            job_id: Optional job ID
            stage: Optional pipeline stage
            success: Whether the call succeeded
            error_message: Error message if failed

        Returns:
            LLMUsageLog: The created usage log
        """
        # Create log entry
        log = LLMUsageLog(
            trace_id=trace_id or f"{provider}_{int(time.time() * 1000)}",
            provider=provider,
            model=model,
            agent_name=agent_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=latency_ms,
            corp_id=corp_id,
            job_id=job_id,
            stage=stage,
            success=success,
            error_message=error_message,
        )

        # Calculate cost
        log.calculate_cost()

        # Thread-safe update
        with self._lock:
            # Store log
            self._usage_logs.append(log)

            # Trim history if needed
            if len(self._usage_logs) > self._max_history:
                self._usage_logs = self._usage_logs[-self._max_history:]

            # Update totals
            self._totals["calls"] += 1
            self._totals["tokens"] += log.total_tokens
            self._totals["cost_usd"] += log.cost_usd

            # Update provider stats
            self._provider_stats[provider]["calls"] += 1
            self._provider_stats[provider]["tokens"] += log.total_tokens
            self._provider_stats[provider]["cost_usd"] += log.cost_usd
            if not success:
                self._provider_stats[provider]["errors"] += 1

            # Update agent stats
            self._agent_stats[agent_name]["calls"] += 1
            self._agent_stats[agent_name]["tokens"] += log.total_tokens
            self._agent_stats[agent_name]["cost_usd"] += log.cost_usd

        # Log to standard logger for Grafana/Loki
        if success:
            logger.info(log.to_log_line())
        else:
            logger.warning(log.to_log_line())

        return log

    def get_summary(self, last_n_minutes: int = 60) -> UsageSummary:
        """
        Get usage summary for the specified time period

        Args:
            last_n_minutes: Time window in minutes

        Returns:
            UsageSummary: Aggregated statistics

        P1-6 Fix: Use datetime parsing for proper timestamp comparison
        """
        cutoff_dt = datetime.now() - timedelta(minutes=last_n_minutes)
        cutoff_iso = cutoff_dt.isoformat()

        summary = UsageSummary(
            period_start=cutoff_iso,
            period_end=datetime.now().isoformat(),
        )

        by_provider = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost_usd": 0.0})
        by_agent = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost_usd": 0.0})
        by_stage = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost_usd": 0.0})

        with self._lock:
            for log in self._usage_logs:
                # P1-6 Fix: Parse timestamp for proper datetime comparison
                try:
                    log_dt = datetime.fromisoformat(log.timestamp)
                    if log_dt < cutoff_dt:
                        continue
                except (ValueError, TypeError):
                    # Fallback to string comparison if parsing fails
                    if log.timestamp < cutoff_iso:
                        continue

                # Aggregate stats for logs within time window
                summary.total_calls += 1
                summary.total_tokens += log.total_tokens
                summary.total_cost_usd += log.cost_usd
                summary.total_latency_ms += log.latency_ms

                if log.success:
                    summary.success_count += 1
                else:
                    summary.failure_count += 1

                by_provider[log.provider]["calls"] += 1
                by_provider[log.provider]["tokens"] += log.total_tokens
                by_provider[log.provider]["cost_usd"] += log.cost_usd

                by_agent[log.agent_name]["calls"] += 1
                by_agent[log.agent_name]["tokens"] += log.total_tokens
                by_agent[log.agent_name]["cost_usd"] += log.cost_usd

                if log.stage:
                    by_stage[log.stage]["calls"] += 1
                    by_stage[log.stage]["tokens"] += log.total_tokens
                    by_stage[log.stage]["cost_usd"] += log.cost_usd

        summary.by_provider = dict(by_provider)
        summary.by_agent = dict(by_agent)
        summary.by_stage = dict(by_stage)

        return summary

    def get_totals(self) -> dict:
        """Get running totals"""
        with self._lock:
            return {
                **self._totals,
                "by_provider": dict(self._provider_stats),
                "by_agent": dict(self._agent_stats),
            }

    def reset(self):
        """Reset all counters (for testing)"""
        with self._lock:
            self._usage_logs.clear()
            self._totals = {"calls": 0, "tokens": 0, "cost_usd": 0.0}
            self._provider_stats.clear()
            self._agent_stats.clear()
        logger.info("[UsageTracker] Reset all counters")


# Singleton instance with thread-safe initialization (P1-2 Fix)
_tracker_instance: Optional[LLMUsageTracker] = None
_tracker_lock = threading.Lock()


def get_usage_tracker() -> LLMUsageTracker:
    """
    Get singleton usage tracker instance.

    P1-2 Fix: Thread-safe singleton with double-checked locking
    """
    global _tracker_instance
    if _tracker_instance is None:
        with _tracker_lock:
            # Double-check after acquiring lock
            if _tracker_instance is None:
                _tracker_instance = LLMUsageTracker()
    return _tracker_instance


def reset_usage_tracker():
    """Reset singleton instance (for testing)"""
    global _tracker_instance
    with _tracker_lock:
        if _tracker_instance:
            _tracker_instance.reset()
        _tracker_instance = None


# Convenience function for logging
def log_llm_usage(
    provider: str,
    model: str,
    agent_name: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    **kwargs,
) -> LLMUsageLog:
    """
    Convenience function to log LLM usage

    Example:
        log_llm_usage(
            provider="claude",
            model="claude-opus-4-5-20251101",
            agent_name="profiling",
            input_tokens=1500,
            output_tokens=800,
            latency_ms=2500,
            corp_id="8001-3719240",
            job_id="job-123",
            stage="PROFILING",
        )
    """
    tracker = get_usage_tracker()
    return tracker.log_usage(
        provider=provider,
        model=model,
        agent_name=agent_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        **kwargs,
    )
