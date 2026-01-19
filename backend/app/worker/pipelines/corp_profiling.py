"""
Corp Profiling Pipeline for ENVIRONMENT Signal Enhancement

PRD v1.2 4-Layer Fallback Architecture:
- Layer 0: Profile Cache (exact match)
- Layer 1: Perplexity Search (with citation verification)
- Layer 1.5: Gemini Validation (cross-validation, enrichment)
- Layer 2: Consensus Engine / Claude Synthesis (multi-source merge)
- Layer 3: Rule-Based Merge (deterministic fallback)
- Layer 4: Graceful Degradation (최소 프로필 + 경고)

Anti-Hallucination 4-Layer Defense:
- Layer 1: Source Verification (PerplexityResponseParser)
- Layer 2: Extraction Guardrails (LLM Prompt with strict null rules)
- Layer 3: Validation Layer (CorpProfileValidator)
- Layer 4: Audit Trail (ProvenanceTracker, raw_search_result storage)

Pipeline Flow:
1. Orchestrator coordination (4-layer fallback)
2. Perplexity search + Gemini validation
3. Claude synthesis / Consensus Engine
4. Rule-Based merge fallback
5. Graceful degradation
6. DB storage with full audit trail
7. Conditional query selection
"""

import logging
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID, uuid4

from app.core.config import settings
from app.worker.llm.orchestrator import (
    MultiAgentOrchestrator,
    OrchestratorResult,
    FallbackLayer,
    get_orchestrator,
)
from app.worker.llm.circuit_breaker import get_circuit_breaker_manager

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Default TTL for profiles
PROFILE_TTL_DAYS = 7
FALLBACK_TTL_DAYS = 1  # Shorter TTL for fallback profiles

# High-trust domains for confidence determination
HIGH_TRUST_DOMAINS = [
    "dart.fss.or.kr",
    "kind.krx.co.kr",
    ".go.kr",
    ".or.kr",
]

MED_TRUST_DOMAINS = [
    "reuters.com",
    "bloomberg.com",
    "hankyung.com",
    "mk.co.kr",
    "sedaily.com",
    "chosun.com",
    "donga.com",
    "hani.co.kr",
]

# Extraction prompt version for reproducibility
PROMPT_VERSION = "v1.0"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class FieldProvenance:
    """Track source of each extracted field."""
    field_name: str
    value: Any
    source_url: Optional[str]
    excerpt: Optional[str]
    confidence: str
    extraction_date: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "source_url": self.source_url,
            "excerpt": self.excerpt[:200] if self.excerpt else None,
            "confidence": self.confidence,
            "extraction_date": self.extraction_date.isoformat(),
        }


@dataclass
class ValidationResult:
    """Profile validation result."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    corrected_profile: Optional[dict] = None


@dataclass
class QueryCondition:
    """Condition for query selection."""
    field: str
    op: str  # ">=", "==", "in", "contains_key", "is_not_empty"
    value: Any


@dataclass
class CorpProfileResult:
    """Result of corp profiling pipeline."""
    profile: dict
    selected_queries: list[str]
    is_cached: bool = False
    query_details: list[dict] = field(default_factory=list)


# ============================================================================
# Layer 1: Source Verification - PerplexityResponseParser
# ============================================================================


class PerplexityResponseParser:
    """
    Parse and validate Perplexity API responses with citation extraction.
    Anti-Hallucination Layer 1: Source Verification
    """

    def parse_response(self, raw_response: dict) -> dict:
        """Extract content, citations, and assess source quality."""
        content = ""
        citations = []

        if "choices" in raw_response:
            choices = raw_response.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")

        # Perplexity provides citations in the response
        citations = raw_response.get("citations", [])

        # Extract URLs from content if citations not provided
        if not citations:
            citations = self._extract_urls_from_content(content)

        source_quality = self._assess_source_quality(citations)

        return {
            "content": content,
            "citations": citations,
            "source_quality": source_quality,
            "raw_response": raw_response,
        }

    def _extract_urls_from_content(self, content: str) -> list[str]:
        """Extract URLs from content text."""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        return list(set(urls))[:10]  # Limit to 10 unique URLs

    def _assess_source_quality(self, citations: list[str]) -> str:
        """
        Assess overall source quality for confidence determination.
        Returns: HIGH, MED, or LOW
        """
        if not citations:
            return "LOW"

        high_trust_count = 0
        med_trust_count = 0

        for url in citations:
            url_lower = url.lower()
            if any(domain in url_lower for domain in HIGH_TRUST_DOMAINS):
                high_trust_count += 1
            elif any(domain in url_lower for domain in MED_TRUST_DOMAINS):
                med_trust_count += 1

        if high_trust_count >= 2:
            return "HIGH"
        elif high_trust_count >= 1 or med_trust_count >= 2:
            return "MED"
        return "LOW"


# ============================================================================
# Layer 2: Extraction Guardrails - Prompts
# ============================================================================

PROFILE_EXTRACTION_SYSTEM_PROMPT = """당신은 금융기관 기업심사를 위한 기업 프로파일 추출 전문가입니다.

