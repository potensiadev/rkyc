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
from datetime import datetime, timedelta, UTC
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
# Helper Functions (PRD Bug Fixes)
# ============================================================================


def safe_json_dumps(value: Any) -> str:
    """
    JSON 직렬화 (이중 직렬화 방지) - P0-3 Fix

    Args:
        value: dict, list, str, or None

    Returns:
        JSON string (이미 JSON 문자열이면 그대로 반환)
    """
    if value is None:
        return '{}'
    if isinstance(value, str):
        # 이미 JSON 문자열인지 확인
        try:
            json.loads(value)
            return value  # 유효한 JSON 문자열이면 그대로 반환
        except (json.JSONDecodeError, ValueError):
            # JSON이 아니면 문자열을 JSON으로 직렬화
            return json.dumps(value, ensure_ascii=False, default=str)
    return json.dumps(value, ensure_ascii=False, default=str)


def parse_datetime_safely(dt_string: str | None) -> datetime | None:
    """
    datetime 파싱 ("Z" suffix 지원) - P1-3 Fix

    Python 3.10 이하에서는 fromisoformat()이 "Z" suffix를 지원하지 않음.

    Args:
        dt_string: ISO format datetime string (e.g., "2026-01-21T12:00:00Z")

    Returns:
        datetime object or None
    """
    if not dt_string:
        return None
    try:
        # "Z"를 "+00:00"으로 치환 (Python 3.10 호환)
        if isinstance(dt_string, str) and dt_string.endswith("Z"):
            dt_string = dt_string[:-1] + "+00:00"
        return datetime.fromisoformat(dt_string)
    except (ValueError, TypeError):
        return None


def normalize_single_source_risk(value: Any) -> list[str]:
    """
    single_source_risk 타입 정규화 - P0-1 Fix

    LLM이 boolean, string, list 등 다양한 타입으로 반환할 수 있음.
    모두 list[str]로 정규화.

    Args:
        value: boolean, string, or list

    Returns:
        list[str]
    """
    if value is None:
        return []
    if isinstance(value, bool):
        return ["단일 조달처 위험 있음"] if value else []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []


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

