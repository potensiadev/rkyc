"""
Multi-Agent Orchestrator for Corp Profiling Pipeline

PRD v1.2 4-Layer Fallback Architecture:
- Layer 0: Profile Cache (exact match)
- Layer 1: Perplexity Search (with citation verification)
- Layer 1.5: Gemini Validation (cross-validation, enrichment)
- Layer 2: Consensus Engine (multi-source synthesis)
- Layer 3: Rule-Based Merge (deterministic fallback)
- Layer 4: Graceful Degradation (최소 프로필 + 경고)

Anti-Hallucination 4-Layer Defense:
- Source Verification (Perplexity citations)
- Extraction Guardrails (confidence scoring)
- Validation Layer (Gemini cross-check)
- Audit Trail (full provenance)

Sprint 1 Enhancement (ADR-009):
- Parallel Perplexity + Gemini execution using asyncio
- 25% speedup target (40s → 30s)
"""

import asyncio
import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Callable
from uuid import uuid4

from app.worker.llm.circuit_breaker import (
    CircuitBreakerManager,
    CircuitOpenError,
    get_circuit_breaker_manager,
)
from app.worker.llm.consensus_engine import (
    ConsensusEngine,
    ConsensusMetadata,
    get_consensus_engine,
)
from app.worker.llm.gemini_adapter import GeminiAdapter, get_gemini_adapter
from app.worker.llm.exceptions import AllProvidersFailedError
from app.worker.llm.search_providers import (
    MultiSearchManager,
    SearchResult,
    SearchProviderType,
    GeminiGroundingProvider,
    get_multi_search_manager,
)

logger = logging.getLogger(__name__)

# P0 Fix: Thread-safe event loop 관리
import threading
_thread_local = threading.local()
_event_loop_lock = threading.Lock()


def _get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """
    P0 Fix: Thread-safe event loop 관리 (TOCTOU 방지)

    스레드별로 독립된 event loop를 관리하여 race condition 방지.
    Lock으로 is_closed() 체크와 사용 사이의 경쟁 조건 방지.
    """
    # 먼저 running loop 확인 (이미 async 컨텍스트인 경우)
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        pass

    # Thread-local storage에서 안전하게 loop 관리 (Lock으로 TOCTOU 방지)
    with _event_loop_lock:
        if hasattr(_thread_local, 'loop') and _thread_local.loop is not None:
            if not _thread_local.loop.is_closed():
                return _thread_local.loop

        # 새 loop 생성 및 저장
        loop = asyncio.new_event_loop()
        _thread_local.loop = loop
        return loop


class FallbackLayer(str, Enum):
    """Fallback Layer 식별자"""
    CACHE = "CACHE"
    PERPLEXITY_GEMINI = "PERPLEXITY_GEMINI"
    CLAUDE_SYNTHESIS = "CLAUDE_SYNTHESIS"
    RULE_BASED = "RULE_BASED"
    GRACEFUL_DEGRADATION = "GRACEFUL_DEGRADATION"


@dataclass
class OrchestratorResult:
    """Orchestrator 실행 결과"""
    profile: dict
    fallback_layer: FallbackLayer
    retry_count: int
    error_messages: list[str]
    consensus_metadata: Optional[ConsensusMetadata] = None
    provenance: dict = field(default_factory=dict)
    execution_time_ms: int = 0
    trace_id: str = ""  # P2-2: 분산 추적용 Trace ID
    source_map: dict = field(default_factory=dict)  # 필드별 출처 추적: {"revenue_krw": "PERPLEXITY", ...}
    layer1_both_failed: bool = False  # Layer 1 둘 다 실패 플래그

    def to_dict(self) -> dict:
        """결과를 딕셔너리로 변환"""
        return {
            "profile": self.profile,
            "fallback_layer": self.fallback_layer.value,
            "retry_count": self.retry_count,
            "error_messages": self.error_messages,
            "consensus_metadata": self.consensus_metadata.to_dict() if self.consensus_metadata else None,
            "provenance": self.provenance,
            "execution_time_ms": self.execution_time_ms,
            "trace_id": self.trace_id,
            "source_map": self.source_map,
            "layer1_both_failed": self.layer1_both_failed,
        }


@dataclass
class RuleBasedMergeConfig:
    """Rule-Based Merge 설정"""
    # 필드 우선순위 (높을수록 우선)
    source_priority: dict = field(default_factory=lambda: {
        "PERPLEXITY_VERIFIED": 100,
        "GEMINI_VALIDATED": 90,
        "CLAUDE_SYNTHESIZED": 80,
        "GEMINI_INFERRED": 50,
        "RULE_BASED": 30,
        "UNKNOWN": 10,
    })

    # 필수 필드 목록 (graceful degradation에서도 포함)
    required_fields: list[str] = field(default_factory=lambda: [
        "corp_name",
        "industry_code",
        "industry_name",
    ])

    # 숫자 필드 (범위 검증)
    numeric_fields: list[str] = field(default_factory=lambda: [
        "export_ratio",
        "domestic_ratio",
        "employee_count",
        "major_shareholder_ratio",
    ])

    # 비율 필드 (0-100% 범위)
    ratio_fields: list[str] = field(default_factory=lambda: [
        "export_ratio",
        "domestic_ratio",
        "major_shareholder_ratio",
    ])