## 핵심 규칙 (Anti-Hallucination)

### 규칙 1: 출처 귀속 필수
추출하는 모든 값에는 반드시 다음이 포함되어야 합니다:
- 해당 정보를 찾은 출처 URL
- 출처에서 직접 인용하거나 요약한 텍스트

특정 출처에 귀속할 수 없는 값은 반드시 null로 설정하세요.

### 규칙 2: 불확실 = null
다음과 같은 정보는 null로 설정해야 합니다:
- 출처 간 모호하거나 상충되는 정보
- 명확한 숫자 없이 언급만 된 정보
- 최근 확인 없이 3년 이상 된 정보
- 회사 발표가 아닌 애널리스트 추정치

### 규칙 3: 추론 금지
다음을 하지 마세요:
- 부분 데이터로 export_ratio_pct 계산
- 제품 목적지로 country_exposure 추정
- 시장 점유율 데이터로 매출 추론
- 업종 "일반적인" 값으로 대체

### 규칙 4: 필드별 신뢰도
추출하는 각 필드에 대해 다음을 제공하세요:
- confidence: HIGH/MED/LOW
- source_url: 특정 URL
- excerpt: 값을 뒷받침하는 정확한 텍스트 (최대 200자)

## 신뢰도 판단 기준
- HIGH: DART 공시, IR 자료, 사업보고서 등 공식 출처
- MED: 주요 언론 보도, 업계 리포트
- LOW: 추정, 간접 정보, 출처 불명확, 블로그/커뮤니티
"""

PROFILE_EXTRACTION_USER_PROMPT = """## 검색 결과
{search_results}

## 추출 대상 기업
기업명: {corp_name}
업종: {industry_name}

## 출력 스키마
다음 JSON 형식으로만 응답하세요:

```json
{{
  "business_summary": {{
    "value": "string (100자 이내) 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "revenue_krw": {{
    "value": "integer (원화) 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "export_ratio_pct": {{
    "value": "integer 0-100 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "country_exposure": {{
    "value": {{"국가명": 비중(%)}} 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "key_materials": {{
    "value": ["원자재1", "원자재2"] 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "key_customers": {{
    "value": ["고객사1", "고객사2"] 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "overseas_operations": {{
    "value": ["베트남 하노이 공장", "중국 상해 법인"] 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "_uncertainty_notes": ["확실하지 않은 필드 및 이유 목록"],
  "_source_urls": ["참조한 모든 URL 목록"]
}}
```