# Domains to exclude from citations (blogs, user-generated content)
EXCLUDED_DOMAINS = [
    "blog.naver.com",
    "m.blog.naver.com",
    "blog.daum.net",
    "tistory.com",
    "brunch.co.kr",
    "velog.io",
    "medium.com",
    "wordpress.com",
    "blogspot.com",
    "cafe.naver.com",
    "cafe.daum.net",
    "dcinside.com",
    "fmkorea.com",
    "clien.net",
    "ruliweb.com",
    "ppomppu.co.kr",
    "instiz.net",
    "theqoo.net",
    "reddit.com",
    "quora.com",
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
    extraction_date: datetime = field(default_factory=lambda: datetime.now(UTC))

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

    def parse_response(self, raw_response: dict, exclude_blogs: bool = True) -> dict:
        """Extract content, citations, and assess source quality.

        Args:
            raw_response: Raw Perplexity API response
            exclude_blogs: If True, filter out blog/community URLs from citations
        """
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

        # Filter out blog/community URLs if requested
        if exclude_blogs:
            original_count = len(citations)
            citations = self._filter_excluded_domains(citations)
            filtered_count = original_count - len(citations)
            if filtered_count > 0:
                logger.info(f"Filtered {filtered_count} blog/community URLs from citations")

        source_quality = self._assess_source_quality(citations)

        return {
            "content": content,
            "citations": citations,
            "filtered_blog_count": filtered_count if exclude_blogs else 0,
            "source_quality": source_quality,
            "raw_response": raw_response,
        }

    def _extract_urls_from_content(self, content: str) -> list[str]:
        """Extract URLs from content text."""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        return list(set(urls))[:10]  # Limit to 10 unique URLs

    def _filter_excluded_domains(self, urls: list[str]) -> list[str]:
        """Filter out blog/community URLs from the list."""
        filtered = []
        for url in urls:
            url_lower = url.lower()
            is_excluded = any(domain in url_lower for domain in EXCLUDED_DOMAINS)
            if not is_excluded:
                filtered.append(url)
        return filtered

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

## 핵심 원칙: 적극적 추출 + 신뢰도 표시
검색 결과에 정보가 있으면 **반드시 추출**하고, 신뢰도(confidence)로 정확성을 표시하세요.
null은 정보가 **완전히 없는 경우에만** 사용합니다.

## 규칙 1: 숫자 데이터 - 적극 추출
다음 필드는 검색 결과에 숫자가 언급되면 **반드시 추출**하세요:

**revenue_krw (연간 매출액, 원화)**
- "매출 3,000억원" → 300000000000
- "매출 약 3천억" → 300000000000 (confidence: MED)
- "수조원대 매출" → 추정값 사용 (confidence: LOW)

**export_ratio_pct (수출 비중 %)**
- "수출 80%" → 80
- "수출 80% 이상" → 80 (confidence: MED)
- "수출 중심 기업" → 70 추정 (confidence: LOW)

**employee_count (임직원 수)**
- "직원 800명" → 800
- "약 800명 규모" → 800 (confidence: MED)
- "수백 명" → 500 추정 (confidence: LOW)

## 규칙 2: 신뢰도 판단 기준
- **HIGH**: DART 공시, IR 자료, 사업보고서에서 직접 인용
- **MED**: "사업보고서에 따르면...", 언론 보도, "약 X", "X 이상"
- **LOW**: 추정치, 간접 정보, "수백 명", "수천억대"

## 규칙 3: 모든 필드 적극 추출
다음 필드들은 검색 결과에 조금이라도 관련 정보가 있으면 추출하세요:
- supply_chain: 원자재, 부품, 공급사 언급 시 추출
- overseas_business: 해외 법인, 해외 프로젝트 언급 시 추출
- shareholders: 대주주, 최대주주, 지분 구조 언급 시 추출
- key_materials: 업종별 주요 원자재
- key_customers: 주요 고객사, 납품처
- competitors: 경쟁사

## 규칙 4: 출처 정보
- source_url: 가능하면 URL 포함, 없으면 null
- excerpt: 값을 뒷받침하는 텍스트 (최대 200자)

## 중요: null 최소화
- 검색 결과에 힌트가 있으면 **추출 + confidence 표시**
- null은 검색 결과에 관련 정보가 **전혀 없을 때만** 사용
- 빈 배열([])보다 추출된 데이터가 더 가치 있음
"""

PROFILE_EXTRACTION_USER_PROMPT = """## 검색 결과
{search_results}

## 추출 대상 기업
기업명: {corp_name}
업종: {industry_name}

## 출력 스키마 (PRD v1.2 - 19개 필드)
다음 JSON 형식으로만 응답하세요. 모든 필드에 대해 value, confidence, source_url, excerpt를 포함해야 합니다.
확실하지 않은 정보는 value를 null로 설정하세요.

```json
{{
  "business_summary": {{
    "value": "string (100자 이내, 주요 사업 및 제품 설명) 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "revenue_krw": {{
    "value": "integer (연간 매출액, 원화) 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "export_ratio_pct": {{
    "value": "integer 0-100 (수출 비중 %) 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "ceo_name": {{
    "value": "string (대표이사명) 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "employee_count": {{
    "value": "integer (임직원 수) 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "founded_year": {{
    "value": "integer (설립연도, YYYY) 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "headquarters": {{
    "value": "string (본사 위치) 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "executives": {{
    "value": [{{"name": "이름", "title": "직함"}}] 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "industry_overview": {{
    "value": "string (업종 현황 및 시장 동향) 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "business_model": {{
    "value": "string (수익 모델 및 비즈니스 구조) 또는 null",
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "country_exposure": {{
    "value": {{"국가명": 비중(%)}} (국가별 매출/사업 노출도) 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "key_materials": {{
    "value": ["원자재1", "원자재2"] (주요 원자재) 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "key_customers": {{
    "value": ["고객사1", "고객사2"] (주요 고객사) 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "overseas_operations": {{
    "value": ["베트남 하노이 공장", "중국 상해 법인"] (해외 사업장) 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "supply_chain": {{
    "value": {{
      "key_suppliers": ["공급사1", "공급사2"],
      "supplier_countries": {{"국가명": 비중(%)}},
      "single_source_risk": ["단일 조달처 위험 품목1", "단일 조달처 위험 품목2"] (단일 공급처에 의존하는 원자재/부품 목록) 또는 [],
      "material_import_ratio_pct": "integer 0-100 (원자재 수입 비율)"
    }} 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "overseas_business": {{
    "value": {{
      "subsidiaries": [{{"name": "법인명", "country": "국가", "type": "생산/판매/R&D"}}],
      "manufacturing_countries": ["국가1", "국가2"]
    }} 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "shareholders": {{
    "value": [{{"name": "주주명", "ratio_pct": 지분율}}] 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "competitors": {{
    "value": [{{"name": "경쟁사명", "description": "경쟁 영역"}}] 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "macro_factors": {{
    "value": [{{"factor": "요인명", "impact": "POSITIVE|NEGATIVE|NEUTRAL", "description": "설명"}}] 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "뒷받침 텍스트 또는 null"
  }},
  "financial_history": {{
    "value": [{{"year": 2024, "revenue_krw": 금액, "operating_profit_krw": 금액, "net_profit_krw": 금액}}] (최근 3개년) 또는 null,
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
            extraction_date=datetime.now(UTC),
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


def build_perplexity_query(corp_name: str, industry_name: str) -> str:
    """Build comprehensive Perplexity search query for PRD v1.2 (19 fields)."""
    return f"""
{corp_name} ({industry_name}) 기업 종합 정보 (한국 기업, 2026년 기준):

[기본 정보] - 필수
- 대표이사 이름
- 설립연도
- 본사 위치 (시/도 단위)
- 임직원 수 (정규직 기준)
- 주요 경영진 (이름, 직함)

[사업 현황]
- 주요 사업 및 제품/서비스 설명
- 비즈니스 모델 및 수익 구조
- 업종 현황 및 시장 동향

[재무 정보]
- 연간 매출액 (최근 3개년, 원화)
- 영업이익, 순이익

[공급망 정보] - 중요! 반드시 찾아주세요
- 주요 공급사 회사명 (원자재, 부품, 자재 공급하는 회사)
- 공급사 국가 비중 (국내/해외)
- 단일 조달처 위험 여부 (특정 공급사에 의존하는 품목)
- 주요 원자재/자재 (건설: 철강, 시멘트, 레미콘 / 제조: 반도체, 부품 등)
- 원자재 수입 비율 (%)

[주주 정보] - 중요! 반드시 찾아주세요
- 최대주주 및 지분율
- 주요 주주 명단 (개인, 기관, 계열사 등)
- 지분 구조

[해외 사업] - 중요!
- 수출 비중 (%)
- 국가별 매출/사업 노출도 (중국, 미국, 베트남 등)
- 해외 법인 명단 (법인명, 국가, 사업유형)
- 해외 공장/생산 국가
- 해외 프로젝트

[고객 및 경쟁]
- 주요 고객사 (발주처, 납품처)
- 주요 경쟁사

[거시 요인]
- 기업에 영향을 미치는 거시경제/정책 요인 (긍정/부정 구분)

공식 출처(DART, 금감원, 기업 IR 자료, 사업보고서, 주요 언론)의 정보를 검색해주세요.
특히 공급망, 주주 정보, 해외 사업 관련 정보를 반드시 찾아주세요.
"""


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
        skip_cache: bool = False,
    ) -> CorpProfileResult:
        """
        Execute corp profiling with full anti-hallucination pipeline
        using the MultiAgentOrchestrator for 4-layer fallback.

        Args:
            corp_id: 기업 ID
            corp_name: 기업명
            industry_code: 업종코드
            db_session: DB 세션 (옵션)
            llm_service: LLM 서비스 (옵션)
            perplexity_api_key: Perplexity API 키 (옵션)
            skip_cache: True면 캐시 무시하고 항상 새로 검색
        """
        logger.info(f"PROFILING stage starting for corp_id={corp_id}, skip_cache={skip_cache}")

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
            lambda sources, corp_name, industry_name, industry_code, gemini_discrepancies: self._sync_claude_synthesis(
                sources, corp_name, industry_name, industry_code, gemini_discrepancies, llm_service
            )
        )

        # Get existing profile for potential enrichment (but don't use as cache if skip_cache)
        existing_profile = None if skip_cache else await self._get_cached_profile(corp_id, db_session)

        # Execute orchestrator (4-layer fallback)
        orchestrator_result = self.orchestrator.execute(
            corp_name=corp_name,
            industry_name=industry_name,
            industry_code=industry_code,
            existing_profile=existing_profile,
            skip_cache=skip_cache,
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
            # Basic info
            "business_summary": raw_profile.get("business_summary", f"{industry_name} 업체"),
            "revenue_krw": raw_profile.get("revenue_krw"),
            "export_ratio_pct": raw_profile.get("export_ratio_pct"),
            # PRD v1.2 new fields - Basic info
            "ceo_name": raw_profile.get("ceo_name"),
            "employee_count": raw_profile.get("employee_count"),
            "founded_year": raw_profile.get("founded_year"),
            "headquarters": raw_profile.get("headquarters"),
            "executives": raw_profile.get("executives", []),
            # PRD v1.2 new fields - Value chain
            "industry_overview": raw_profile.get("industry_overview"),
            "business_model": raw_profile.get("business_model"),
            "financial_history": raw_profile.get("financial_history", []),
            "competitors": raw_profile.get("competitors", []),
            "macro_factors": raw_profile.get("macro_factors", []),
            # Original fields
            "country_exposure": raw_profile.get("country_exposure", {}),
            "key_materials": raw_profile.get("key_materials", []),
            "key_customers": raw_profile.get("key_customers", []),
            "overseas_operations": raw_profile.get("overseas_operations", []),
            # PRD v1.2 new fields - Supply chain & Overseas
            "supply_chain": raw_profile.get("supply_chain", {}),
            "overseas_business": raw_profile.get("overseas_business", {}),
            "shareholders": raw_profile.get("shareholders", []),
            # Metadata
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
            "fetched_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(days=ttl_days)).isoformat(),
            "is_expired": False,
            # PRD v1.2 fallback metadata
            "fallback_layer": orchestrator_result.fallback_layer.value,
            "retry_count": orchestrator_result.retry_count,
            "error_messages": orchestrator_result.error_messages,
            "execution_time_ms": orchestrator_result.execution_time_ms,
        }

        # P1-1 Fix: consensus_metadata 기본값 추가
        if orchestrator_result.consensus_metadata:
            profile["consensus_metadata"] = orchestrator_result.consensus_metadata.to_dict()
        else:
            # 캐시 히트 또는 메타데이터 없는 경우 기본값
            is_cache_hit = orchestrator_result.fallback_layer == FallbackLayer.CACHE
            profile["consensus_metadata"] = {
                "consensus_at": None,
                "perplexity_success": False,
                "gemini_success": False,
                "claude_success": False,
                "total_fields": 0,
                "matched_fields": 0,
                "discrepancy_fields": 0,
                "enriched_fields": 0,
                "overall_confidence": "CACHED" if is_cache_hit else overall_confidence,
                "fallback_layer": orchestrator_result.fallback_layer.value if orchestrator_result.fallback_layer else 0,
                "retry_count": orchestrator_result.retry_count,
                "error_messages": orchestrator_result.error_messages or [],
            }

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

        # PRD v1.2: 19개 필드를 위한 종합 쿼리
        query = build_perplexity_query(corp_name, industry_name)

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
        """Extract structured profile fields from search response using LLM."""
        content = parsed_response.get("content", "")
        citations = parsed_response.get("citations", [])
        source_quality = parsed_response.get("source_quality", "LOW")

        logger.info(f"[Profile Extraction] corp={corp_name}, has_llm={self._llm_service is not None}, content_len={len(content)}")

        # Try LLM extraction if service available
        if self._llm_service and content:
            try:
                llm_profile = self._extract_with_llm(content, corp_name, industry_name, citations)
                if llm_profile:
                    llm_profile["source_urls"] = citations
                    llm_profile["source_quality"] = source_quality
                    llm_profile["raw_content"] = content
                    return llm_profile
            except Exception as e:
                logger.warning(f"LLM extraction failed, using basic extraction: {e}")

        # Fallback to basic extraction
        profile = {
            "corp_name": corp_name,
            "industry_name": industry_name,
            "business_summary": content[:500] if content else f"{industry_name} 업체",
            "source_urls": citations,
            "source_quality": source_quality,
            "raw_content": content,
        }

        return profile

    def _extract_with_llm(
        self,
        content: str,
        corp_name: str,
        industry_name: str,
        citations: list[str],
    ) -> Optional[dict]:
        """Use LLM to extract structured profile from search content."""
        system_prompt = PROFILE_EXTRACTION_SYSTEM_PROMPT
        user_prompt = PROFILE_EXTRACTION_USER_PROMPT.format(
            search_results=content[:8000],  # Limit content length
            corp_name=corp_name,
            industry_name=industry_name,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            result = self._llm_service.call_with_json_response(
                messages=messages,
                temperature=0.1,
            )

            if not result:
                return None

            # Extract values from structured response
            profile = {
                "corp_name": corp_name,
                "industry_name": industry_name,
            }

            # Map fields with value extraction
            field_mapping = [
                "business_summary", "revenue_krw", "export_ratio_pct",
                "country_exposure", "key_materials", "key_customers",
                "overseas_operations", "ceo_name", "employee_count",
                "founded_year", "headquarters", "executives",
                "industry_overview", "business_model", "financial_history",
                "competitors", "macro_factors", "supply_chain",
                "overseas_business", "shareholders",
            ]

            for field_name in field_mapping:
                field_data = result.get(field_name)
                if field_data is None:
                    profile[field_name] = None
                elif isinstance(field_data, dict) and "value" in field_data:
                    profile[field_name] = field_data.get("value")
                    # Track provenance
                    self.provenance_tracker.record(
                        field_name=field_name,
                        value=field_data.get("value"),
                        source_url=field_data.get("source_url"),
                        excerpt=field_data.get("excerpt"),
                        confidence=field_data.get("confidence", "LOW"),
                    )
                else:
                    profile[field_name] = field_data

            # Add metadata
            profile["_uncertainty_notes"] = result.get("_uncertainty_notes", [])
            profile["_source_urls"] = result.get("_source_urls", citations)

            logger.info(f"LLM extraction successful for {corp_name}")
            return profile

        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return None

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

        # PRD v1.2: 19개 필드를 위한 종합 쿼리
        query = build_perplexity_query(corp_name, industry_name)

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
            "fetched_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(days=FALLBACK_TTL_DAYS)).isoformat(),
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
        """Save profile to database (PRD v1.2 - all 19+ fields)."""
        try:
            from sqlalchemy import text

            # Upsert (insert or update) - PRD v1.2 full schema
            query = text("""
                INSERT INTO rkyc_corp_profile (
                    profile_id, corp_id, business_summary, revenue_krw, export_ratio_pct,
                    country_exposure, key_materials, key_customers, overseas_operations,
                    ceo_name, employee_count, founded_year, headquarters, executives,
                    industry_overview, business_model, financial_history,
                    competitors, macro_factors, supply_chain, overseas_business, shareholders,
                    consensus_metadata,
                    profile_confidence, field_confidences, source_urls,
                    raw_search_result, field_provenance, extraction_model, extraction_prompt_version,
                    is_fallback, search_failed, validation_warnings, status,
                    fetched_at, expires_at
                ) VALUES (
                    CAST(:profile_id AS uuid), :corp_id, :business_summary, :revenue_krw, :export_ratio_pct,
                    CAST(:country_exposure AS jsonb), :key_materials, :key_customers, :overseas_operations,
                    :ceo_name, :employee_count, :founded_year, :headquarters, CAST(:executives AS jsonb),
                    :industry_overview, :business_model, CAST(:financial_history AS jsonb),
                    CAST(:competitors AS jsonb), CAST(:macro_factors AS jsonb),
                    CAST(:supply_chain AS jsonb), CAST(:overseas_business AS jsonb), CAST(:shareholders AS jsonb),
                    CAST(:consensus_metadata AS jsonb),
                    CAST(:profile_confidence AS confidence_level), CAST(:field_confidences AS jsonb), :source_urls,
                    CAST(:raw_search_result AS jsonb), CAST(:field_provenance AS jsonb), :extraction_model, :extraction_prompt_version,
                    :is_fallback, :search_failed, :validation_warnings, :status,
                    CAST(:fetched_at AS timestamptz), CAST(:expires_at AS timestamptz)
                )
                ON CONFLICT (corp_id) DO UPDATE SET
                    business_summary = EXCLUDED.business_summary,
                    revenue_krw = EXCLUDED.revenue_krw,
                    export_ratio_pct = EXCLUDED.export_ratio_pct,
                    country_exposure = EXCLUDED.country_exposure,
                    key_materials = EXCLUDED.key_materials,
                    key_customers = EXCLUDED.key_customers,
                    overseas_operations = EXCLUDED.overseas_operations,
                    ceo_name = EXCLUDED.ceo_name,
                    employee_count = EXCLUDED.employee_count,
                    founded_year = EXCLUDED.founded_year,
                    headquarters = EXCLUDED.headquarters,
                    executives = EXCLUDED.executives,
                    industry_overview = EXCLUDED.industry_overview,
                    business_model = EXCLUDED.business_model,
                    financial_history = EXCLUDED.financial_history,
                    competitors = EXCLUDED.competitors,
                    macro_factors = EXCLUDED.macro_factors,
                    supply_chain = EXCLUDED.supply_chain,
                    overseas_business = EXCLUDED.overseas_business,
                    shareholders = EXCLUDED.shareholders,
                    consensus_metadata = EXCLUDED.consensus_metadata,
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
                    -- P2-2 Fix: 조건부 TTL 업데이트 (데이터 품질이 향상되거나 기존이 fallback인 경우만 TTL 연장)
                    fetched_at = CASE
                        WHEN EXCLUDED.is_fallback = false AND rkyc_corp_profile.is_fallback = true
                            THEN EXCLUDED.fetched_at
                        WHEN EXCLUDED.profile_confidence IN ('HIGH', 'MED')
                             AND rkyc_corp_profile.profile_confidence = 'LOW'
                            THEN EXCLUDED.fetched_at
                        WHEN rkyc_corp_profile.expires_at IS NULL
                             OR rkyc_corp_profile.expires_at < NOW()
                            THEN EXCLUDED.fetched_at
                        ELSE rkyc_corp_profile.fetched_at
                    END,
                    expires_at = CASE
                        WHEN EXCLUDED.is_fallback = false AND rkyc_corp_profile.is_fallback = true
                            THEN EXCLUDED.expires_at
                        WHEN EXCLUDED.profile_confidence IN ('HIGH', 'MED')
                             AND rkyc_corp_profile.profile_confidence = 'LOW'
                            THEN EXCLUDED.expires_at
                        WHEN rkyc_corp_profile.expires_at IS NULL
                             OR rkyc_corp_profile.expires_at < NOW()
                            THEN EXCLUDED.expires_at
                        ELSE rkyc_corp_profile.expires_at
                    END,
                    updated_at = NOW()
            """)

            await db_session.execute(query, {
                "profile_id": str(profile.get("profile_id", "")),
                "corp_id": profile.get("corp_id", ""),
                "business_summary": profile.get("business_summary"),
                "revenue_krw": profile.get("revenue_krw"),
                "export_ratio_pct": profile.get("export_ratio_pct"),
                # P0-3 Fix: safe_json_dumps()로 이중 직렬화 방지
                "country_exposure": safe_json_dumps(profile.get("country_exposure", {})),
                "key_materials": profile.get("key_materials", []),
                "key_customers": profile.get("key_customers", []),
                "overseas_operations": profile.get("overseas_operations", []),
                # PRD v1.2 new fields
                "ceo_name": profile.get("ceo_name"),
                "employee_count": profile.get("employee_count"),
                "founded_year": profile.get("founded_year"),
                "headquarters": profile.get("headquarters"),
                "executives": safe_json_dumps(profile.get("executives", [])),
                "industry_overview": profile.get("industry_overview"),
                "business_model": profile.get("business_model"),
                "financial_history": safe_json_dumps(profile.get("financial_history", [])),
                "competitors": safe_json_dumps(profile.get("competitors", [])),
                "macro_factors": safe_json_dumps(profile.get("macro_factors", [])),
                "supply_chain": safe_json_dumps(profile.get("supply_chain", {})),
                "overseas_business": safe_json_dumps(profile.get("overseas_business", {})),
                "shareholders": safe_json_dumps(profile.get("shareholders", [])),
                "consensus_metadata": safe_json_dumps(profile.get("consensus_metadata", {})),
                # Original fields
                "profile_confidence": profile.get("profile_confidence", "LOW"),
                "field_confidences": safe_json_dumps(profile.get("field_confidences", {})),
                "source_urls": profile.get("source_urls", []),
                "raw_search_result": safe_json_dumps(profile.get("raw_search_result", {})),
                "field_provenance": safe_json_dumps(profile.get("field_provenance", {})),
                "extraction_model": profile.get("extraction_model"),
                "extraction_prompt_version": profile.get("extraction_prompt_version"),
                "is_fallback": profile.get("is_fallback", False),
                "search_failed": profile.get("search_failed", False),
                "validation_warnings": profile.get("validation_warnings", []),
                "status": profile.get("status", "ACTIVE"),
                "fetched_at": profile.get("fetched_at"),
                "expires_at": profile.get("expires_at"),
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
