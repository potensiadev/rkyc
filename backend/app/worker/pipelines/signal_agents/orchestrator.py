"""
Signal Agent Orchestrator - Coordinates 3-Agent parallel execution

Sprint 2: Signal Multi-Agent Architecture (ADR-009)
Sprint 3: Quality & Reliability (Cross-Validation, Graceful Degradation, Concurrency Limit)
Sprint 4: Celery group() distributed execution

Features:
- Parallel execution of DirectSignalAgent, IndustrySignalAgent, EnvironmentSignalAgent
- Signal deduplication across agents
- Cross-validation between agents with conflict detection
- Result merging with conflict resolution
- Graceful degradation on agent failures
- Provider concurrency limits
- Celery group() integration for distributed execution
"""

import asyncio
import logging
import time
import hashlib
import threading
from dataclasses import dataclass, field
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

from app.worker.pipelines.signal_agents.direct_agent import DirectSignalAgent
from app.worker.pipelines.signal_agents.industry_agent import IndustrySignalAgent
from app.worker.pipelines.signal_agents.environment_agent import EnvironmentSignalAgent

logger = logging.getLogger(__name__)


# =============================================================================
# Sprint 3: Data Classes for Enhanced Tracking
# =============================================================================

class AgentStatus(str, Enum):
    """Agent execution status"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class AgentResult:
    """Result from a single agent execution."""
    agent_name: str
    status: AgentStatus
    signals: list[dict] = field(default_factory=list)
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    retry_count: int = 0

    def to_dict(self) -> dict:
        """
        P3-1 Fix: Serialize AgentResult to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "agent_name": self.agent_name,
            "status": self.status.value if isinstance(self.status, AgentStatus) else self.status,
            "signals": list(self.signals),
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "retry_count": self.retry_count,
        }


@dataclass
class CrossValidationResult:
    """Result of cross-validation check."""
    signal: dict
    is_valid: bool
    needs_review: bool = False
    conflict_reason: Optional[str] = None
    conflicting_signals: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """
        P3-2 Fix: Serialize CrossValidationResult to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return {
            "signal": dict(self.signal) if self.signal else {},
            "is_valid": self.is_valid,
            "needs_review": self.needs_review,
            "conflict_reason": self.conflict_reason,
            "conflicting_signals": list(self.conflicting_signals),
        }


@dataclass
class OrchestratorMetadata:
    """Metadata about orchestrator execution"""
    total_raw_signals: int = 0
    deduplicated_count: int = 0
    validated_count: int = 0
    conflicts_detected: int = 0
    needs_review_count: int = 0
    processing_time_ms: int = 0
    partial_failure: bool = False
    failed_agents: list[str] = field(default_factory=list)
    agent_results: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """
        P2-3 Fix: Serialize metadata to dictionary for JSON serialization.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "total_raw_signals": self.total_raw_signals,
            "deduplicated_count": self.deduplicated_count,
            "validated_count": self.validated_count,
            "conflicts_detected": self.conflicts_detected,
            "needs_review_count": self.needs_review_count,
            "processing_time_ms": self.processing_time_ms,
            "partial_failure": self.partial_failure,
            "failed_agents": list(self.failed_agents),
            "agent_results": dict(self.agent_results),
        }


# =============================================================================
# Sprint 3: Provider Concurrency Limiter
# =============================================================================