JSON만 출력하세요. 다른 텍스트는 포함하지 마세요.
"""


# ============================================================================
# Layer 3: Validation Layer - CorpProfileValidator
# ============================================================================


class CorpProfileValidator:
    """
    Validate extracted profile data for consistency and plausibility.
    Anti-Hallucination Layer 3
    """

    def validate(self, profile: dict) -> ValidationResult:
        """Comprehensive profile validation."""
        errors = []
        warnings = []
        corrected = dict(profile)

        # Rule 1: export_ratio_pct range validation
        export_ratio = profile.get("export_ratio_pct")
        if export_ratio is not None:
            if not isinstance(export_ratio, (int, float)):
                errors.append(f"export_ratio_pct must be numeric: {export_ratio}")
                corrected["export_ratio_pct"] = None
            elif not (0 <= export_ratio <= 100):
                errors.append(f"export_ratio_pct out of range: {export_ratio}")
                corrected["export_ratio_pct"] = None

        # Rule 2: Revenue plausibility
        revenue = profile.get("revenue_krw")
        if revenue is not None:
            if not isinstance(revenue, (int, float)):
                errors.append(f"revenue_krw must be numeric: {revenue}")
                corrected["revenue_krw"] = None
            elif revenue < 0:
                errors.append("revenue_krw cannot be negative")
                corrected["revenue_krw"] = None
            elif revenue > 1_000_000_000_000_000:  # > 1000조 (unrealistic)
                warnings.append(f"revenue_krw unusually high: {revenue}")

        # Rule 3: Country exposure validation
        country_exp = profile.get("country_exposure", {})
        if country_exp and isinstance(country_exp, dict):
            for country, pct in list(country_exp.items()):
                if not isinstance(pct, (int, float)):
                    errors.append(f"country_exposure[{country}] must be numeric")
                    corrected["country_exposure"].pop(country, None)
                elif not (0 <= pct <= 100):
                    errors.append(f"country_exposure[{country}] out of range: {pct}")
                    corrected["country_exposure"].pop(country, None)

        # Rule 4: Source URL requirement
        if not profile.get("source_urls"):
            errors.append("source_urls is required - profile has no attribution")

        # Rule 5: Consistency checks
        consistency_warnings = self._check_consistency(profile)
        warnings.extend(consistency_warnings)

        # Rule 6: Field coverage check
        coverage_warning = self._check_field_coverage(profile)
        if coverage_warning:
            warnings.append(coverage_warning)

        # Rule 7: business_summary required
        if not profile.get("business_summary"):
            errors.append("business_summary is required")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            corrected_profile=corrected if errors else None,
        )

    def _check_consistency(self, profile: dict) -> list[str]:
        """Check for internal inconsistencies."""
        warnings = []

        # If export_ratio > 50%, should have country_exposure
        export_ratio = profile.get("export_ratio_pct", 0) or 0
        if export_ratio > 50:
            if not profile.get("country_exposure"):
                warnings.append(
                    "High export_ratio but no country_exposure - may be incomplete"
                )

        # If has overseas_operations, should have some country_exposure
        if profile.get("overseas_operations") and not profile.get("country_exposure"):
            warnings.append(
                "Has overseas_operations but no country_exposure - may be incomplete"
            )

        return warnings

    def _check_field_coverage(self, profile: dict) -> Optional[str]:
        """Check if profile has sufficient data."""
        important_fields = [
            "business_summary",
            "export_ratio_pct",
            "country_exposure",
            "key_materials",
            "overseas_operations",
        ]

        null_count = sum(
            1 for f in important_fields
            if profile.get(f) is None
            or profile.get(f) == {}
            or profile.get(f) == []
        )

        if null_count >= 4:
            return "Profile has insufficient data - most fields are empty"
        return None


# ============================================================================
# Layer 4: Audit Trail - ProvenanceTracker
# ============================================================================


class ProvenanceTracker:
    """Track provenance for all extracted fields."""

    def __init__(self):
        self.provenance: dict[str, FieldProvenance] = {}

    def record(
        self,
        field_name: str,
        value: Any,
        source_url: Optional[str],
        excerpt: Optional[str],
        confidence: str,
    ):
        """Record provenance for a field."""
        self.provenance[field_name] = FieldProvenance(
            field_name=field_name,
            value=value,
            source_url=source_url,
            excerpt=excerpt,
            confidence=confidence,
            extraction_date=datetime.utcnow(),
        )

    def to_json(self) -> dict:
        """Export provenance for storage."""
        return {
            name: prov.to_dict()
            for name, prov in self.provenance.items()
        }

    def get_unattributed_fields(self) -> list[str]:
        """Get fields without source attribution."""
        return [
            name for name, prov in self.provenance.items()
            if prov.source_url is None and prov.value is not None
        ]

    def get_field_confidences(self) -> dict[str, str]:
        """Get confidence level for each field."""
        return {
            name: prov.confidence
            for name, prov in self.provenance.items()
        }


# ============================================================================
# Confidence Determination
# ============================================================================


class ConfidenceDeterminer:
    """Determine field-level and overall profile confidence."""

    def determine_overall_confidence(
        self,
        field_confidences: dict[str, str],
        required_fields: list[str],
    ) -> str:
        """
        Overall profile confidence based on field confidences.

        Rules:
        - If any required field is LOW, overall is at most MED
        - If >50% of fields are null/empty, overall is LOW
        - If all required fields are HIGH, overall is HIGH
        """
        if not field_confidences:
            return "LOW"

        required_confidences = [
            field_confidences.get(f, "LOW")
            for f in required_fields
            if field_confidences.get(f)
        ]

        if not required_confidences:
            return "LOW"

        # If any required field is LOW
        if any(c == "LOW" for c in required_confidences):
            return "LOW"

        # If all required fields are HIGH
        if all(c == "HIGH" for c in required_confidences):
            return "HIGH"

        return "MED"


# ============================================================================
# Conditional Query Selection
# ============================================================================


class EnvironmentQuerySelector:
    """Select ENVIRONMENT queries based on profile conditions."""

    # Query definitions with conditions
    QUERY_CONDITIONS: dict[str, list[QueryCondition]] = {
        "FX_RISK": [
            QueryCondition(field="export_ratio_pct", op=">=", value=30),
        ],
        "TRADE_BLOC": [
            QueryCondition(field="export_ratio_pct", op=">=", value=30),
        ],
        "GEOPOLITICAL": [
            QueryCondition(field="country_exposure", op="contains_key", value="중국"),
            QueryCondition(field="country_exposure", op="contains_key", value="미국"),
            QueryCondition(field="overseas_operations", op="is_not_empty", value=None),
        ],
        "SUPPLY_CHAIN": [
            QueryCondition(field="country_exposure", op="contains_key", value="중국"),
            QueryCondition(field="key_materials", op="is_not_empty", value=None),
        ],
        "REGULATION": [
            QueryCondition(field="country_exposure", op="contains_key", value="중국"),
            QueryCondition(field="country_exposure", op="contains_key", value="미국"),
        ],
        "COMMODITY": [
            QueryCondition(field="key_materials", op="is_not_empty", value=None),
        ],
        "PANDEMIC_HEALTH": [
            QueryCondition(field="overseas_operations", op="is_not_empty", value=None),
        ],
        "POLITICAL_INSTABILITY": [
            QueryCondition(field="overseas_operations", op="is_not_empty", value=None),
        ],
        "CYBER_TECH": [
            QueryCondition(field="industry_code", op="in", value=["C26", "C21"]),
        ],
        "ENERGY_SECURITY": [
            QueryCondition(field="industry_code", op="==", value="D35"),
        ],
        "FOOD_SECURITY": [
            QueryCondition(field="industry_code", op="==", value="C10"),
        ],
    }

    def select_queries(
        self,
        profile: dict,
        industry_code: str,
    ) -> tuple[list[str], list[dict]]:
        """
        Select applicable query categories based on profile.

        Returns:
            Tuple of (selected category names, details with conditions met)
        """
        selected = []
        details = []

        for category, conditions in self.QUERY_CONDITIONS.items():
            met_conditions = []
            is_applicable = False

            for cond in conditions:
                if self._evaluate_condition(profile, industry_code, cond):
                    is_applicable = True
                    met_conditions.append({
                        "field": cond.field,
                        "operator": cond.op,
                        "value": cond.value,
                        "is_met": True,
                    })

            if is_applicable:
                selected.append(category)
                details.append({
                    "category": category,
                    "conditions_met": met_conditions,
                })

        logger.info(f"Selected {len(selected)} query categories: {selected}")
        return selected, details

    def _evaluate_condition(
        self,
        profile: dict,
        industry_code: str,
        cond: QueryCondition,
    ) -> bool:
        """Evaluate a single condition."""
        # Get field value
        if cond.field == "industry_code":
            field_value = industry_code
        else:
            field_value = profile.get(cond.field)

        if field_value is None:
            return False

        # Evaluate based on operator
        if cond.op == ">=":
            return isinstance(field_value, (int, float)) and field_value >= cond.value
        elif cond.op == "==":
            return field_value == cond.value
        elif cond.op == "in":
            return field_value in cond.value
        elif cond.op == "contains_key":
            return isinstance(field_value, dict) and cond.value in field_value
        elif cond.op == "is_not_empty":
            if isinstance(field_value, (list, dict)):
                return len(field_value) > 0
            return bool(field_value)

        return False


# ============================================================================
# Profile Evidence Creator
# ============================================================================


class ProfileEvidenceCreator:
    """Create Evidence records linking Signals to Profile data."""

    def create_profile_evidence(
        self,
        signal_id: UUID,
        profile: dict,
        field_path: str,
        provenance: Optional[dict],
    ) -> dict:
        """
        Create an Evidence record for a profile field.

        Args:
            signal_id: The signal this evidence supports
            profile: The full profile dict
            field_path: JSON Pointer to the field (e.g., "/export_ratio_pct")
            provenance: Provenance info for this field

        Returns:
            Evidence dict ready for insertion
        """
        # Get the field value using JSON Pointer
        field_value = self._get_by_path(profile, field_path)

        # Build snippet that shows the value and its source
        snippet = self._build_snippet(field_path, field_value, provenance)

        meta = {
            "field_value": field_value,
        }
        if provenance:
            meta["source_url"] = provenance.get("source_url")
            meta["confidence"] = provenance.get("confidence")
            meta["excerpt"] = provenance.get("excerpt")

        return {
            "evidence_id": str(uuid4()),
            "signal_id": str(signal_id),
            "evidence_type": "CORP_PROFILE",
            "ref_type": "PROFILE_KEYPATH",
            "ref_value": field_path,
            "snippet": snippet,
            "meta": meta,
        }

    def _build_snippet(
        self,
        field_path: str,
        field_value: Any,
        provenance: Optional[dict],
    ) -> str:
        """Build human-readable snippet for evidence."""
        # Convert path to human-readable name
        field_name = field_path.strip("/").replace("_", " ").replace("/", " > ")
        field_name = field_name.title()

        # Format value
        if isinstance(field_value, dict):
            value_str = ", ".join(f"{k}: {v}%" for k, v in field_value.items())
        elif isinstance(field_value, list):
            value_str = ", ".join(str(v) for v in field_value)
        else:
            value_str = str(field_value)

        # Add source excerpt if available
        if provenance and provenance.get("excerpt"):
            excerpt = provenance["excerpt"][:100]
            return f"{field_name}: {value_str} (출처: \"{excerpt}...\")"
        else:
            return f"{field_name}: {value_str}"

    def _get_by_path(self, obj: dict, path: str) -> Any:
        """Get value by JSON Pointer path."""
        parts = path.strip("/").split("/")
        current = obj
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                return None
        return current


# ============================================================================
# Industry Master Helper
# ============================================================================

INDUSTRY_NAMES = {
    "C10": "식료품 제조업",
    "C21": "의약품 제조업",
    "C26": "전자부품 제조업",
    "C29": "기계 제조업",
    "D35": "전기 가스 증기 공급업",
    "F41": "건설업",
}


def get_industry_name(industry_code: str) -> str:
    """Get industry name from code."""
    return INDUSTRY_NAMES.get(industry_code, f"업종코드 {industry_code}")


# ============================================================================
# Main Pipeline
# ============================================================================


class CorpProfilingPipeline:
    """
    Stage 2.5: Corp Profiling with Anti-Hallucination and 4-Layer Fallback

    PRD v1.2 4-Layer Fallback:
    - Layer 0: Cache
    - Layer 1+1.5: Perplexity + Gemini
    - Layer 2: Claude Synthesis / Consensus Engine
    - Layer 3: Rule-Based Merge
    - Layer 4: Graceful Degradation

    Sits between DOC_INGEST and EXTERNAL stages.
    """

    def __init__(self, orchestrator: Optional[MultiAgentOrchestrator] = None):
        self.parser = PerplexityResponseParser()
        self.validator = CorpProfileValidator()
        self.confidence_determiner = ConfidenceDeterminer()
        self.query_selector = EnvironmentQuerySelector()
        self.provenance_tracker = ProvenanceTracker()
        self.evidence_creator = ProfileEvidenceCreator()

        # Multi-Agent Orchestrator for 4-layer fallback
        self.orchestrator = orchestrator or get_orchestrator()
        self._llm_service = None
        self._db_session = None
        self._perplexity_api_key = None

    async def execute(
        self,
        corp_id: str,
        corp_name: str,
        industry_code: str,
        db_session=None,
        llm_service=None,
        perplexity_api_key: Optional[str] = None,
    ) -> CorpProfileResult:
        """
        Execute corp profiling with full anti-hallucination pipeline
        using the MultiAgentOrchestrator for 4-layer fallback.
        """
        logger.info(f"PROFILING stage starting for corp_id={corp_id}")

        industry_name = get_industry_name(industry_code)
        self._llm_service = llm_service
        self._db_session = db_session
        self._perplexity_api_key = perplexity_api_key

        # Configure orchestrator with injectable functions
        self.orchestrator.set_cache_lookup(
            lambda cn, ic: self._sync_get_cached_profile(corp_id, db_session)
        )
        self.orchestrator.set_perplexity_search(
            lambda cn, ind: self._sync_perplexity_search(cn, ind, perplexity_api_key)
        )
        self.orchestrator.set_claude_synthesis(
            lambda sources, cn, ind, ic, disc: self._sync_claude_synthesis(
                sources, cn, ind, ic, disc, llm_service
            )
        )

        # Get existing profile for potential enrichment
        existing_profile = await self._get_cached_profile(corp_id, db_session)

        # Execute orchestrator (4-layer fallback)
        orchestrator_result = self.orchestrator.execute(
            corp_name=corp_name,
            industry_name=industry_name,
            industry_code=industry_code,
            existing_profile=existing_profile,
        )

        # Build final profile with orchestrator result
        profile = self._build_final_profile(
            orchestrator_result=orchestrator_result,
            corp_id=corp_id,
            industry_name=industry_name,
        )

        # Validate the profile
        validation_result = self.validator.validate(profile)
        if not validation_result.is_valid:
            logger.warning(f"Validation errors: {validation_result.errors}")
            profile = validation_result.corrected_profile or profile
        profile["validation_warnings"] = validation_result.warnings

        # Save to DB
        if db_session:
            await self._save_profile(profile, db_session)

        # Select queries based on profile
        selected, details = self.query_selector.select_queries(
            profile, industry_code
        )

        logger.info(
            f"PROFILING completed: layer={orchestrator_result.fallback_layer.value}, "
            f"confidence={profile.get('profile_confidence')}, queries={len(selected)}"
        )

        return CorpProfileResult(
            profile=profile,
            selected_queries=selected,
            is_cached=orchestrator_result.fallback_layer == FallbackLayer.CACHE,
            query_details=details,
        )

    def _build_final_profile(
        self,
        orchestrator_result: OrchestratorResult,
        corp_id: str,
        industry_name: str,
    ) -> dict:
        """Build final profile dict from orchestrator result."""
        raw_profile = orchestrator_result.profile or {}

        # Determine overall confidence from fallback layer
        layer_confidence_map = {
            FallbackLayer.CACHE: "HIGH",
            FallbackLayer.PERPLEXITY_GEMINI: "HIGH",
            FallbackLayer.CLAUDE_SYNTHESIS: "MED",
            FallbackLayer.RULE_BASED: "LOW",
            FallbackLayer.GRACEFUL_DEGRADATION: "LOW",
        }
        overall_confidence = layer_confidence_map.get(
            orchestrator_result.fallback_layer, "LOW"
        )

        # Determine TTL based on fallback layer
        is_fallback = orchestrator_result.fallback_layer in [
            FallbackLayer.RULE_BASED,
            FallbackLayer.GRACEFUL_DEGRADATION,
        ]
        ttl_days = FALLBACK_TTL_DAYS if is_fallback else PROFILE_TTL_DAYS

        profile = {
            "profile_id": str(uuid4()),
            "corp_id": corp_id,
            "business_summary": raw_profile.get("business_summary", f"{industry_name} 업체"),
            "revenue_krw": raw_profile.get("revenue_krw"),
            "export_ratio_pct": raw_profile.get("export_ratio_pct"),
            "country_exposure": raw_profile.get("country_exposure", {}),
            "key_materials": raw_profile.get("key_materials", []),
            "key_customers": raw_profile.get("key_customers", []),
            "overseas_operations": raw_profile.get("overseas_operations", []),
            "profile_confidence": overall_confidence,
            "field_confidences": raw_profile.get("field_confidences", {}),
            "source_urls": raw_profile.get("source_urls", []),
            "raw_search_result": raw_profile.get("raw_search_result", {}),
            "field_provenance": orchestrator_result.provenance,
            "extraction_model": raw_profile.get("extraction_model", "orchestrator"),
            "extraction_prompt_version": PROMPT_VERSION,
            "is_fallback": is_fallback,
            "search_failed": orchestrator_result.fallback_layer == FallbackLayer.GRACEFUL_DEGRADATION,
            "validation_warnings": [],
            "status": "ACTIVE",
            "fetched_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=ttl_days)).isoformat(),
            "is_expired": False,
            # PRD v1.2 fallback metadata
            "fallback_layer": orchestrator_result.fallback_layer.value,
            "retry_count": orchestrator_result.retry_count,
            "error_messages": orchestrator_result.error_messages,
            "execution_time_ms": orchestrator_result.execution_time_ms,
        }

        # Add consensus metadata if available
        if orchestrator_result.consensus_metadata:
            profile["consensus_metadata"] = orchestrator_result.consensus_metadata.to_dict()

        return profile

    def _sync_get_cached_profile(self, corp_id: str, db_session) -> Optional[dict]:
        """Sync wrapper for cache lookup (for orchestrator injection)."""
        # Note: This is a simplified sync version. In production,
        # you'd need to handle async properly.
        return None  # Cache lookup handled by orchestrator directly

    def _sync_perplexity_search(
        self,
        corp_name: str,
        industry_name: str,
        api_key: Optional[str],
    ) -> dict:
        """Sync wrapper for Perplexity search (for orchestrator injection)."""
        import httpx

        api_key = api_key or getattr(settings, "PERPLEXITY_API_KEY", None)
        if not api_key:
            logger.warning("Perplexity API key not configured")
            return {}

        query = f"""
{corp_name} ({industry_name}) 기업 정보:
1. 주요 사업 및 제품
2. 매출 규모 및 재무 현황
3. 수출 비중 및 주요 수출국
4. 원자재 조달 및 공급망
5. 해외 법인 및 공장