class MultiAgentOrchestrator:
    """
    Multi-Agent Orchestrator

    4-Layer Fallback을 조율하며, Circuit Breaker와 통합됨.

    실행 순서 (v2.0 - 순차 Fallback):
    1. Cache 확인 (Layer 0)
    2. Perplexity 검색 (Layer 1) - Primary Search
    3. Gemini 검색 (Layer 1.5) - Perplexity 실패 시에만 Fallback
    4. OpenAI 검증 (Layer 2) - Validation (검색 아님)
    5. Rule-Based Merge (Layer 3)
    6. Graceful Degradation (Layer 4)

    v2.0 핵심 변경:
    - Perplexity 성공하면 Gemini 호출 안 함 (비용 절약)
    - Perplexity 실패 시에만 Gemini 시도
    - OpenAI는 검증 전용 (검색 기능 없음)
    - 타임아웃 30초로 단축
    """

    # Provider별 동시 요청 제한 (Rate Limit 보호)
    PROVIDER_CONCURRENCY_LIMITS = {
        "perplexity": 5,
        "gemini": 10,
        "claude": 3,
        "openai": 5,
    }

    # v2.0: 타임아웃 설정 (초)
    TIMEOUT_PERPLEXITY = 30  # 기존 45초에서 단축
    TIMEOUT_GEMINI = 30
    TIMEOUT_OPENAI_VALIDATION = 15

    # v2.0: 성공 판정 기준 (필드 수)
    MIN_FIELDS_FULL_SUCCESS = 15  # 완전 성공
    MIN_FIELDS_PARTIAL_SUCCESS = 5  # 부분 성공

    def __init__(
        self,
        circuit_breaker_manager: Optional[CircuitBreakerManager] = None,
        consensus_engine: Optional[ConsensusEngine] = None,
        gemini_adapter: Optional[GeminiAdapter] = None,
        rule_config: Optional[RuleBasedMergeConfig] = None,
        max_workers: int = 4,
    ):
        self.circuit_breaker = circuit_breaker_manager or get_circuit_breaker_manager()
        self.consensus_engine = consensus_engine or get_consensus_engine()
        self.gemini = gemini_adapter or get_gemini_adapter()
        self.rule_config = rule_config or RuleBasedMergeConfig()

        # Thread pool for parallel execution (ADR-009)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        # Perplexity search function will be injected
        self._perplexity_search_fn: Optional[Callable] = None
        self._claude_synthesis_fn: Optional[Callable] = None
        self._cache_lookup_fn: Optional[Callable] = None

        # Gemini parallel search function (optional, for Layer 1 parallel mode)
        self._gemini_search_fn: Optional[Callable] = None

        # Multi-Search Manager for Perplexity fallback (대안 검색 Provider)
        self._multi_search_manager: Optional[MultiSearchManager] = None
        self._use_multi_search: bool = False  # 활성화 시 Perplexity 실패 시 대안 Provider 시도

        # Parallel mode flag (default: True - Perplexity + Gemini 병렬 검색)
        self.parallel_mode = True

        # v2.0: OpenAI Validation function
        self._openai_validation_fn: Optional[Callable] = None

        # Shutdown flag
        self._shutdown = False

    def __del__(self):
        """리소스 정리 - ThreadPoolExecutor shutdown"""
        self.shutdown()

    def shutdown(self):
        """ThreadPoolExecutor 안전하게 종료"""
        if not self._shutdown and self._executor:
            try:
                self._executor.shutdown(wait=False)
                self._shutdown = True
                logger.debug("[Orchestrator] ThreadPoolExecutor shutdown completed")
            except Exception as e:
                logger.warning(f"[Orchestrator] ThreadPoolExecutor shutdown error: {e}")

    def set_perplexity_search(self, fn: Callable):
        """Perplexity 검색 함수 주입"""
        self._perplexity_search_fn = fn

    def set_claude_synthesis(self, fn: Callable):
        """Claude 합성 함수 주입"""
        self._claude_synthesis_fn = fn

    def set_cache_lookup(self, fn: Callable):
        """캐시 조회 함수 주입"""
        self._cache_lookup_fn = fn

    def set_gemini_search(self, fn: Callable):
        """Gemini 검색 함수 주입 (Fallback 모드용)"""
        self._gemini_search_fn = fn

    def set_openai_validation(self, fn: Callable):
        """OpenAI 검증 함수 주입 (v2.0 Layer 2)"""
        self._openai_validation_fn = fn

    def set_multi_search_manager(self, manager: MultiSearchManager, use_as_fallback: bool = True):
        """
        Multi-Search Manager 설정

        Args:
            manager: MultiSearchManager 인스턴스
            use_as_fallback: True면 Perplexity 실패 시에만 사용 (기본값)
                             False면 항상 MultiSearchManager 사용
        """
        self._multi_search_manager = manager
        self._use_multi_search = True
        logger.info(f"[Orchestrator] MultiSearchManager configured (fallback_mode={use_as_fallback})")

    def enable_multi_search(self, enabled: bool = True):
        """Multi-Search 모드 활성화/비활성화"""
        self._use_multi_search = enabled
        if enabled and not self._multi_search_manager:
            self._multi_search_manager = get_multi_search_manager()
        logger.info(f"[Orchestrator] Multi-search mode: {enabled}")

    def set_parallel_mode(self, enabled: bool):
        """병렬 실행 모드 설정"""
        self.parallel_mode = enabled
        logger.info(f"[Orchestrator] Parallel mode: {enabled}")

    def execute(
        self,
        corp_name: str,
        industry_name: str,
        industry_code: str,
        existing_profile: Optional[dict] = None,
        skip_cache: bool = False,
    ) -> OrchestratorResult:
        """
        4-Layer Fallback 실행

        Args:
            corp_name: 기업명
            industry_name: 업종명
            industry_code: 업종코드
            existing_profile: 기존 프로필 (있으면 보완용)
            skip_cache: True면 캐시 무시하고 항상 새로 검색

        Returns:
            OrchestratorResult: 실행 결과 (프로필, fallback layer, 메타데이터)
        """
        start_time = time.time()
        error_messages = []
        retry_count = 0

        # P2-2: Trace ID 생성 (corp_name + timestamp 기반 해시)
        trace_seed = f"{corp_name}:{industry_code}:{time.time_ns()}"
        trace_id = hashlib.md5(trace_seed.encode()).hexdigest()[:12]
        logger.info(f"[Orchestrator][{trace_id}] Starting execution for {corp_name} ({industry_code})")

        provenance = {
            "trace_id": trace_id,
            "started_at": datetime.now().isoformat(),
            "corp_name": corp_name,
            "industry_code": industry_code,
            "layers_attempted": [],
            "skip_cache": skip_cache,
        }

        # Layer 0: Cache (skip if force refresh)
        # P0-2 Fix: existing_profile이 이미 전달되었으면 캐시 히트로 처리 (더블 조회 방지)
        if skip_cache:
            logger.info(f"[Orchestrator] Cache skipped (force refresh) for {corp_name}")
            provenance["cache_skipped"] = True
            cached_profile = None
        elif existing_profile:
            # P0-2: 호출자가 이미 캐시를 조회해서 전달함 -> 캐시 히트
            logger.info(f"[Orchestrator] Using pre-fetched cache for {corp_name}")
            provenance["layers_attempted"].append("CACHE")
            provenance["cache_hit"] = True
            logger.info(f"[Orchestrator][{trace_id}] Cache hit (pre-fetched)")
            return OrchestratorResult(
                profile=existing_profile,
                fallback_layer=FallbackLayer.CACHE,
                retry_count=0,
                error_messages=[],
                provenance=provenance,
                execution_time_ms=int((time.time() - start_time) * 1000),
                trace_id=trace_id,
            )
        else:
            # Fallback: 주입된 캐시 조회 함수 사용 (호환성 유지)
            cached_profile = self._try_cache(corp_name, industry_code, provenance)
        if cached_profile:
            logger.info(f"[Orchestrator][{trace_id}] Cache hit (lookup)")
            return OrchestratorResult(
                profile=cached_profile,
                fallback_layer=FallbackLayer.CACHE,
                retry_count=0,
                error_messages=[],
                provenance=provenance,
                execution_time_ms=int((time.time() - start_time) * 1000),
                trace_id=trace_id,
            )

        # Layer 1 + 1.5: Perplexity + Gemini
        perplexity_result = None
        gemini_validation = None
        layer1_both_failed = False
        source_map = {}  # 필드별 출처 추적

        try:
            perplexity_result, gemini_validation = self._try_perplexity_gemini(
                corp_name, industry_name, provenance, error_messages
            )
            retry_count += 1

            # source_map 초기 설정
            if perplexity_result and not perplexity_result.get("error"):
                for key in perplexity_result.keys():
                    if not key.startswith("_") and perplexity_result[key] is not None:
                        source_map[key] = perplexity_result.get("_search_source", "PERPLEXITY")
            if gemini_validation and gemini_validation.get("enriched_fields"):
                for key in gemini_validation["enriched_fields"].keys():
                    if key not in source_map:
                        source_map[key] = "GEMINI"

        except (CircuitOpenError, AllProvidersFailedError) as e:
            error_messages.append(f"Layer 1: {str(e)}")
            logger.warning(f"[Orchestrator] Layer 1 failed: {e}")
            layer1_both_failed = True

        # Layer 1 둘 다 실패 체크
        if not layer1_both_failed:
            perplexity_ok = perplexity_result and not perplexity_result.get("error")
            gemini_ok = gemini_validation and gemini_validation.get("enriched_fields")
            layer1_both_failed = not perplexity_ok and not gemini_ok

        # P1: Gemini Validation 결과를 provenance에 저장 (Fact-Check 통합용)
        if gemini_validation:
            fact_check_hints = gemini_validation.get("fact_check_hints", {})
            if fact_check_hints:
                provenance["gemini_fact_check_hints"] = fact_check_hints
                logger.info(
                    f"[Orchestrator] P1 Fact-check hints from Layer 1.5: {len(fact_check_hints)} fields"
                )

        # [핵심 수정] Layer 1 둘 다 실패 시 → Layer 4 직행 (Layer 2, 3 스킵)
        if layer1_both_failed:
            logger.warning(
                f"[Orchestrator][{trace_id}] Layer 1 both failed - skipping to Layer 4"
            )
            provenance["layer1_both_failed"] = True
            provenance["skipped_layers"] = ["CLAUDE_SYNTHESIS", "RULE_BASED"]

            degraded_profile = self._graceful_degradation(
                existing_profile,
                corp_name,
                industry_name,
                industry_code,
                provenance,
            )

            error_messages.append("Layer 1 both providers failed - graceful degradation")

            return OrchestratorResult(
                profile=degraded_profile,
                fallback_layer=FallbackLayer.GRACEFUL_DEGRADATION,
                retry_count=retry_count,
                error_messages=error_messages,
                provenance=provenance,
                execution_time_ms=int((time.time() - start_time) * 1000),
                trace_id=trace_id,
                source_map=source_map,
                layer1_both_failed=True,
            )

        # Layer 2 (v2.0): OpenAI Validation - 검색 결과 검증
        # P0 Fix: _openai_validation_fn이 설정되어 있으면 검색 결과 검증 수행
        if perplexity_result and self._openai_validation_fn:
            provenance["layers_attempted"].append("OPENAI_VALIDATION")
            try:
                # 검색 결과의 소스 확인
                search_source = perplexity_result.get("_search_source", "UNKNOWN")

                # OpenAI Validation 호출
                validation_result = self._openai_validation_fn(
                    perplexity_result,
                    corp_name,
                    industry_name,
                    search_source,
                )

                # ValidationResult 처리
                if hasattr(validation_result, 'is_valid'):
                    provenance["openai_validation_valid"] = validation_result.is_valid
                    provenance["openai_validation_confidence"] = (
                        validation_result.confidence.value
                        if hasattr(validation_result.confidence, 'value')
                        else str(validation_result.confidence)
                    )

                    # 검증된 프로필로 교체 (오류 수정 적용)
                    if hasattr(validation_result, 'validated_profile') and validation_result.validated_profile:
                        perplexity_result.update(validation_result.validated_profile)
                        provenance["openai_validation_applied"] = True

                    # 이슈 로깅
                    if hasattr(validation_result, 'issues') and validation_result.issues:
                        issue_count = len(validation_result.issues)
                        error_issues = [i for i in validation_result.issues if hasattr(i, 'severity') and i.severity.value == "ERROR"]
                        if error_issues:
                            provenance["openai_validation_errors"] = len(error_issues)
                            logger.warning(
                                f"[Orchestrator][{trace_id}] OpenAI validation found {len(error_issues)} errors"
                            )

                    logger.info(
                        f"[Orchestrator][{trace_id}] OpenAI validation completed: "
                        f"valid={validation_result.is_valid}"
                    )
                else:
                    logger.warning(f"[Orchestrator] OpenAI validation returned unexpected format")

            except Exception as e:
                error_messages.append(f"OpenAI Validation: {str(e)}")
                provenance["openai_validation_error"] = str(e)
                logger.warning(f"[Orchestrator] OpenAI validation failed: {e}")
                # 검증 실패해도 계속 진행 (non-blocking)

        # Layer 2.5: Claude Synthesis (Consensus Engine)
        if perplexity_result or gemini_validation:
            try:
                consensus_result = self._try_claude_synthesis(
                    perplexity_result,
                    gemini_validation,
                    corp_name,
                    industry_name,
                    industry_code,
                    existing_profile,
                    provenance,
                    error_messages,
                )
                retry_count += 1

                if consensus_result and consensus_result.get("profile"):
                    # source_map 업데이트 (Consensus 결과 반영)
                    if consensus_result.get("metadata") and hasattr(consensus_result["metadata"], "field_sources"):
                        source_map.update(consensus_result["metadata"].field_sources)

                    logger.info(f"[Orchestrator][{trace_id}] Layer 2 success (Claude synthesis)")
                    return OrchestratorResult(
                        profile=consensus_result["profile"],
                        fallback_layer=FallbackLayer.CLAUDE_SYNTHESIS,
                        retry_count=retry_count,
                        error_messages=error_messages,
                        consensus_metadata=consensus_result.get("metadata"),
                        provenance=provenance,
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        trace_id=trace_id,
                        source_map=source_map,
                    )
            except (CircuitOpenError, AllProvidersFailedError) as e:
                error_messages.append(f"Layer 2: {str(e)}")
                logger.warning(f"[Orchestrator] Layer 2 failed: {e}")

        # Layer 3: Rule-Based Merge
        rule_based_profile = self._try_rule_based_merge(
            perplexity_result,
            gemini_validation,
            existing_profile,
            corp_name,
            industry_name,
            industry_code,
            provenance,
        )

        if rule_based_profile and self._is_profile_sufficient(rule_based_profile):
            # source_map 업데이트 (Rule-based 결과)
            if provenance.get("rule_based_sources"):
                source_map.update(provenance["rule_based_sources"])

            logger.info(f"[Orchestrator][{trace_id}] Layer 3 success (Rule-based merge)")
            return OrchestratorResult(
                profile=rule_based_profile,
                fallback_layer=FallbackLayer.RULE_BASED,
                retry_count=retry_count,
                error_messages=error_messages,
                provenance=provenance,
                execution_time_ms=int((time.time() - start_time) * 1000),
                trace_id=trace_id,
                source_map=source_map,
            )

        # Layer 4: Graceful Degradation
        degraded_profile = self._graceful_degradation(
            existing_profile,
            corp_name,
            industry_name,
            industry_code,
            provenance,
        )

        error_messages.append("All layers failed - using graceful degradation")
        logger.warning(
            f"[Orchestrator][{trace_id}] Graceful degradation for {corp_name}: "
            f"errors={len(error_messages)}"
        )

        return OrchestratorResult(
            profile=degraded_profile,
            fallback_layer=FallbackLayer.GRACEFUL_DEGRADATION,
            retry_count=retry_count,
            error_messages=error_messages,
            provenance=provenance,
            execution_time_ms=int((time.time() - start_time) * 1000),
            trace_id=trace_id,
            source_map=source_map,
            layer1_both_failed=layer1_both_failed,
        )

    # =========================================================================
    # Layer 0: Cache
    # =========================================================================

    def _try_cache(
        self,
        corp_name: str,
        industry_code: str,
        provenance: dict,
    ) -> Optional[dict]:
        """캐시에서 프로필 조회"""
        provenance["layers_attempted"].append("CACHE")

        if not self._cache_lookup_fn:
            logger.debug("[Orchestrator] Cache lookup not configured")
            return None

        try:
            cached = self._cache_lookup_fn(corp_name, industry_code)
            if cached:
                provenance["cache_hit"] = True
                logger.info(f"[Orchestrator] Cache hit for {corp_name}")
                return cached
        except Exception as e:
            logger.warning(f"[Orchestrator] Cache lookup failed: {e}")

        return None

    # =========================================================================
    # Layer 1 + 1.5: Perplexity + Gemini (병렬 실행 - ADR-009)
    # =========================================================================

    def _try_perplexity_gemini(
        self,
        corp_name: str,
        industry_name: str,
        provenance: dict,
        error_messages: list[str],
    ) -> tuple[Optional[dict], Optional[dict]]:
        """
        Perplexity 검색 + Gemini 검증

        ADR-009 Enhancement:
        - parallel_mode=True: Perplexity + Gemini 동시 실행 (25% speedup)
        - parallel_mode=False: 기존 순차 실행 (Gemini는 Perplexity 결과 검증)

        Returns:
            (perplexity_result, gemini_validation)
        """
        provenance["layers_attempted"].append("PERPLEXITY_GEMINI")
        provenance["parallel_mode"] = self.parallel_mode

        if self.parallel_mode:
            return self._try_perplexity_gemini_parallel(
                corp_name, industry_name, provenance, error_messages
            )
        else:
            return self._try_perplexity_gemini_sequential(
                corp_name, industry_name, provenance, error_messages
            )

    def _try_perplexity_gemini_parallel(
        self,
        corp_name: str,
        industry_name: str,
        provenance: dict,
        error_messages: list[str],
    ) -> tuple[Optional[dict], Optional[dict]]:
        """
        병렬 모드: Perplexity + Gemini 동시 실행

        ADR-009 Sprint 1 구현:
        - ThreadPoolExecutor로 두 API를 동시 호출
        - 둘 다 완료 후 Consensus Engine으로 결과 병합
        - 개별 실패는 허용 (Graceful Degradation)
        """
        import concurrent.futures

        start_time = time.time()
        perplexity_result = None
        gemini_result = None
        futures = {}

        # 병렬 실행할 태스크 준비
        if self.circuit_breaker.is_available("perplexity") and self._perplexity_search_fn:
            futures["perplexity"] = self._executor.submit(
                self._safe_perplexity_search, corp_name, industry_name
            )
        else:
            if not self.circuit_breaker.is_available("perplexity"):
                error_messages.append("Perplexity circuit breaker is OPEN")
                provenance["perplexity_circuit_open"] = True
            else:
                logger.warning("[Orchestrator] Perplexity search function not configured")

        # Gemini도 병렬로 독립 검색 (검증이 아닌 독립 검색 역할)
        if self.circuit_breaker.is_available("gemini"):
            futures["gemini"] = self._executor.submit(
                self._safe_gemini_search, corp_name, industry_name
            )
        else:
            error_messages.append("Gemini circuit breaker is OPEN")
            provenance["gemini_circuit_open"] = True

        # 모든 태스크 완료 대기 (최대 45초)
        done, not_done = concurrent.futures.wait(
            futures.values(),
            # P0 Fix: 상수 사용 (병렬 모드는 max timeout + 여유 5초)
            timeout=max(self.TIMEOUT_PERPLEXITY, self.TIMEOUT_GEMINI) + 5,
            return_when=concurrent.futures.ALL_COMPLETED
        )

        # 결과 수집
        if "perplexity" in futures:
            try:
                perplexity_result = futures["perplexity"].result(timeout=1.0)
                if perplexity_result and not perplexity_result.get("error"):
                    self.circuit_breaker.record_success("perplexity")
                    provenance["perplexity_success"] = True
                    logger.info(f"[Orchestrator] Perplexity parallel search success for {corp_name}")
                elif perplexity_result and perplexity_result.get("error"):
                    error_messages.append(f"Perplexity: {perplexity_result.get('error')}")
                    provenance["perplexity_error"] = perplexity_result.get("error")
            except concurrent.futures.TimeoutError:
                error_messages.append("Perplexity: timeout")
                provenance["perplexity_error"] = "timeout"
                self.circuit_breaker.record_failure("perplexity", "timeout")
            except Exception as e:
                error_messages.append(f"Perplexity: {str(e)}")
                provenance["perplexity_error"] = str(e)
                self.circuit_breaker.record_failure("perplexity", str(e))

        if "gemini" in futures:
            try:
                gemini_result = futures["gemini"].result(timeout=1.0)
                if gemini_result and not gemini_result.get("error"):
                    self.circuit_breaker.record_success("gemini")
                    provenance["gemini_parallel_success"] = True
                    logger.info(f"[Orchestrator] Gemini parallel enrichment success for {corp_name}")
                elif gemini_result and gemini_result.get("error"):
                    error_messages.append(f"Gemini: {gemini_result.get('error')}")
                    provenance["gemini_error"] = gemini_result.get("error")
            except concurrent.futures.TimeoutError:
                error_messages.append("Gemini: timeout")
                provenance["gemini_error"] = "timeout"
                self.circuit_breaker.record_failure("gemini", "timeout")
            except Exception as e:
                error_messages.append(f"Gemini: {str(e)}")
                provenance["gemini_error"] = str(e)
                self.circuit_breaker.record_failure("gemini", str(e))

        elapsed_ms = int((time.time() - start_time) * 1000)
        provenance["layer1_parallel_time_ms"] = elapsed_ms
        logger.info(
            f"[Orchestrator] Layer 1+1.5 parallel completed in {elapsed_ms}ms "
            f"(perplexity={'OK' if perplexity_result else 'FAIL'}, "
            f"gemini={'OK' if gemini_result else 'FAIL'})"
        )

        # Gemini 결과를 validation 형식으로 변환 (Consensus Engine 호환)
        gemini_validation = None
        if gemini_result and not gemini_result.get("error"):
            gemini_validation = {
                "validated_fields": [],
                "enriched_fields": gemini_result.get("enriched_fields", {}),
                "discrepancies": [],
                "source": "GEMINI_PARALLEL",
            }

        return perplexity_result, gemini_validation

    def _safe_perplexity_search(self, corp_name: str, industry_name: str) -> Optional[dict]:
        """
        Thread-safe Perplexity 검색 래퍼

        Multi-Search 모드가 활성화되어 있으면:
        1. Perplexity 먼저 시도
        2. 실패 시 MultiSearchManager로 대안 Provider 시도
        """
        # 1차: Perplexity 직접 호출 시도
        try:
            result = self._perplexity_search_fn(corp_name, industry_name)
            if result and not result.get("error"):
                return result
        except Exception as e:
            logger.warning(f"[Orchestrator] Perplexity search exception: {e}")
            perplexity_error = str(e)
        else:
            perplexity_error = result.get("error") if result else "empty_result"

        # 2차: Multi-Search Fallback (Perplexity 실패 시)
        if self._use_multi_search and self._multi_search_manager:
            logger.info(f"[Orchestrator] Perplexity failed, trying MultiSearchManager fallback")
            try:
                # 검색 쿼리 생성
                query = f"{corp_name} {industry_name} 기업 정보 매출 사업 현황"

                # P1 Fix: Thread-safe event loop 사용
                loop = _get_or_create_event_loop()

                search_result: SearchResult = loop.run_until_complete(
                    self._multi_search_manager.search(
                        query=query,
                        preferred_provider=None,  # Perplexity 제외하고 시도
                    )
                )

                if search_result and search_result.content:
                    logger.info(
                        f"[Orchestrator] MultiSearch fallback success with {search_result.provider.value}",
                        extra={
                            "provider": search_result.provider.value,
                            "latency_ms": search_result.latency_ms,
                        }
                    )
                    return {
                        "content": search_result.content,
                        "citations": search_result.citations,
                        "source": f"MULTI_SEARCH_{search_result.provider.value.upper()}",
                        "fallback_used": True,
                        "original_error": perplexity_error,
                    }

            except Exception as fallback_error:
                logger.warning(f"[Orchestrator] MultiSearch fallback also failed: {fallback_error}")
                return {
                    "error": f"Perplexity: {perplexity_error}; Fallback: {str(fallback_error)}",
                    "error_type": "all_search_failed"
                }

        return {"error": perplexity_error, "error_type": "exception"}

    def _safe_gemini_search(self, corp_name: str, industry_name: str) -> Optional[dict]:
        """
        Thread-safe Gemini Grounding 검색 래퍼 (병렬 모드용)

        Gemini를 검증 역할이 아닌 독립 검색 역할로 사용합니다.
        GeminiGroundingProvider를 사용하여 Google Search 기반 검색을 수행합니다.
        """
        try:
            # GeminiGroundingProvider로 실제 검색 수행
            gemini_provider = GeminiGroundingProvider(self.circuit_breaker)

            if not gemini_provider.is_available():
                logger.warning("[Orchestrator] Gemini API key not available")
                return {"error": "Gemini API key not configured", "error_type": "no_api_key"}

            # 검색 쿼리 생성 (Perplexity와 유사한 포맷)
            query = f"""다음 한국 기업의 최신 정보를 검색해주세요:
기업명: {corp_name}
업종: {industry_name}

다음 정보를 찾아주세요:
- 사업 개요 및 주요 제품/서비스
- 최근 매출액 (원화)
- 수출 비중 (%)
- 주요 고객사
- 국가별 매출 비중
- 주요 원자재
- 공급망 정보 (주요 공급사, 단일 조달처 위험)
- 해외 사업 현황 (해외 법인, 공장)
- 주요 주주 정보
- CEO/대표이사 이름
- 임직원 수
- 설립 연도
- 본사 위치

정확한 수치와 출처를 포함해주세요."""

            # Thread-safe event loop 사용
            loop = _get_or_create_event_loop()
            search_result: SearchResult = loop.run_until_complete(
                gemini_provider.search(query)
            )

            if search_result and search_result.content:
                logger.info(
                    f"[Orchestrator] Gemini Grounding search success for {corp_name}",
                    extra={
                        "latency_ms": search_result.latency_ms,
                        "citations_count": len(search_result.citations),
                    }
                )
                return {
                    "content": search_result.content,
                    "citations": search_result.citations,
                    "enriched_fields": {"raw_content": search_result.content},
                    "_search_source": "GEMINI_GROUNDING",
                    "confidence": search_result.confidence,
                }
            else:
                return {"error": "Empty search result", "error_type": "empty_result"}

        except Exception as e:
            logger.warning(f"[Orchestrator] Gemini Grounding search exception: {e}")
            return {"error": str(e), "error_type": "exception"}

    def _try_perplexity_gemini_sequential(
        self,
        corp_name: str,
        industry_name: str,
        provenance: dict,
        error_messages: list[str],
    ) -> tuple[Optional[dict], Optional[dict]]:
        """
        v2.0 순차 Fallback 모드: Perplexity 먼저 → 실패 시에만 Gemini

        핵심 변경:
        - Perplexity 성공하면 Gemini 호출 안 함 (비용 절약)
        - Perplexity 실패 시에만 Gemini Fallback 시도
        - 타임아웃 30초로 단축

        Returns:
            (search_result, None) - Gemini는 더 이상 validation 역할 안 함
        """
        search_result = None
        search_source = None

        # Layer 1: Perplexity Search (Primary)
        perplexity_success = False
        if self.circuit_breaker.is_available("perplexity"):
            try:
                if self._perplexity_search_fn:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            self._perplexity_search_fn, corp_name, industry_name
                        )
                        try:
                            search_result = future.result(timeout=self.TIMEOUT_PERPLEXITY)
                            # 성공 판정: 에러 없고 필드 수 충분
                            if search_result and not search_result.get("error"):
                                field_count = self._count_profile_fields(search_result)
                                if field_count >= self.MIN_FIELDS_PARTIAL_SUCCESS:
                                    perplexity_success = True
                                    search_source = "PERPLEXITY"
                                    self.circuit_breaker.record_success("perplexity")
                                    provenance["perplexity_success"] = True
                                    provenance["perplexity_field_count"] = field_count
                                    logger.info(
                                        f"[Orchestrator] Perplexity success for {corp_name}: "
                                        f"{field_count} fields"
                                    )
                                else:
                                    # 부분 실패: 필드 수 부족
                                    error_messages.append(
                                        f"Perplexity: insufficient fields ({field_count})"
                                    )
                                    provenance["perplexity_partial"] = True
                                    provenance["perplexity_field_count"] = field_count
                            else:
                                error_msg = search_result.get("error", "empty_result") if search_result else "empty_result"
                                error_messages.append(f"Perplexity: {error_msg}")
                                provenance["perplexity_error"] = error_msg
                        except concurrent.futures.TimeoutError:
                            error_messages.append(f"Perplexity: timeout ({self.TIMEOUT_PERPLEXITY}s)")
                            provenance["perplexity_error"] = "timeout"
                            self.circuit_breaker.record_failure("perplexity", "timeout")
                else:
                    logger.warning("[Orchestrator] Perplexity search function not configured")
            except Exception as e:
                self.circuit_breaker.record_failure("perplexity", str(e))
                error_messages.append(f"Perplexity: {str(e)}")
                provenance["perplexity_error"] = str(e)
                logger.warning(f"[Orchestrator] Perplexity search failed: {e}")
        else:
            error_messages.append("Perplexity circuit breaker is OPEN")
            provenance["perplexity_circuit_open"] = True

        # Layer 1.5: Gemini Fallback (Perplexity 실패 시에만)
        if not perplexity_success and self.circuit_breaker.is_available("gemini"):
            logger.info(f"[Orchestrator] Perplexity failed, trying Gemini fallback for {corp_name}")
            provenance["gemini_fallback_attempted"] = True
            gemini_fn_failed = False

            try:
                # P1 Fix: Gemini 검색 함수 먼저 시도, 실패 시 MultiSearchManager 시도
                # (이전에는 둘 중 하나만 시도했음)
                if self._gemini_search_fn:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            self._gemini_search_fn, corp_name, industry_name
                        )
                        try:
                            gemini_result = future.result(timeout=self.TIMEOUT_GEMINI)
                            if gemini_result and not gemini_result.get("error"):
                                field_count = self._count_profile_fields(gemini_result)
                                if field_count >= self.MIN_FIELDS_PARTIAL_SUCCESS:
                                    search_result = gemini_result
                                    search_source = "GEMINI_FALLBACK"
                                    self.circuit_breaker.record_success("gemini")
                                    provenance["gemini_fallback_success"] = True
                                    provenance["gemini_field_count"] = field_count
                                    logger.info(
                                        f"[Orchestrator] Gemini fallback success for {corp_name}: "
                                        f"{field_count} fields"
                                    )
                                else:
                                    gemini_fn_failed = True
                                    provenance["gemini_partial"] = True
                                    logger.warning(f"[Orchestrator] Gemini returned insufficient fields ({field_count})")
                            else:
                                gemini_fn_failed = True
                                error_msg = gemini_result.get("error", "empty_result") if gemini_result else "empty_result"
                                provenance["gemini_fn_error"] = error_msg
                        except concurrent.futures.TimeoutError:
                            gemini_fn_failed = True
                            provenance["gemini_fn_error"] = "timeout"
                            self.circuit_breaker.record_failure("gemini", "timeout")
                else:
                    gemini_fn_failed = True  # 함수 미설정

                # P1 Fix: Gemini 함수 실패 시 MultiSearchManager로 2차 시도
                if gemini_fn_failed and self._use_multi_search and self._multi_search_manager:
                    logger.info(f"[Orchestrator] Gemini function failed, trying MultiSearchManager")
                    provenance["gemini_multisearch_attempted"] = True

                    gemini_result = self._safe_gemini_fallback_search(corp_name, industry_name)
                    if gemini_result and not gemini_result.get("error"):
                        search_result = gemini_result
                        search_source = "GEMINI_GROUNDING"
                        self.circuit_breaker.record_success("gemini")
                        provenance["gemini_fallback_success"] = True
                    else:
                        error_msg = gemini_result.get("error") if gemini_result else "no_result"
                        error_messages.append(f"Gemini: {error_msg}")
                        provenance["gemini_error"] = error_msg
                elif gemini_fn_failed:
                    # MultiSearchManager 미설정
                    error_messages.append("Gemini: fallback not available")
                    provenance["gemini_error"] = "no_fallback_configured"

            except Exception as e:
                self.circuit_breaker.record_failure("gemini", str(e))
                error_messages.append(f"Gemini: {str(e)}")
                provenance["gemini_error"] = str(e)
                logger.warning(f"[Orchestrator] Gemini fallback failed: {e}")
        elif not perplexity_success:
            error_messages.append("Gemini circuit breaker is OPEN")
            provenance["gemini_circuit_open"] = True
        else:
            # Perplexity 성공 → Gemini 스킵
            provenance["gemini_skipped"] = "perplexity_success"
            logger.debug(f"[Orchestrator] Skipping Gemini - Perplexity succeeded for {corp_name}")

        # 결과에 소스 정보 추가
        if search_result:
            search_result["_search_source"] = search_source

        # v2.0: Gemini validation 역할 제거 → None 반환
        return search_result, None

    def _safe_gemini_fallback_search(self, corp_name: str, industry_name: str) -> Optional[dict]:
        """Gemini Grounding을 사용한 Fallback 검색"""
        try:
            query = f"{corp_name} {industry_name} 기업 정보 매출 사업 현황 경쟁사 주요 고객"

            # P1 Fix: Thread-safe event loop 사용
            loop = _get_or_create_event_loop()

            from app.worker.llm.search_providers import SearchProviderType
            search_result = loop.run_until_complete(
                self._multi_search_manager.search(
                    query=query,
                    preferred_provider=SearchProviderType.GEMINI_GROUNDING,
                )
            )

            if search_result and search_result.content:
                return {
                    "content": search_result.content,
                    "citations": search_result.citations,
                    "source": "GEMINI_GROUNDING",
                    "confidence": search_result.confidence,
                }
            return {"error": "empty_result"}
        except Exception as e:
            logger.warning(f"[Orchestrator] Gemini fallback search exception: {e}")
            return {"error": str(e)}

    def _count_profile_fields(self, profile: dict) -> int:
        """프로필에서 유효한 필드 수 카운트"""
        if not profile:
            return 0
        count = 0
        for key, value in profile.items():
            # 메타 필드 제외
            if key.startswith("_"):
                continue
            # None, 빈 문자열, 빈 리스트 제외
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, list) and not value:
                continue
            # P2 Fix: dict인 경우 내부에 유효한 값이 있는지 확인
            if isinstance(value, dict):
                if not value:  # 빈 dict
                    continue
                # 중첩된 dict의 모든 값이 None/빈값인지 확인
                has_valid_nested = False
                for nested_val in value.values():
                    if nested_val is not None:
                        if isinstance(nested_val, str) and not nested_val.strip():
                            continue
                        if isinstance(nested_val, (list, dict)) and not nested_val:
                            continue
                        has_valid_nested = True
                        break
                if not has_valid_nested:
                    continue
            count += 1
        return count

    # =========================================================================
    # Layer 2: Claude Synthesis (Consensus Engine)
    # =========================================================================

    def _try_claude_synthesis(
        self,
        perplexity_result: Optional[dict],
        gemini_validation: Optional[dict],
        corp_name: str,
        industry_name: str,
        industry_code: str,
        existing_profile: Optional[dict],
        provenance: dict,
        error_messages: list[str],
    ) -> Optional[dict]:
        """
        Claude를 사용한 합성 (Consensus Engine)

        Returns:
            {"profile": dict, "metadata": ConsensusMetadata}
        """
        provenance["layers_attempted"].append("CLAUDE_SYNTHESIS")

        if not self.circuit_breaker.is_available("claude"):
            error_messages.append("Claude circuit breaker is OPEN")
            provenance["claude_circuit_open"] = True
            return None

        try:
            # Consensus Engine에 전달할 소스들 준비
            sources = []

            if perplexity_result:
                sources.append({
                    "provider": "perplexity",
                    "profile": perplexity_result,
                    "confidence": "HIGH" if gemini_validation else "MED",
                })

            if gemini_validation and gemini_validation.get("enriched_fields"):
                # Gemini enriched 필드를 별도 소스로
                sources.append({
                    "provider": "gemini",
                    "profile": gemini_validation.get("enriched_fields", {}),
                    "confidence": "MED",  # 생성형 보완은 기본 MED
                })

            if existing_profile:
                sources.append({
                    "provider": "existing",
                    "profile": existing_profile,
                    "confidence": "MED",
                })

            if not sources:
                logger.warning("[Orchestrator] No sources for consensus")
                return None

            # Claude 합성 함수 호출 (주입된 함수 사용)
            if self._claude_synthesis_fn:
                synthesis_result = self._claude_synthesis_fn(
                    sources=sources,
                    corp_name=corp_name,
                    industry_name=industry_name,
                    industry_code=industry_code,
                    gemini_discrepancies=gemini_validation.get("discrepancies", []) if gemini_validation else [],
                )
                self.circuit_breaker.record_success("claude")
                provenance["claude_synthesis_success"] = True

                return synthesis_result
            else:
                # Claude 함수 없으면 Consensus Engine만 사용
                # ConsensusEngine.merge()는 perplexity_profile, gemini_result를 기대함
                consensus_result = self.consensus_engine.merge(
                    perplexity_profile=perplexity_result or {},
                    gemini_result=gemini_validation or {},
                    corp_name=corp_name,
                    industry_code=industry_code,
                )

                return {
                    "profile": consensus_result.profile,
                    "metadata": ConsensusMetadata(
                        perplexity_success=True,
                        gemini_success=gemini_validation is not None,
                        claude_success=True,
                        total_fields=consensus_result.metadata.total_fields,
                        matched_fields=consensus_result.metadata.matched_fields,
                        discrepancy_fields=consensus_result.metadata.discrepancy_fields,
                        enriched_fields=consensus_result.metadata.enriched_fields,
                        overall_confidence=consensus_result.metadata.overall_confidence,
                        fallback_layer=2,  # 2: Claude Synthesis layer
                        retry_count=consensus_result.metadata.retry_count,
                        error_messages=consensus_result.metadata.error_messages,
                    ),
                }

        except Exception as e:
            self.circuit_breaker.record_failure("claude", str(e))
            error_messages.append(f"Claude: {str(e)}")
            provenance["claude_synthesis_error"] = str(e)
            logger.warning(f"[Orchestrator] Claude synthesis failed: {e}")
            return None

    # =========================================================================
    # Layer 3: Rule-Based Merge
    # =========================================================================

    def _try_rule_based_merge(
        self,
        perplexity_result: Optional[dict],
        gemini_validation: Optional[dict],
        existing_profile: Optional[dict],
        corp_name: str,
        industry_name: str,
        industry_code: str,
        provenance: dict,
    ) -> Optional[dict]:
        """
        Rule-Based Merge (LLM 없이 결정론적 병합)

        규칙:
        1. 소스 우선순위에 따라 필드 선택
        2. 숫자 필드 범위 검증
        3. 비율 필드 합계 검증 (export + domestic = 100)
        4. 필수 필드 강제 설정
        """
        provenance["layers_attempted"].append("RULE_BASED")

        merged = {}
        field_sources = {}  # 필드별 소스 추적

        # 소스별 데이터 수집
        sources_data = []

        if perplexity_result:
            sources_data.append({
                "source": "PERPLEXITY_VERIFIED",
                "data": perplexity_result,
            })

        if gemini_validation:
            # Validated fields
            for field_name in gemini_validation.get("validated_fields", []):
                if perplexity_result and field_name in perplexity_result:
                    # 이미 perplexity에서 가져옴
                    pass

            # Enriched fields
            enriched = gemini_validation.get("enriched_fields", {})
            if enriched:
                sources_data.append({
                    "source": "GEMINI_INFERRED",
                    "data": self._extract_enriched_values(enriched),
                })

        if existing_profile:
            sources_data.append({
                "source": "EXISTING",
                "data": existing_profile,
            })

        # 우선순위에 따라 필드 병합
        all_fields = set()
        for src in sources_data:
            all_fields.update(src["data"].keys())

        for field_name in all_fields:
            best_value = None
            best_priority = -1
            best_source = None

            for src in sources_data:
                if field_name in src["data"]:
                    value = src["data"][field_name]
                    if value is None:
                        continue

                    priority = self.rule_config.source_priority.get(src["source"], 10)
                    if priority > best_priority:
                        best_priority = priority
                        best_value = value
                        best_source = src["source"]

            if best_value is not None:
                # 범위 검증
                if field_name in self.rule_config.numeric_fields:
                    best_value = self._validate_numeric(field_name, best_value)

                merged[field_name] = best_value
                field_sources[field_name] = best_source

        # 필수 필드 강제 설정
        merged["corp_name"] = corp_name
        merged["industry_code"] = industry_code
        merged["industry_name"] = industry_name

        # 비율 합계 검증 (export + domestic = 100)
        merged = self._validate_ratio_sum(merged)

        provenance["rule_based_fields"] = len(merged)
        provenance["rule_based_sources"] = field_sources

        logger.info(
            f"[Orchestrator] Rule-based merge: {len(merged)} fields from "
            f"{len(set(field_sources.values()))} sources"
        )

        return merged

    def _extract_enriched_values(self, enriched: dict) -> dict:
        """Gemini enriched 필드에서 값만 추출"""
        result = {}
        for field_name, field_data in enriched.items():
            if isinstance(field_data, dict) and "value" in field_data:
                result[field_name] = field_data["value"]
            else:
                result[field_name] = field_data
        return result

    def _validate_numeric(self, field_name: str, value: Any) -> Any:
        """숫자 필드 범위 검증"""
        if not isinstance(value, (int, float)):
            try:
                value = float(value)
            except (ValueError, TypeError):
                return None

        # 비율 필드는 0-100 범위
        if field_name in self.rule_config.ratio_fields:
            value = max(0, min(100, value))

        # 음수 불가 필드
        if field_name in ["employee_count"]:
            value = max(0, value)

        return value

    def _validate_ratio_sum(self, profile: dict) -> dict:
        """비율 합계 검증 (export + domestic = 100)"""
        export_ratio = profile.get("export_ratio")
        domestic_ratio = profile.get("domestic_ratio")

        if export_ratio is not None and domestic_ratio is None:
            profile["domestic_ratio"] = 100 - export_ratio
        elif domestic_ratio is not None and export_ratio is None:
            profile["export_ratio"] = 100 - domestic_ratio
        elif export_ratio is not None and domestic_ratio is not None:
            total = export_ratio + domestic_ratio
            if abs(total - 100) > 1:  # 1% 오차 허용
                # 비율 조정
                if total > 0:
                    ratio = 100 / total
                    profile["export_ratio"] = round(export_ratio * ratio, 1)
                    profile["domestic_ratio"] = round(domestic_ratio * ratio, 1)

        return profile

    # =========================================================================
    # Layer 4: Graceful Degradation
    # =========================================================================

    def _graceful_degradation(
        self,
        existing_profile: Optional[dict],
        corp_name: str,
        industry_name: str,
        industry_code: str,
        provenance: dict,
    ) -> dict:
        """
        Graceful Degradation (최소 프로필 + 경고)

        모든 Layer 실패 시 최소한의 프로필 반환:
        - 필수 필드만 포함
        - 경고 메시지 추가
        - 기존 프로필 있으면 사용
        """
        provenance["layers_attempted"].append("GRACEFUL_DEGRADATION")

        degraded = {
            "corp_name": corp_name,
            "industry_code": industry_code,
            "industry_name": industry_name,
            "_degraded": True,
            "_degradation_reason": "All profiling layers failed",
            "_degradation_timestamp": datetime.now().isoformat(),
        }

        # 기존 프로필에서 복사 가능한 필드
        if existing_profile:
            safe_fields = [
                "biz_no", "corp_reg_no", "ceo_name", "address",
                "main_products", "main_customers", "main_suppliers",
            ]
            for field in safe_fields:
                if field in existing_profile and existing_profile[field]:
                    degraded[field] = existing_profile[field]

        logger.warning(
            f"[Orchestrator] Graceful degradation for {corp_name}: "
            f"returning {len(degraded)} fields"
        )

        return degraded

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _is_profile_sufficient(self, profile: dict) -> bool:
        """
        프로필이 충분한지 확인

        P0-3 Fix: 최소 필드 수 기준 완화
        - 기존: 필수 3개 + 추가 3개 = 6개 필드 필요
        - 수정: 필수 3개 + 추가 1개 = 4개 필드 필요

        이유: Perplexity 실패 시 Gemini enriched 필드만으로도
        Layer 3 Rule-Based Merge 가능하도록 기준 완화
        """
        if not profile:
            return False

        # 필수 필드 확인
        for field in self.rule_config.required_fields:
            if field not in profile or profile[field] is None:
                return False

        # P0-3 Fix: 최소 필드 수 완화 (3개 → 1개 추가)
        # 기존: required(3) + 3 = 6개 필요
        # 수정: required(3) + 1 = 4개 필요
        MIN_ADDITIONAL_FIELDS = 1
        non_meta_fields = [k for k in profile.keys() if not k.startswith("_")]
        if len(non_meta_fields) < len(self.rule_config.required_fields) + MIN_ADDITIONAL_FIELDS:
            return False

        return True

    def get_circuit_status(self) -> dict:
        """모든 Circuit Breaker 상태 조회"""
        return {
            provider: status.to_dict() if hasattr(status, 'to_dict') else {
                "state": status.state.value,
                "failure_count": status.failure_count,
                "cooldown_remaining": status.cooldown_remaining,
            }
            for provider, status in self.circuit_breaker.get_all_status().items()
        }


# ============================================================================
# Singleton Instance
# ============================================================================

_orchestrator_instance: Optional[MultiAgentOrchestrator] = None


def get_orchestrator() -> MultiAgentOrchestrator:
    """MultiAgentOrchestrator 싱글톤 인스턴스 반환"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = MultiAgentOrchestrator()
    return _orchestrator_instance


def reset_orchestrator():
    """테스트용 - 인스턴스 리셋"""
    global _orchestrator_instance
    _orchestrator_instance = None