class ProviderConcurrencyLimiter:
    """
    Manages concurrent access to LLM providers.

    Sprint 3 (ADR-009):
    - Perplexity: 5 concurrent
    - Gemini: 10 concurrent
    - Claude: 3 concurrent

    P0-1 Fix: Thread-safe singleton with _initialized flag
    P0-2 Fix: Release method logs warning for unmatched providers
    """

    _instance = None
    _lock = threading.Lock()
    _init_lock = threading.Lock()  # P0-1: Separate lock for initialization

    # Concurrency limits per provider
    LIMITS = {
        "anthropic": 3,
        "claude": 3,
        "openai": 5,
        "gpt": 5,
        "google": 10,
        "gemini": 10,
        "perplexity": 5,
    }

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False  # P0-1: Flag before full init
                    cls._instance = instance
        return cls._instance

    def _ensure_initialized(self):
        """P0-1 Fix: Thread-safe lazy initialization with double-checked locking."""
        if getattr(self, '_initialized', False):
            return

        with self._init_lock:
            if not getattr(self, '_initialized', False):
                self._do_initialize()
                self._initialized = True

    def _do_initialize(self):
        """Internal initialization logic (called under lock)."""
        self._semaphores = {}
        self._limits = dict(self.LIMITS)  # Copy for API access
        self._default_limit = 5  # Default limit for unknown providers

        for provider, limit in self.LIMITS.items():
            self._semaphores[provider] = threading.Semaphore(limit)

        # Track current usage
        self._usage = {provider: 0 for provider in self.LIMITS}
        self._usage_lock = threading.Lock()

        logger.info(
            f"[ConcurrencyLimiter] Initialized with limits: {self.LIMITS}"
        )

    def _find_provider_key(self, provider: str) -> str | None:
        """Find matching provider key for the given provider name."""
        provider_lower = provider.lower()
        for key in self._semaphores:
            if key in provider_lower or provider_lower in key:
                return key
        return None

    def acquire(self, provider: str, timeout: float = 30.0) -> bool:
        """
        Acquire a slot for the provider.

        Args:
            provider: Provider name (anthropic, openai, google, perplexity)
            timeout: Maximum time to wait for a slot

        Returns:
            True if acquired, False if timeout
        """
        self._ensure_initialized()  # P0-1: Ensure initialized before use

        provider_key = self._find_provider_key(provider)

        if provider_key is None:
            logger.warning(f"[ConcurrencyLimiter] Unknown provider: {provider}")
            return True  # Allow unknown providers

        semaphore = self._semaphores[provider_key]
        acquired = semaphore.acquire(timeout=timeout)

        if acquired:
            with self._usage_lock:
                self._usage[provider_key] += 1
            logger.debug(
                f"[ConcurrencyLimiter] Acquired slot for {provider_key} "
                f"(current: {self._usage[provider_key]}/{self.LIMITS[provider_key]})"
            )
        else:
            logger.warning(
                f"[ConcurrencyLimiter] Timeout acquiring slot for {provider_key}"
            )

        return acquired

    def release(self, provider: str) -> None:
        """
        Release a slot for the provider.

        P3-3 Fix: Enhanced docstring.

        Args:
            provider: Provider name (anthropic, openai, google, perplexity).
                      Must match the name used in acquire().

        Raises:
            No exceptions raised; logs warning if provider not found.
        """
        self._ensure_initialized()  # P0-1: Ensure initialized before use

        provider_key = self._find_provider_key(provider)

        if provider_key is None:
            # P0-2 Fix: Log warning for unmatched provider (potential semaphore leak)
            logger.warning(
                f"[ConcurrencyLimiter] Cannot release - unknown provider: {provider}. "
                f"This may indicate a semaphore leak if acquire() was called with a different name."
            )
            return

        self._semaphores[provider_key].release()
        with self._usage_lock:
            self._usage[provider_key] = max(0, self._usage[provider_key] - 1)
        logger.debug(
            f"[ConcurrencyLimiter] Released slot for {provider_key} "
            f"(current: {self._usage[provider_key]}/{self.LIMITS[provider_key]})"
        )

    def get_usage(self) -> dict:
        """
        Get current usage statistics for all providers.

        P3-3 Fix: Enhanced docstring.

        Returns:
            Dictionary mapping provider names to usage stats:
            {
                "provider_name": {
                    "current": int,   # Currently acquired slots
                    "limit": int,     # Maximum allowed slots
                    "available": int  # Remaining available slots
                }
            }
        """
        self._ensure_initialized()  # P0-1: Ensure initialized before use

        with self._usage_lock:
            return {
                provider: {
                    "current": self._usage[provider],
                    "limit": self.LIMITS[provider],
                    "available": self.LIMITS[provider] - self._usage[provider],
                }
                for provider in self.LIMITS
            }


_concurrency_limiter_lock = threading.Lock()


def get_concurrency_limiter() -> ProviderConcurrencyLimiter:
    """
    Get singleton concurrency limiter instance.

    P2-4 Fix: Thread-safe singleton access with double-checked locking.
    """
    # First check without lock (fast path)
    if ProviderConcurrencyLimiter._instance is not None:
        return ProviderConcurrencyLimiter._instance

    # Acquire lock for instance creation
    with _concurrency_limiter_lock:
        # Double-check after acquiring lock
        if ProviderConcurrencyLimiter._instance is None:
            ProviderConcurrencyLimiter()  # Creates singleton
        return ProviderConcurrencyLimiter._instance


# =============================================================================
# Main Orchestrator Class
# =============================================================================