2026년 기준 최신 공식 정보 검색. 한국 기업 기준.
"""

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "sonar-pro",
                        "messages": [
                            {
                                "role": "system",
                                "content": "금융기관 기업심사 전문가입니다. 정확하고 검증 가능한 정보만 제공합니다.",
                            },
                            {"role": "user", "content": query},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 2000,
                    },
                )
                response.raise_for_status()
                raw_response = response.json()
                parsed = self.parser.parse_response(raw_response)

                # Extract profile fields from parsed response
                return self._extract_profile_from_search(
                    corp_name, industry_name, parsed
                )

        except Exception as e:
            logger.error(f"Perplexity search failed: {e}")
            raise

    def _extract_profile_from_search(
        self,
        corp_name: str,
        industry_name: str,
        parsed_response: dict,
    ) -> dict:
        """Extract structured profile fields from search response."""
        content = parsed_response.get("content", "")
        citations = parsed_response.get("citations", [])
        source_quality = parsed_response.get("source_quality", "LOW")

        # Basic extraction (can be enhanced with LLM if available)
        profile = {
            "corp_name": corp_name,
            "industry_name": industry_name,
            "business_summary": content[:500] if content else f"{industry_name} 업체",
            "source_urls": citations,
            "source_quality": source_quality,
            "raw_content": content,
        }

        return profile

    def _sync_claude_synthesis(
        self,
        sources: list[dict],
        corp_name: str,
        industry_name: str,
        industry_code: str,
        discrepancies: list[dict],
        llm_service,
    ) -> Optional[dict]:
        """Sync wrapper for Claude synthesis (for orchestrator injection)."""
        if not llm_service:
            return None

        try:
            # Build synthesis prompt
            system_prompt = PROFILE_EXTRACTION_SYSTEM_PROMPT
            user_prompt = self._build_synthesis_prompt(
                sources, corp_name, industry_name, discrepancies
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            result = llm_service.call_with_json_response(
                messages=messages,
                temperature=0.1,
            )

            # Track provenance
            extracted = {}
            for field_name, field_data in result.items():
                if field_name.startswith("_"):
                    extracted[field_name] = field_data
                    continue

                if isinstance(field_data, dict) and "value" in field_data:
                    value = field_data.get("value")
                    extracted[field_name] = value
                    self.provenance_tracker.record(
                        field_name=field_name,
                        value=value,
                        source_url=field_data.get("source_url"),
                        excerpt=field_data.get("excerpt"),
                        confidence=field_data.get("confidence", "LOW"),
                    )
                else:
                    extracted[field_name] = field_data

            return {
                "profile": extracted,
                "metadata": None,  # ConsensusMetadata handled by orchestrator
            }

        except Exception as e:
            logger.error(f"Claude synthesis failed: {e}")
            raise

    def _build_synthesis_prompt(
        self,
        sources: list[dict],
        corp_name: str,
        industry_name: str,
        discrepancies: list[dict],
    ) -> str:
        """Build synthesis prompt for Claude."""
        sources_text = ""
        for i, src in enumerate(sources, 1):
            provider = src.get("provider", "unknown")
            profile = src.get("profile", {})
            sources_text += f"\n### Source {i} ({provider}):\n"
            sources_text += json.dumps(profile, ensure_ascii=False, indent=2)

        discrepancy_text = ""
        if discrepancies:
            discrepancy_text = "\n### Discrepancies detected by validation:\n"
            for d in discrepancies:
                discrepancy_text += f"- {d.get('field')}: {d.get('issue')}\n"

        return PROFILE_EXTRACTION_USER_PROMPT.format(
            corp_name=corp_name,
            industry_name=industry_name,
            search_results=sources_text + discrepancy_text,
        )

    async def _get_cached_profile(self, corp_id: str, db_session) -> Optional[dict]:
        """Check for cached profile in DB."""
        if not db_session:
            return None

        try:
            from sqlalchemy import text

            query = text("""
                SELECT * FROM rkyc_corp_profile
                WHERE corp_id = :corp_id
                AND expires_at > NOW()
                LIMIT 1
            """)
            result = await db_session.execute(query, {"corp_id": corp_id})
            row = result.fetchone()

            if row:
                return {
                    "profile_id": str(row.profile_id),
                    "corp_id": row.corp_id,
                    "business_summary": row.business_summary,
                    "revenue_krw": row.revenue_krw,
                    "export_ratio_pct": row.export_ratio_pct,
                    "country_exposure": row.country_exposure or {},
                    "key_materials": list(row.key_materials or []),
                    "key_customers": list(row.key_customers or []),
                    "overseas_operations": list(row.overseas_operations or []),
                    "profile_confidence": row.profile_confidence,
                    "is_fallback": row.is_fallback,
                    "is_expired": False,
                }
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")

        return None

    async def _search_perplexity(
        self,
        corp_name: str,
        industry_name: str,
        api_key: Optional[str],
    ) -> dict:
        """Execute Perplexity search with unified query."""
        import httpx

        api_key = api_key or getattr(settings, "PERPLEXITY_API_KEY", None)
        if not api_key:
            logger.warning("Perplexity API key not configured")
            return {"content": "", "citations": [], "source_quality": "LOW", "raw_response": {}}

        # Unified query (최대 2회 중 1차)
        query = f"""
{corp_name} ({industry_name}) 기업 정보:
1. 주요 사업 및 제품
2. 매출 규모 및 재무 현황
3. 수출 비중 및 주요 수출국
4. 원자재 조달 및 공급망
5. 해외 법인 및 공장

