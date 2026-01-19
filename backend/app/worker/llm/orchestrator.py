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
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any

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

logger = logging.getLogger(__name__)


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

    실행 순서:
    1. Cache 확인 (Layer 0)
    2. Perplexity 검색 + Gemini 검증 (Layer 1 + 1.5)
    3. Claude 합성 (Layer 2) - Consensus Engine 사용
    4. Rule-Based Merge (Layer 3)
    5. Graceful Degradation (Layer 4)
    """

    def __init__(
        self,
        circuit_breaker_manager: Optional[CircuitBreakerManager] = None,
        consensus_engine: Optional[ConsensusEngine] = None,
        gemini_adapter: Optional[GeminiAdapter] = None,
        rule_config: Optional[RuleBasedMergeConfig] = None,
    ):
        self.circuit_breaker = circuit_breaker_manager or get_circuit_breaker_manager()
        self.consensus_engine = consensus_engine or get_consensus_engine()
        self.gemini = gemini_adapter or get_gemini_adapter()
        self.rule_config = rule_config or RuleBasedMergeConfig()

        # Perplexity search function will be injected
        self._perplexity_search_fn = None
        self._claude_synthesis_fn = None
        self._cache_lookup_fn = None

    def set_perplexity_search(self, fn):
        """Perplexity 검색 함수 주입"""
        self._perplexity_search_fn = fn

    def set_claude_synthesis(self, fn):
        """Claude 합성 함수 주입"""
        self._claude_synthesis_fn = fn

    def set_cache_lookup(self, fn):
        """캐시 조회 함수 주입"""
        self._cache_lookup_fn = fn

    def execute(
        self,
        corp_name: str,
        industry_name: str,
        industry_code: str,
        existing_profile: Optional[dict] = None,
    ) -> OrchestratorResult:
        """
        4-Layer Fallback 실행

        Args:
            corp_name: 기업명
            industry_name: 업종명
            industry_code: 업종코드
            existing_profile: 기존 프로필 (있으면 보완용)

        Returns:
            OrchestratorResult: 실행 결과 (프로필, fallback layer, 메타데이터)
        """
        start_time = time.time()
        error_messages = []
        retry_count = 0
        provenance = {
            "started_at": datetime.now().isoformat(),
            "corp_name": corp_name,
            "industry_code": industry_code,
            "layers_attempted": [],
        }

        # Layer 0: Cache
        cached_profile = self._try_cache(corp_name, industry_code, provenance)
        if cached_profile:
            return OrchestratorResult(
                profile=cached_profile,
                fallback_layer=FallbackLayer.CACHE,
                retry_count=0,
                error_messages=[],
                provenance=provenance,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        # Layer 1 + 1.5: Perplexity + Gemini
        perplexity_result = None
        gemini_validation = None

        try:
            perplexity_result, gemini_validation = self._try_perplexity_gemini(
                corp_name, industry_name, provenance, error_messages
            )
            retry_count += 1
        except (CircuitOpenError, AllProvidersFailedError) as e:
            error_messages.append(f"Layer 1: {str(e)}")
            logger.warning(f"[Orchestrator] Layer 1 failed: {e}")

        # Layer 2: Claude Synthesis (Consensus Engine)
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
                    return OrchestratorResult(
                        profile=consensus_result["profile"],
                        fallback_layer=FallbackLayer.CLAUDE_SYNTHESIS,
                        retry_count=retry_count,
                        error_messages=error_messages,
                        consensus_metadata=consensus_result.get("metadata"),
                        provenance=provenance,
                        execution_time_ms=int((time.time() - start_time) * 1000),
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
            return OrchestratorResult(
                profile=rule_based_profile,
                fallback_layer=FallbackLayer.RULE_BASED,
                retry_count=retry_count,
                error_messages=error_messages,
                provenance=provenance,
                execution_time_ms=int((time.time() - start_time) * 1000),
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
            f"[Orchestrator] Graceful degradation for {corp_name}: "
            f"errors={len(error_messages)}"
        )

        return OrchestratorResult(
            profile=degraded_profile,
            fallback_layer=FallbackLayer.GRACEFUL_DEGRADATION,
            retry_count=retry_count,
            error_messages=error_messages,
            provenance=provenance,
            execution_time_ms=int((time.time() - start_time) * 1000),
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
    # Layer 1 + 1.5: Perplexity + Gemini
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

        Returns:
            (perplexity_result, gemini_validation)
        """
        provenance["layers_attempted"].append("PERPLEXITY_GEMINI")
        perplexity_result = None
        gemini_validation = None

        # Layer 1: Perplexity Search
        if self.circuit_breaker.is_available("perplexity"):
            try:
                if self._perplexity_search_fn:
                    perplexity_result = self._perplexity_search_fn(corp_name, industry_name)
                    self.circuit_breaker.record_success("perplexity")
                    provenance["perplexity_success"] = True
                    logger.info(f"[Orchestrator] Perplexity search success for {corp_name}")
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

        # Layer 1.5: Gemini Validation
        if perplexity_result and self.circuit_breaker.is_available("gemini"):
            try:
                gemini_validation = self.gemini.validate(
                    perplexity_result=perplexity_result,
                    corp_name=corp_name,
                    industry_name=industry_name,
                )
                self.circuit_breaker.record_success("gemini")
                provenance["gemini_validation_success"] = True
                logger.info(f"[Orchestrator] Gemini validation success for {corp_name}")
            except Exception as e:
                self.circuit_breaker.record_failure("gemini", str(e))
                error_messages.append(f"Gemini: {str(e)}")
                provenance["gemini_validation_error"] = str(e)
                logger.warning(f"[Orchestrator] Gemini validation failed: {e}")
        elif not perplexity_result:
            logger.debug("[Orchestrator] Skipping Gemini - no Perplexity result")
        else:
            error_messages.append("Gemini circuit breaker is OPEN")
            provenance["gemini_circuit_open"] = True

        return perplexity_result, gemini_validation

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
                merged_profile = self.consensus_engine.merge(
                    profiles=[s["profile"] for s in sources],
                    weights={s["provider"]: 1.0 for s in sources},
                )

                return {
                    "profile": merged_profile,
                    "metadata": ConsensusMetadata(
                        total_sources=len(sources),
                        agreement_ratio=0.8,  # 기본값
                        fields_merged=list(merged_profile.keys()),
                        discrepancies=[],
                        fallback_layer=FallbackLayer.CLAUDE_SYNTHESIS.value,
                        retry_count=0,
                        error_messages=[],
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
        """프로필이 충분한지 확인"""
        if not profile:
            return False

        # 필수 필드 확인
        for field in self.rule_config.required_fields:
            if field not in profile or profile[field] is None:
                return False

        # 최소 필드 수 확인 (필수 필드 외 3개 이상)
        non_meta_fields = [k for k in profile.keys() if not k.startswith("_")]
        if len(non_meta_fields) < len(self.rule_config.required_fields) + 3:
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