class SignalAgentOrchestrator:
    """
    Orchestrates parallel execution of 3 signal agents.

    Execution modes:
    1. Local parallel (ThreadPoolExecutor) - for single worker
    2. Celery group (distributed) - for multi-worker setup

    Features (Sprint 2):
    - Deduplication by event_signature
    - Cross-validation for conflicting signals
    - Result merging with agent attribution

    Features (Sprint 3):
    - Enhanced cross-validation with conflict detection
    - Graceful degradation on agent failures
    - Provider concurrency limits
    - needs_review flag for manual review

    Features (Sprint 4):
    - Celery group() distributed execution
    - Agent performance monitoring
    """

    def __init__(
        self,
        parallel_mode: bool = True,
        max_workers: int = 3,
        enable_concurrency_limit: bool = True,
        agent_timeout: float = 60.0,
    ):
        """
        Initialize orchestrator.

        Args:
            parallel_mode: True for parallel execution, False for sequential
            max_workers: Number of parallel workers (default 3 for 3 agents)
            enable_concurrency_limit: Enable provider concurrency limiting
            agent_timeout: Timeout for each agent in seconds
        """
        self.parallel_mode = parallel_mode
        self.max_workers = max_workers
        self.enable_concurrency_limit = enable_concurrency_limit
        self.agent_timeout = agent_timeout

        # Initialize agents
        self.direct_agent = DirectSignalAgent()
        self.industry_agent = IndustrySignalAgent()
        self.environment_agent = EnvironmentSignalAgent()

        # Agent registry for API access
        self._agents = {
            "direct": self.direct_agent,
            "industry": self.industry_agent,
            "environment": self.environment_agent,
        }

        # ThreadPoolExecutor for local parallel execution
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        # Concurrency limiter
        self._concurrency_limiter = (
            get_concurrency_limiter() if enable_concurrency_limit else None
        )

        # Statistics tracking
        self._stats = {
            "total_executions": 0,
            "partial_failures": 0,
            "conflicts_detected": 0,
            "needs_review_count": 0,
        }
        self._stats_lock = threading.Lock()

        logger.info(
            f"SignalAgentOrchestrator initialized: "
            f"parallel_mode={parallel_mode}, max_workers={max_workers}, "
            f"concurrency_limit={enable_concurrency_limit}"
        )

    def execute(self, context: dict) -> tuple[list[dict], OrchestratorMetadata]:
        """
        Execute all 3 agents and merge results.

        Args:
            context: Unified context from ContextPipeline

        Returns:
            Tuple of (validated signals list, orchestrator metadata)
        """
        corp_id = context.get("corp_id", "")
        trace_id = context.get("trace_id", f"orch_{corp_id}_{int(time.time() * 1000)}")
        start_time = time.time()

        metadata = OrchestratorMetadata()

        # P2-5 Fix: Consistent logging with corp_id and trace_id
        logger.info(
            f"[Orchestrator] Starting 3-Agent extraction "
            f"corp_id={corp_id} trace_id={trace_id}"
        )

        # Execute agents (parallel or sequential)
        if self.parallel_mode:
            agent_results = self._execute_parallel_with_graceful_degradation(context)
        else:
            agent_results = self._execute_sequential_with_graceful_degradation(context)

        # Collect all signals and track failures
        all_signals = []
        for agent_name, result in agent_results.items():
            metadata.agent_results[agent_name] = {
                "status": result.status.value,
                "signal_count": len(result.signals),
                "execution_time_ms": result.execution_time_ms,
                "error": result.error_message,
            }

            if result.status == AgentStatus.SUCCESS:
                all_signals.extend(result.signals)
            else:
                metadata.failed_agents.append(agent_name)
                metadata.partial_failure = True

        metadata.total_raw_signals = len(all_signals)

        # Apply DIRECT fallback if needed
        if "direct" in [a.lower() for a in metadata.failed_agents]:
            fallback_signals = self._apply_direct_fallback(context)
            all_signals.extend(fallback_signals)
            logger.info(
                f"[Orchestrator] Applied DIRECT fallback: "
                f"{len(fallback_signals)} rule-based signals"
            )

        # Deduplicate signals
        deduplicated = self._deduplicate_signals(all_signals)
        metadata.deduplicated_count = len(deduplicated)

        # Enhanced cross-validation with conflict detection
        validated, conflicts = self._cross_validate_signals_enhanced(
            deduplicated, context
        )
        metadata.validated_count = len(validated)
        metadata.conflicts_detected = len(conflicts)
        metadata.needs_review_count = sum(
            1 for s in validated if s.get("needs_review", False)
        )

        elapsed_ms = int((time.time() - start_time) * 1000)
        metadata.processing_time_ms = elapsed_ms

        # Update statistics
        with self._stats_lock:
            self._stats["total_executions"] += 1
            if metadata.partial_failure:
                self._stats["partial_failures"] += 1
            self._stats["conflicts_detected"] += metadata.conflicts_detected
            self._stats["needs_review_count"] += metadata.needs_review_count

        # P2-5 Fix: Consistent logging with corp_id and trace_id
        logger.info(
            f"[Orchestrator] Completed "
            f"corp_id={corp_id} trace_id={trace_id} "
            f"total={metadata.total_raw_signals} "
            f"deduplicated={metadata.deduplicated_count} "
            f"validated={metadata.validated_count} "
            f"conflicts={metadata.conflicts_detected} "
            f"needs_review={metadata.needs_review_count} "
            f"partial_failure={metadata.partial_failure} "
            f"elapsed_ms={elapsed_ms}"
        )

        # Add metadata to signals
        for signal in validated:
            signal["orchestrator_metadata"] = {
                "total_raw_signals": metadata.total_raw_signals,
                "deduplicated_count": metadata.deduplicated_count,
                "final_count": metadata.validated_count,
                "processing_time_ms": elapsed_ms,
                "partial_failure": metadata.partial_failure,
                "failed_agents": metadata.failed_agents,
            }

        return validated, metadata

    def _execute_parallel_with_graceful_degradation(
        self,
        context: dict,
    ) -> dict[str, AgentResult]:
        """
        Execute all agents in parallel with graceful degradation.

        Sprint 3: Individual agent failures don't fail the entire pipeline.
        """
        results = {}
        futures = {}

        # Submit all agents
        futures["direct"] = self._executor.submit(
            self._safe_agent_execute_with_tracking,
            self.direct_agent,
            context,
            "direct",
        )
        futures["industry"] = self._executor.submit(
            self._safe_agent_execute_with_tracking,
            self.industry_agent,
            context,
            "industry",
        )
        futures["environment"] = self._executor.submit(
            self._safe_agent_execute_with_tracking,
            self.environment_agent,
            context,
            "environment",
        )

        # Collect results with timeout
        for name, future in futures.items():
            try:
                result = future.result(timeout=self.agent_timeout)
                results[name] = result
            except Exception as e:
                logger.error(f"[Orchestrator] {name}_agent failed: {e}")
                results[name] = AgentResult(
                    agent_name=name,
                    status=AgentStatus.FAILED,
                    error_message=str(e),
                )

        return results

    def _execute_sequential_with_graceful_degradation(
        self,
        context: dict,
    ) -> dict[str, AgentResult]:
        """
        Execute all agents sequentially with graceful degradation.
        """
        results = {}

        for agent_name, agent in [
            ("direct", self.direct_agent),
            ("industry", self.industry_agent),
            ("environment", self.environment_agent),
        ]:
            result = self._safe_agent_execute_with_tracking(
                agent, context, agent_name
            )
            results[agent_name] = result

        return results

    def _safe_agent_execute_with_tracking(
        self,
        agent,
        context: dict,
        agent_name: str,
    ) -> AgentResult:
        """
        Execute agent with tracking and error handling.

        Sprint 3: Enhanced tracking with timing and retry count.
        P1-1 Fix: Properly classify TimeoutError as AgentStatus.TIMEOUT
        """
        start_time = time.time()

        try:
            signals = agent.execute(context)
            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"[Orchestrator] {agent_name}_agent returned "
                f"{len(signals)} signals in {execution_time_ms}ms"
            )

            return AgentResult(
                agent_name=agent_name,
                status=AgentStatus.SUCCESS,
                signals=signals,
                execution_time_ms=execution_time_ms,
            )

        except TimeoutError as e:
            # P1-1 Fix: Classify timeout separately from general failures
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"[Orchestrator] {agent_name}_agent timed out after "
                f"{execution_time_ms}ms: {e}"
            )

            return AgentResult(
                agent_name=agent_name,
                status=AgentStatus.TIMEOUT,
                error_message=f"Timeout: {e}",
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            # P1-1 Fix: Check if exception message indicates timeout
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                logger.warning(
                    f"[Orchestrator] {agent_name}_agent timed out after "
                    f"{execution_time_ms}ms: {e}"
                )
                return AgentResult(
                    agent_name=agent_name,
                    status=AgentStatus.TIMEOUT,
                    error_message=f"Timeout: {e}",
                    execution_time_ms=execution_time_ms,
                )

            logger.error(
                f"[Orchestrator] {agent_name}_agent failed after "
                f"{execution_time_ms}ms: {e}"
            )

            return AgentResult(
                agent_name=agent_name,
                status=AgentStatus.FAILED,
                error_message=str(e),
                execution_time_ms=execution_time_ms,
            )

    def _apply_direct_fallback(self, context: dict) -> list[dict]:
        """
        Apply rule-based fallback for DIRECT signals when agent fails.

        Sprint 3: Graceful degradation - extract critical signals from snapshot.
        """
        fallback_signals = []
        snapshot = context.get("snapshot_json", {})
        corp_id = context.get("corp_id", "")

        if not snapshot:
            return fallback_signals

        # Rule 1: Overdue flag
        credit = snapshot.get("credit", {})
        loan_summary = credit.get("loan_summary", {})

        if loan_summary.get("overdue_flag"):
            fallback_signals.append({
                "signal_type": "DIRECT",
                "event_type": "OVERDUE_FLAG_ON",
                "impact_direction": "RISK",
                "impact_strength": "HIGH",
                "confidence": "HIGH",
                "title": "연체 발생",
                "summary": "내부 데이터에서 연체 플래그가 활성화되었습니다.",
                "evidence": [{
                    "evidence_type": "INTERNAL_FIELD",
                    "ref_type": "SNAPSHOT_KEYPATH",
                    "ref_value": "/credit/loan_summary/overdue_flag",
                    "snippet": "overdue_flag: true",
                }],
                "corp_id": corp_id,
                "extracted_by": "rule_based_fallback",
                "is_fallback": True,
            })

        # Rule 2: Risk grade change
        kyc_status = snapshot.get("corp", {}).get("kyc_status", {})
        risk_grade = kyc_status.get("internal_risk_grade", "")

        if risk_grade in ["HIGH", "CRITICAL"]:
            fallback_signals.append({
                "signal_type": "DIRECT",
                "event_type": "INTERNAL_RISK_GRADE_CHANGE",
                "impact_direction": "RISK",
                "impact_strength": "HIGH" if risk_grade == "CRITICAL" else "MED",
                "confidence": "HIGH",
                "title": f"내부 신용등급 {risk_grade}",
                "summary": f"내부 신용등급이 {risk_grade}로 설정되어 있습니다.",
                "evidence": [{
                    "evidence_type": "INTERNAL_FIELD",
                    "ref_type": "SNAPSHOT_KEYPATH",
                    "ref_value": "/corp/kyc_status/internal_risk_grade",
                    "snippet": f"internal_risk_grade: {risk_grade}",
                }],
                "corp_id": corp_id,
                "extracted_by": "rule_based_fallback",
                "is_fallback": True,
            })

        # Compute signatures for fallback signals
        for signal in fallback_signals:
            signal["event_signature"] = self._compute_signature(signal)

        return fallback_signals

    def _deduplicate_signals(self, signals: list[dict]) -> list[dict]:
        """
        Deduplicate signals by event_signature.

        When duplicates found:
        - Keep the one with higher confidence
        - If same confidence, keep the one with more evidence

        Returns:
            List of unique signals
        """
        signature_map: dict[str, dict] = {}

        for signal in signals:
            sig = signal.get("event_signature", "")

            if not sig:
                # Generate signature if missing
                sig = self._compute_signature(signal)
                signal["event_signature"] = sig

            if sig in signature_map:
                existing = signature_map[sig]

                # Compare and keep better one
                if self._is_better_signal(signal, existing):
                    logger.debug(
                        f"[Orchestrator] Replacing duplicate signal: "
                        f"old={existing.get('extracted_by')}, "
                        f"new={signal.get('extracted_by')}"
                    )
                    signature_map[sig] = signal
                else:
                    logger.debug(
                        f"[Orchestrator] Keeping existing duplicate signal"
                    )
            else:
                signature_map[sig] = signal

        deduplicated = list(signature_map.values())

        if len(signals) != len(deduplicated):
            logger.info(
                f"[Orchestrator] Deduplication: {len(signals)} -> {len(deduplicated)}"
            )

        return deduplicated

    def _is_better_signal(self, new: dict, existing: dict) -> bool:
        """
        Determine if new signal is better than existing.

        P3-3 Fix: Enhanced docstring with Args section.

        Args:
            new: New signal dictionary to compare.
            existing: Existing signal dictionary to compare against.

        Returns:
            True if new signal should replace existing, False otherwise.

        Criteria (in order):
            1. Prefer non-fallback over fallback
            2. Higher confidence (HIGH > MED > LOW)
            3. If same confidence, more evidence items

        P2-2 Fix: Safe handling of missing/invalid confidence values
        """
        # Prefer non-fallback
        new_fallback = new.get("is_fallback", False)
        existing_fallback = existing.get("is_fallback", False)

        if not new_fallback and existing_fallback:
            return True
        if new_fallback and not existing_fallback:
            return False

        # P2-2 Fix: Expanded confidence mapping with safe defaults
        confidence_order = {
            "HIGH": 3,
            "MED": 2,
            "MEDIUM": 2,  # Alternative spelling
            "LOW": 1,
            None: 0,      # Missing value
            "": 0,        # Empty string
        }

        # P2-2 Fix: Safely get confidence with explicit None handling
        new_conf_raw = new.get("confidence")
        existing_conf_raw = existing.get("confidence")

        # Normalize to uppercase if string
        new_conf_key = new_conf_raw.upper() if isinstance(new_conf_raw, str) else new_conf_raw
        existing_conf_key = existing_conf_raw.upper() if isinstance(existing_conf_raw, str) else existing_conf_raw

        new_conf = confidence_order.get(new_conf_key, 0)
        existing_conf = confidence_order.get(existing_conf_key, 0)

        if new_conf > existing_conf:
            return True
        elif new_conf < existing_conf:
            return False

        # Same confidence - compare evidence count
        new_evidence = len(new.get("evidence", []) or [])
        existing_evidence = len(existing.get("evidence", []) or [])

        return new_evidence > existing_evidence

    def _compute_signature(self, signal: dict) -> str:
        """
        Compute event_signature hash for deduplication.

        P3-3 Fix: Enhanced docstring.

        Args:
            signal: Signal dictionary containing signal_type, event_type, and evidence.

        Returns:
            SHA-256 hash string based on signal_type, event_type, and sorted evidence ref_values.
        """
        evidence_refs = sorted([
            ev.get("ref_value", "")
            for ev in signal.get("evidence", [])
        ])

        sig_string = "|".join([
            signal.get("signal_type", ""),
            signal.get("event_type", ""),
            ",".join(evidence_refs),
        ])

        return hashlib.sha256(sig_string.encode()).hexdigest()

    def _cross_validate_signals_enhanced(
        self,
        signals: list[dict],
        context: dict,
    ) -> tuple[list[dict], list[dict]]:
        """
        Enhanced cross-validation with conflict detection.

        Sprint 3: Detect conflicts and flag for manual review.
        P1-4 Fix: Handle empty signals list gracefully

        Validation rules:
        1. DIRECT signals should reference internal data or direct events
        2. INDUSTRY signals should have industry-wide scope
        3. ENVIRONMENT signals should reference policy/regulation sources
        4. Detect similar signals with different classifications

        Returns:
            Tuple of (validated signals, conflicting signals)
        """
        # P1-4 Fix: Early return for empty input
        if not signals:
            logger.debug("[Orchestrator] No signals to cross-validate")
            return [], []

        validated = []
        conflicts = []

        # Group signals by similar content for conflict detection
        content_groups = self._group_signals_by_content(signals)

        for signal in signals:
            signal_type = signal.get("signal_type", "")
            evidence = signal.get("evidence", [])
            title = signal.get("title", "")

            # Check for conflicts with other signals
            conflict_info = self._check_signal_conflicts(
                signal, content_groups, signals
            )

            if conflict_info["has_conflict"]:
                signal["needs_review"] = True
                signal["conflict_reason"] = conflict_info["reason"]
                signal["conflicting_signal_ids"] = conflict_info["conflicting_ids"]
                conflicts.append(signal)

            # Validate based on signal type
            is_valid = False

            if signal_type == "DIRECT":
                # DIRECT should have internal or direct external evidence
                has_valid_evidence = any(
                    ev.get("evidence_type") == "INTERNAL_FIELD"
                    or ev.get("ref_type") == "SNAPSHOT_KEYPATH"
                    for ev in evidence
                ) or len(evidence) > 0

                is_valid = has_valid_evidence
                if not is_valid:
                    logger.warning(
                        f"[Orchestrator] DIRECT signal without valid evidence: "
                        f"{title[:30]}"
                    )

            elif signal_type == "INDUSTRY":
                # INDUSTRY signals should mention industry-wide impact
                summary = signal.get("summary", "").lower()
                has_industry_scope = any(
                    keyword in summary
                    for keyword in ["업종", "산업", "전체", "시장", "업계"]
                )

                is_valid = True  # Accept if passed agent validation
                signal["industry_scope"] = has_industry_scope

                if not has_industry_scope:
                    signal["needs_review"] = True
                    signal["review_reason"] = "Industry scope not clearly stated"

            elif signal_type == "ENVIRONMENT":
                # ENVIRONMENT signals always valid if they passed agent validation
                is_valid = True

                # Check for policy/regulation keywords
                summary = signal.get("summary", "").lower()
                has_policy_ref = any(
                    keyword in summary
                    for keyword in ["정책", "규제", "법", "정부", "규정", "제도"]
                )

                if not has_policy_ref:
                    signal["needs_review"] = True
                    signal["review_reason"] = "Policy reference not clearly stated"

            else:
                logger.warning(
                    f"[Orchestrator] Unknown signal_type: {signal_type}"
                )
                is_valid = False

            if is_valid:
                validated.append(signal)

        return validated, conflicts

    def _group_signals_by_content(
        self,
        signals: list[dict],
    ) -> dict[str, list[dict]]:
        """
        Group signals by similar content for conflict detection.

        Uses title and key evidence to detect similar signals.
        P2-1 Fix: Improved Korean text tokenization
        """
        import re
        groups = {}

        for signal in signals:
            # Create content key from title keywords
            title = signal.get("title", "").lower()

            # P2-1 Fix: Better tokenization for Korean text
            # Split on whitespace, punctuation, and extract Korean character sequences
            # This handles both Korean and English text
            tokens = re.findall(r'[가-힣]+|[a-zA-Z]+|\d+', title)

            # Filter tokens: Korean 2+ chars, English 3+ chars
            words = []
            for token in tokens:
                if re.match(r'^[가-힣]+$', token) and len(token) >= 2:
                    words.append(token)
                elif re.match(r'^[a-zA-Z]+$', token) and len(token) >= 3:
                    words.append(token.lower())

            if not words:
                continue

            # Use first 3 significant words as group key
            group_key = "_".join(sorted(words[:3]))

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(signal)

        return groups

    def _check_signal_conflicts(
        self,
        signal: dict,
        content_groups: dict[str, list[dict]],
        all_signals: list[dict],
    ) -> dict:
        """
        Check if signal conflicts with other signals.

        Conflicts occur when:
        1. Similar content but different signal_type
        2. Same event but different impact_direction
        """
        result = {
            "has_conflict": False,
            "reason": None,
            "conflicting_ids": [],
        }

        title = signal.get("title", "").lower()
        words = [w for w in title.split() if len(w) > 2]

        if not words:
            return result

        group_key = "_".join(sorted(words[:3]))
        similar_signals = content_groups.get(group_key, [])

        for other in similar_signals:
            if other is signal:
                continue

            # Check for signal_type conflict
            if other.get("signal_type") != signal.get("signal_type"):
                result["has_conflict"] = True
                result["reason"] = (
                    f"Same content classified as {signal.get('signal_type')} "
                    f"and {other.get('signal_type')}"
                )
                result["conflicting_ids"].append(
                    other.get("event_signature", "")[:8]
                )

            # Check for impact_direction conflict
            elif other.get("impact_direction") != signal.get("impact_direction"):
                result["has_conflict"] = True
                result["reason"] = (
                    f"Same content with {signal.get('impact_direction')} "
                    f"and {other.get('impact_direction')} impact"
                )
                result["conflicting_ids"].append(
                    other.get("event_signature", "")[:8]
                )

        return result

    def get_stats(self) -> dict:
        """
        Get orchestrator execution statistics.

        P3-3 Fix: Enhanced docstring.

        Returns:
            Dictionary containing:
            - total_executions: Number of execute() calls
            - partial_failures: Number of executions with at least one agent failure
            - conflicts_detected: Total conflicts found during cross-validation
            - needs_review_count: Total signals flagged for manual review
            - concurrency_usage: Current provider concurrency stats (if enabled)
        """
        with self._stats_lock:
            return {
                **self._stats,
                "concurrency_usage": (
                    self._concurrency_limiter.get_usage()
                    if self._concurrency_limiter else None
                ),
            }

    def reset_stats(self) -> None:
        """
        Reset all execution statistics to zero.

        P3-3 Fix: Enhanced docstring.

        Note:
            This does not reset concurrency limiter state.
        """
        with self._stats_lock:
            self._stats = {
                "total_executions": 0,
                "partial_failures": 0,
                "conflicts_detected": 0,
                "needs_review_count": 0,
            }

    def close(self) -> None:
        """
        Cleanup executor resources.

        P3-3 Fix: Enhanced docstring.

        Shuts down the ThreadPoolExecutor without waiting for pending tasks.
        Safe to call multiple times.
        """
        if hasattr(self, '_executor') and self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    # P1-3 Fix: Context manager support for proper resource cleanup
    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - cleanup resources."""
        self.close()
        return False

    def __del__(self):
        """Destructor - ensure executor is shutdown."""
        self.close()


# =============================================================================
# Sprint 4: Celery Tasks for Distributed Execution
# =============================================================================

def create_celery_tasks():
    """
    Create Celery tasks for distributed agent execution.

    This function is called during Celery worker initialization
    to register the agent tasks.

    Usage with Celery group:
        from celery import group
        from app.worker.pipelines.signal_agents.orchestrator import (
            direct_agent_task,
            industry_agent_task,
            environment_agent_task,
        )

        job = group(
            direct_agent_task.s(context),
            industry_agent_task.s(context),
            environment_agent_task.s(context),
        )
        result = job.apply_async()
        signals = result.get(timeout=120)
    """
    from app.worker.celery_app import celery_app

    @celery_app.task(name="signal.direct_agent", bind=True, max_retries=2)
    def direct_agent_task(self, context: dict) -> dict:
        """Celery task for DirectSignalAgent."""
        start_time = time.time()
        try:
            agent = DirectSignalAgent()
            signals = agent.execute(context)
            return {
                "agent": "direct",
                "status": "success",
                "signals": signals,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "retry_count": self.request.retries,  # P1-5 Fix
            }
        except Exception as e:
            logger.error(f"direct_agent_task failed: {e}")
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=5)
            return {
                "agent": "direct",
                "status": "failed",
                "signals": [],
                "error": str(e),
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "retry_count": self.request.retries,  # P1-5 Fix
            }

    @celery_app.task(name="signal.industry_agent", bind=True, max_retries=2)
    def industry_agent_task(self, context: dict) -> dict:
        """Celery task for IndustrySignalAgent."""
        start_time = time.time()
        try:
            agent = IndustrySignalAgent()
            signals = agent.execute(context)
            return {
                "agent": "industry",
                "status": "success",
                "signals": signals,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "retry_count": self.request.retries,  # P1-5 Fix
            }
        except Exception as e:
            logger.error(f"industry_agent_task failed: {e}")
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=5)
            return {
                "agent": "industry",
                "status": "failed",
                "signals": [],
                "error": str(e),
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "retry_count": self.request.retries,  # P1-5 Fix
            }

    @celery_app.task(name="signal.environment_agent", bind=True, max_retries=2)
    def environment_agent_task(self, context: dict) -> dict:
        """Celery task for EnvironmentSignalAgent."""
        start_time = time.time()
        try:
            agent = EnvironmentSignalAgent()
            signals = agent.execute(context)
            return {
                "agent": "environment",
                "status": "success",
                "signals": signals,
                "retry_count": self.request.retries,  # P1-5 Fix
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }
        except Exception as e:
            logger.error(f"environment_agent_task failed: {e}")
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=5)
            return {
                "agent": "environment",
                "status": "failed",
                "signals": [],
                "error": str(e),
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "retry_count": self.request.retries,  # P1-5 Fix
            }

    return direct_agent_task, industry_agent_task, environment_agent_task


def execute_distributed(context: dict, timeout: float = 120.0) -> tuple[list[dict], OrchestratorMetadata]:
    """
    Execute 3-Agent extraction using Celery group for distributed processing.

    Sprint 4: Multi-worker distributed execution.
    P1-7 Fix: Preserve partial results on timeout

    Args:
        context: Unified context from ContextPipeline
        timeout: Maximum time to wait for all agents

    Returns:
        Tuple of (validated signals, metadata)
    """
    from celery import group
    from celery.exceptions import TimeoutError as CeleryTimeoutError
    from app.worker.celery_app import celery_app

    start_time = time.time()
    metadata = OrchestratorMetadata()
    agent_names = ["direct", "industry", "environment"]

    logger.info(
        f"[DistributedOrchestrator] Starting distributed 3-Agent extraction "
        f"for corp_id={context.get('corp_id', '')}"
    )

    # Create task group
    job = group(
        celery_app.signature("signal.direct_agent", args=[context]),
        celery_app.signature("signal.industry_agent", args=[context]),
        celery_app.signature("signal.environment_agent", args=[context]),
    )

    # Execute and wait
    agent_results = []
    try:
        result = job.apply_async()
        agent_results = result.get(timeout=timeout)
    except CeleryTimeoutError as e:
        # P1-7 Fix: Collect partial results from completed tasks
        logger.warning(f"[DistributedOrchestrator] Group timeout, collecting partial results: {e}")
        metadata.partial_failure = True

        # Try to get individual results
        for i, async_result in enumerate(result.results):
            agent_name = agent_names[i]
            try:
                # Short timeout for already-completed tasks
                res = async_result.get(timeout=1.0)
                agent_results.append(res)
                logger.info(f"[DistributedOrchestrator] Retrieved partial result for {agent_name}")
            except Exception:
                # Task not completed
                metadata.failed_agents.append(agent_name)
                logger.warning(f"[DistributedOrchestrator] {agent_name} not completed")

    except Exception as e:
        logger.error(f"[DistributedOrchestrator] Group execution failed: {e}")
        # Return empty result with failure metadata
        metadata.partial_failure = True
        metadata.failed_agents = list(agent_names)
        return [], metadata

    # Process results
    all_signals = []
    for res in agent_results:
        agent_name = res.get("agent", "unknown")
        metadata.agent_results[agent_name] = {
            "status": res.get("status", "unknown"),
            "signal_count": len(res.get("signals", [])),
            "execution_time_ms": res.get("execution_time_ms", 0),
            "error": res.get("error"),
        }

        if res.get("status") == "success":
            all_signals.extend(res.get("signals", []))
        else:
            metadata.failed_agents.append(agent_name)
            metadata.partial_failure = True

    metadata.total_raw_signals = len(all_signals)

    # Use local orchestrator for post-processing
    orchestrator = get_signal_orchestrator()

    # Deduplicate
    deduplicated = orchestrator._deduplicate_signals(all_signals)
    metadata.deduplicated_count = len(deduplicated)

    # Cross-validate
    validated, conflicts = orchestrator._cross_validate_signals_enhanced(
        deduplicated, context
    )
    metadata.validated_count = len(validated)
    metadata.conflicts_detected = len(conflicts)
    metadata.needs_review_count = sum(
        1 for s in validated if s.get("needs_review", False)
    )

    elapsed_ms = int((time.time() - start_time) * 1000)
    metadata.processing_time_ms = elapsed_ms

    logger.info(
        f"[DistributedOrchestrator] Completed: "
        f"total={metadata.total_raw_signals}, "
        f"validated={metadata.validated_count}, "
        f"elapsed={elapsed_ms}ms"
    )

    return validated, metadata


# =============================================================================
# Singleton Management
# =============================================================================

_orchestrator_instance: Optional[SignalAgentOrchestrator] = None


def get_signal_orchestrator() -> SignalAgentOrchestrator:
    """
    Get singleton SignalAgentOrchestrator instance.

    P3-3 Fix: Enhanced docstring.

    Returns:
        SignalAgentOrchestrator: Shared orchestrator instance with default configuration.

    Note:
        Creates a new instance on first call with default settings:
        - parallel_mode=True
        - max_workers=3
        - enable_concurrency_limit=True
        - agent_timeout=30.0 (v2.1: 30초로 단축하여 hang 방지)
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = SignalAgentOrchestrator(
            agent_timeout=30.0  # v2.1: 30초 타임아웃 (hang 방지)
        )
    return _orchestrator_instance


def reset_signal_orchestrator() -> None:
    """
    Reset singleton orchestrator instance.

    P3-3 Fix: Enhanced docstring.

    Primarily used for testing to ensure clean state between tests.
    Closes the existing instance before resetting.
    """
    global _orchestrator_instance
    if _orchestrator_instance:
        _orchestrator_instance.close()
    _orchestrator_instance = None