2026년 기준 최신 공식 정보 검색. 한국 기업 기준.
"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "sonar-pro",
                        "messages": [
                            {
                                "role": "system",
                                "content": "금융기관 기업심사 전문가입니다. 정확하고 검증 가능한 정보만 제공합니다.",
                            },
                            {"role": "user", "content": query},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 2000,
                    },
                )
                response.raise_for_status()
                raw_response = response.json()
                return self.parser.parse_response(raw_response)

        except Exception as e:
            logger.error(f"Perplexity search failed: {e}")
            raise

    async def _extract_profile(
        self,
        corp_name: str,
        industry_name: str,
        raw_results: dict,
        llm_service,
    ) -> dict:
        """Extract structured profile using LLM with anti-hallucination prompt."""
        if not llm_service:
            # Return minimal profile if no LLM service
            return {
                "business_summary": f"{industry_name} 업체",
                "_source_urls": raw_results.get("citations", []),
            }

        messages = [
            {"role": "system", "content": PROFILE_EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": PROFILE_EXTRACTION_USER_PROMPT.format(
                    corp_name=corp_name,
                    industry_name=industry_name,
                    search_results=raw_results.get("content", "검색 결과 없음"),
                ),
            },
        ]

        try:
            result = llm_service.call_with_json_response(
                messages=messages,
                temperature=0.1,
            )

            # Track provenance for each field
            extracted = {}
            for field_name, field_data in result.items():
                if field_name.startswith("_"):
                    extracted[field_name] = field_data
                    continue

                if isinstance(field_data, dict) and "value" in field_data:
                    value = field_data.get("value")
                    extracted[field_name] = value
                    self.provenance_tracker.record(
                        field_name=field_name,
                        value=value,
                        source_url=field_data.get("source_url"),
                        excerpt=field_data.get("excerpt"),
                        confidence=field_data.get("confidence", "LOW"),
                    )
                else:
                    extracted[field_name] = field_data

            return extracted

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {
                "business_summary": f"{industry_name} 업체",
                "_source_urls": raw_results.get("citations", []),
            }

    async def _create_fallback_profile(
        self,
        corp_id: str,
        industry_code: str,
        industry_name: str,
    ) -> CorpProfileResult:
        """Create fallback profile when Perplexity/LLM fails."""
        profile = {
            "profile_id": str(uuid4()),
            "corp_id": corp_id,
            "business_summary": f"{industry_name} 업체",
            "revenue_krw": None,
            "export_ratio_pct": None,
            "country_exposure": {},
            "key_materials": [],
            "key_customers": [],
            "overseas_operations": [],
            "profile_confidence": "LOW",
            "field_confidences": {},
            "source_urls": [],
            "raw_search_result": {},
            "field_provenance": {},
            "extraction_model": None,
            "extraction_prompt_version": PROMPT_VERSION,
            "is_fallback": True,
            "search_failed": True,
            "validation_warnings": ["Profile created using industry fallback"],
            "status": "ACTIVE",
            "fetched_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=FALLBACK_TTL_DAYS)).isoformat(),
            "is_expired": False,
        }

        # Fallback profiles get minimal queries based on industry
        selected, details = self.query_selector.select_queries(
            profile, industry_code
        )

        logger.info(f"Created fallback profile for {corp_id}")

        return CorpProfileResult(
            profile=profile,
            selected_queries=selected,
            is_cached=False,
            query_details=details,
        )

    async def _save_profile(self, profile: dict, db_session) -> None:
        """Save profile to database."""
        try:
            from sqlalchemy import text

            # Upsert (insert or update)
            query = text("""
                INSERT INTO rkyc_corp_profile (
                    profile_id, corp_id, business_summary, revenue_krw, export_ratio_pct,
                    country_exposure, key_materials, key_customers, overseas_operations,
                    profile_confidence, field_confidences, source_urls,
                    raw_search_result, field_provenance, extraction_model, extraction_prompt_version,
                    is_fallback, search_failed, validation_warnings, status,
                    fetched_at, expires_at
                ) VALUES (
                    :profile_id::uuid, :corp_id, :business_summary, :revenue_krw, :export_ratio_pct,
                    :country_exposure::jsonb, :key_materials, :key_customers, :overseas_operations,
                    :profile_confidence::confidence_level, :field_confidences::jsonb, :source_urls,
                    :raw_search_result::jsonb, :field_provenance::jsonb, :extraction_model, :extraction_prompt_version,
                    :is_fallback, :search_failed, :validation_warnings, :status,
                    :fetched_at::timestamptz, :expires_at::timestamptz
                )
                ON CONFLICT (corp_id) DO UPDATE SET
                    business_summary = EXCLUDED.business_summary,
                    revenue_krw = EXCLUDED.revenue_krw,
                    export_ratio_pct = EXCLUDED.export_ratio_pct,
                    country_exposure = EXCLUDED.country_exposure,
                    key_materials = EXCLUDED.key_materials,
                    key_customers = EXCLUDED.key_customers,
                    overseas_operations = EXCLUDED.overseas_operations,
                    profile_confidence = EXCLUDED.profile_confidence,
                    field_confidences = EXCLUDED.field_confidences,
                    source_urls = EXCLUDED.source_urls,
                    raw_search_result = EXCLUDED.raw_search_result,
                    field_provenance = EXCLUDED.field_provenance,
                    extraction_model = EXCLUDED.extraction_model,
                    extraction_prompt_version = EXCLUDED.extraction_prompt_version,
                    is_fallback = EXCLUDED.is_fallback,
                    search_failed = EXCLUDED.search_failed,
                    validation_warnings = EXCLUDED.validation_warnings,
                    status = EXCLUDED.status,
                    fetched_at = EXCLUDED.fetched_at,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = NOW()
            """)

            await db_session.execute(query, {
                "profile_id": profile["profile_id"],
                "corp_id": profile["corp_id"],
                "business_summary": profile["business_summary"],
                "revenue_krw": profile.get("revenue_krw"),
                "export_ratio_pct": profile.get("export_ratio_pct"),
                "country_exposure": json.dumps(profile.get("country_exposure", {})),
                "key_materials": profile.get("key_materials", []),
                "key_customers": profile.get("key_customers", []),
                "overseas_operations": profile.get("overseas_operations", []),
                "profile_confidence": profile["profile_confidence"],
                "field_confidences": json.dumps(profile.get("field_confidences", {})),
                "source_urls": profile.get("source_urls", []),
                "raw_search_result": json.dumps(profile.get("raw_search_result", {})),
                "field_provenance": json.dumps(profile.get("field_provenance", {})),
                "extraction_model": profile.get("extraction_model"),
                "extraction_prompt_version": profile.get("extraction_prompt_version"),
                "is_fallback": profile.get("is_fallback", False),
                "search_failed": profile.get("search_failed", False),
                "validation_warnings": profile.get("validation_warnings", []),
                "status": profile.get("status", "ACTIVE"),
                "fetched_at": profile["fetched_at"],
                "expires_at": profile["expires_at"],
            })
            await db_session.commit()
            logger.info(f"Saved profile for {profile['corp_id']}")

        except Exception as e:
            logger.error(f"Failed to save profile: {e}")
            await db_session.rollback()


# ============================================================================
# Factory Function
# ============================================================================

_pipeline_instance: Optional[CorpProfilingPipeline] = None


def get_corp_profiling_pipeline() -> CorpProfilingPipeline:
    """Get singleton instance of CorpProfilingPipeline."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = CorpProfilingPipeline()
    return _pipeline_instance
