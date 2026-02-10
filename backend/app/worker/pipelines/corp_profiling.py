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

import asyncio
import logging
import hashlib
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
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
from app.worker.llm.key_rotator import get_key_rotator
from app.worker.llm.validator import get_validator, ValidationResult
from app.worker.llm.search_providers import get_multi_search_manager
from app.worker.llm.fact_checker import get_fact_checker, FactCheckResult, FactCheckResponse

# DART API for shareholder verification and Fact-based data (P0/P1/P4)
from app.services.dart_api import (
    get_verified_shareholders,
    verify_shareholders,
    get_corp_code,
    initialize_dart_client,
    # P1: Fact-Based Profile Data
    get_fact_based_profile,
    get_company_info_by_name,
    get_largest_shareholders_by_name,
    FactBasedProfileData,
    # P4: Extended Fact Profile (including executives)
    get_extended_fact_profile,
    ExtendedFactProfile,
    Executive,
)

logger = logging.getLogger(__name__)

# DART Verification 설정 (settings에서 가져오거나 기본값 True)
DART_VERIFICATION_ENABLED = getattr(settings, 'DART_VERIFICATION_ENABLED', True)


# ============================================================================
# v2.0 Architecture Configuration
# ============================================================================

# v2.1 아키텍처 플래그: 항상 Perplexity + Gemini 병렬 실행
# 두 Provider 모두 호출하여 데이터 최대 수집, Cross-Coverage로 결합
# - Perplexity 실패 시 Gemini 데이터로 커버
# - Gemini 실패 시 Perplexity 데이터로 커버
# - 둘 다 성공 시 field_assignment 기반으로 최적 값 선택
USE_V2_ARCHITECTURE: bool = False  # False = 병렬 모드 (데이터 최대 수집)

# v2.0 타임아웃 설정 (초)
V2_TIMEOUT_PERPLEXITY = 30  # 기존 45초에서 단축
V2_TIMEOUT_GEMINI = 30
V2_TIMEOUT_OPENAI_VALIDATION = 15


# ============================================================================
# Helper Functions (PRD Bug Fixes)
# ============================================================================


def _json_serializer(obj: Any) -> str:
    """P1-6 Fix: JSON 직렬화 커스텀 핸들러"""
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    return str(obj)


def safe_json_dumps(value: Any) -> str:
    """
    JSON 직렬화 (이중 직렬화 방지) - P0-3 Fix, P1-6 타입별 처리 개선

    Args:
        value: dict, list, str, UUID, datetime, or None

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
            return json.dumps(value, ensure_ascii=False, default=_json_serializer)
    return json.dumps(value, ensure_ascii=False, default=_json_serializer)


# P1-8 Fix: Prompt Injection 방어를 위한 금지 패턴
_PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(?:the\s+)?(?:above|previous)\s+instructions?",
    r"disregard\s+(?:the\s+)?(?:above|previous)",
    r"forget\s+(?:everything|all)",
    r"you\s+are\s+now\s+a",
    r"new\s+instructions?:",
    r"system\s*:",
    r"</?(?:system|user|assistant)>",
    r"\[/?(?:INST|SYS)\]",
    r"```\s*(?:python|javascript|bash|sh)\s*\n",  # 코드 블록 시작
    r"\\n\\n---\\n\\n",  # 구분자 주입
]


def sanitize_input_for_prompt(text: str, field_name: str = "input") -> str:
    """
    P1-8 Fix: LLM 프롬프트에 사용되는 사용자 입력을 안전하게 처리

    Args:
        text: 사용자 입력 (기업명, 업종명 등)
        field_name: 필드명 (로깅용)

    Returns:
        Sanitized text (위험 패턴 제거)

    Raises:
        ValueError: 입력이 너무 길거나 의심스러운 패턴 포함 시
    """
    if not text:
        return ""

    # 1. 길이 제한 (기업명/업종명은 100자면 충분)
    if len(text) > 100:
        logger.warning(f"[PromptSanitizer] {field_name} too long ({len(text)}), truncating")
        text = text[:100]

    # 2. 위험 패턴 탐지
    import re
    for pattern in _PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.error(f"[PromptSanitizer] Prompt injection detected in {field_name}: {text[:50]}...")
            raise ValueError(f"Suspicious input detected in {field_name}")

    # 3. 특수문자 정규화 (제어문자 제거, 줄바꿈 → 공백)
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)  # 제어문자 제거
    text = re.sub(r"\s+", " ", text).strip()  # 연속 공백/줄바꿈 정규화

    return text


def parse_datetime_safely(dt_string: str | datetime | None) -> datetime | None:
    """
    datetime 파싱 ("Z" suffix 지원) - P1-3 Fix

    Python 3.10 이하에서는 fromisoformat()이 "Z" suffix를 지원하지 않음.
    이 함수를 사용하여 다양한 형식의 datetime 문자열을 안전하게 파싱.

    Args:
        dt_string: ISO format datetime string (e.g., "2026-01-21T12:00:00Z")
                  또는 이미 datetime 객체

    Returns:
        datetime object or None

    Usage:
        # 외부 API 응답 파싱
        fetched_at = parse_datetime_safely(response.get("fetched_at"))

        # 캐시 데이터 파싱
        expires_at = parse_datetime_safely(cached_profile.get("expires_at"))
    """
    if not dt_string:
        return None

    # 이미 datetime 객체면 그대로 반환
    if isinstance(dt_string, datetime):
        return dt_string

    try:
        # "Z"를 "+00:00"으로 치환 (Python 3.10 호환)
        if isinstance(dt_string, str) and dt_string.endswith("Z"):
            dt_string = dt_string[:-1] + "+00:00"
        return datetime.fromisoformat(dt_string)
    except (ValueError, TypeError) as e:
        logger.warning(f"[parse_datetime_safely] Failed to parse '{dt_string}': {e}")
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


# P2-6: Validation Severity 레벨
class ValidationSeverity(str, Enum):
    """Validation 결과의 심각도 레벨"""
    CRITICAL = "CRITICAL"  # 검증 실패, 프로필 사용 불가
    ERROR = "ERROR"        # 오류 있음, 일부 필드 수정됨
    WARNING = "WARNING"    # 경고, 검토 권고


@dataclass
class ValidationIssue:
    """P2-6: 개별 검증 이슈"""
    severity: ValidationSeverity
    field: str
    message: str
    original_value: Any = None
    corrected_value: Any = None


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
    """Profile validation result (P2-6: severity 레벨 추가)."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    corrected_profile: Optional[dict] = None
    issues: list[ValidationIssue] = field(default_factory=list)  # P2-6

    @property
    def max_severity(self) -> Optional[ValidationSeverity]:
        """가장 높은 심각도 레벨 반환"""
        if not self.issues:
            return None
        severities = [i.severity for i in self.issues]
        if ValidationSeverity.CRITICAL in severities:
            return ValidationSeverity.CRITICAL
        if ValidationSeverity.ERROR in severities:
            return ValidationSeverity.ERROR
        if ValidationSeverity.WARNING in severities:
            return ValidationSeverity.WARNING
        return None

    def to_dict(self) -> dict:
        """직렬화"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "max_severity": self.max_severity.value if self.max_severity else None,
            "issues": [
                {
                    "severity": i.severity.value,
                    "field": i.field,
                    "message": i.message,
                    "original_value": i.original_value,
                    "corrected_value": i.corrected_value,
                }
                for i in self.issues
            ],
        }


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
        # P2-1 Fix: 안전한 기본값 초기화
        content = ""
        citations = []
        filtered_count = 0

        # P2-1 Fix: raw_response가 None이거나 dict가 아닌 경우 처리
        if not isinstance(raw_response, dict):
            logger.warning(f"[PerplexityParser] Invalid response type: {type(raw_response)}")
            return {
                "content": "",
                "citations": [],
                "filtered_blog_count": 0,
                "source_quality": "LOW",
                "raw_response": raw_response,
                "parse_error": "Invalid response format",
            }

        # choices 필드에서 content 추출
        choices = raw_response.get("choices", [])
        if choices and isinstance(choices, list) and len(choices) > 0:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", "") or ""

        # Perplexity provides citations in the response
        # P2-1 Fix: citations가 list가 아닌 경우 처리
        raw_citations = raw_response.get("citations")
        if isinstance(raw_citations, list):
            citations = raw_citations
        elif raw_citations is not None:
            logger.warning(f"[PerplexityParser] Unexpected citations type: {type(raw_citations)}")
            citations = []

        # Extract URLs from content if citations not provided
        if not citations:
            citations = self._extract_urls_from_content(content)

        # Filter out blog/community URLs if requested
        if exclude_blogs and citations:
            original_count = len(citations)
            citations = self._filter_excluded_domains(citations)
            filtered_count = original_count - len(citations)
            if filtered_count > 0:
                logger.info(f"Filtered {filtered_count} blog/community URLs from citations")

        source_quality = self._assess_source_quality(citations)

        return {
            "content": content,
            "citations": citations,
            "filtered_blog_count": filtered_count,
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
# OpenAI Structured Summarization (정보 손실 방지)
# ============================================================================

STRUCTURED_SUMMARY_SYSTEM_PROMPT = """당신은 금융기관 기업심사 문서를 구조화하는 전문가입니다.

## 핵심 원칙: 정보 손실 방지
1. **모든 숫자는 반드시 보존**: 금액, 비율, 연도, 인원수 등
2. **모든 고유명사 보존**: 회사명, 인명, 국가명, 지역명
3. **출처 URL 보존**: 모든 URL을 그대로 유지
4. **추측 금지**: 원문에 없는 정보 추가 금지

## 숫자 표기 규칙
- 금액: 원화 그대로 (예: 3,200억원, 1조 2,000억원)
- 비율: % 포함 (예: 82%, 45.3%)
- 연도: YYYY 형식 (예: 2024, 2025)
- 인원: 명 단위 (예: 850명, 1,200명)
"""

STRUCTURED_SUMMARY_USER_PROMPT = """다음 검색 결과를 구조화된 형식으로 요약하세요.

## 원본 텍스트
{raw_content}

## 출처 URL 목록
{source_urls}

## 출력 형식 (JSON)
반드시 다음 JSON 형식으로만 응답하세요. 정보가 없으면 null, 빈 배열/객체로 표시:

```json
{{
  "numbers": {{
    "revenue_krw": "원문 그대로 (예: 3,200억원)",
    "revenue_krw_int": 정수 (예: 320000000000),
    "export_ratio_pct": 정수 0-100,
    "founded_year": 정수 YYYY
  }},
  "names": {{
    "ceo_name": "대표이사명",
    "key_customers": ["고객사1", "고객사2"],
    "key_suppliers": ["원자재 공급 회사명 (예: 다나까 금속, 헤라우스, 니폰 금속 - 반드시 실제 회사명!)"],
    "competitors": ["경쟁사1", "경쟁사2"],
    "shareholders": [{{"name": "주주명", "ratio_pct": 지분율}}]
  }},
  "geography": {{
    "country_exposure": {{"중국": 45, "미국": 25}},
    "overseas_operations": ["베트남 하노이 공장", "중국 상해 법인"],
    "export_countries": ["중국", "미국", "베트남"]
  }},
  "supply_chain": {{
    "key_materials": ["원자재1", "원자재2"],
    "supplier_countries": {{"국내": 60, "중국": 25, "일본": 15}},
    "single_source_risk": ["단일 의존 품목"],
    "material_import_ratio_pct": 정수 0-100
  }},
  "narrative": {{
    "business_summary": "3-5문장 요약. 숫자와 고유명사 포함 필수.",
    "business_model": "비즈니스 모델 설명",
    "industry_overview": "산업 현황"
  }},
  "sources": {{
    "urls": ["출처 URL 전체 목록"],
    "excerpts": {{"필드명": "해당 필드의 근거 문장"}}
  }}
}}
```

JSON만 출력하세요."""


def summarize_with_preservation(
    raw_content: str,
    source_urls: list[str],
    llm_service,
) -> dict:
    """
    OpenAI를 사용하여 검색 결과를 구조화하면서 정보 손실을 방지.

    Args:
        raw_content: Perplexity 검색 원본 텍스트
        source_urls: 출처 URL 목록
        llm_service: LLM 서비스 인스턴스

    Returns:
        구조화된 요약 결과 (numbers, names, geography, supply_chain, narrative, sources)
    """
    if not llm_service or not raw_content:
        return {}

    try:
        user_prompt = STRUCTURED_SUMMARY_USER_PROMPT.format(
            raw_content=raw_content[:10000],  # 토큰 제한
            source_urls="\n".join(source_urls) if source_urls else "없음",
        )

        messages = [
            {"role": "system", "content": STRUCTURED_SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        result = llm_service.call_with_json_response(
            messages=messages,
            temperature=0.1,
        )

        logger.info(f"Structured summarization completed: {list(result.keys()) if result else 'empty'}")
        return result or {}

    except Exception as e:
        logger.error(f"Structured summarization failed: {e}")
        return {}


def merge_phase_results(
    phase1: dict,
    phase2: dict,
    phase3: dict,
) -> dict:
    """
    3-Phase 검색 결과를 하나의 프로필로 병합.

    우선순위: Phase별 전문 필드 우선
    - Phase 1: 기본 정보, 재무
    - Phase 2: 해외 사업
    - Phase 3: 공급망, 고객, 경쟁사

    Args:
        phase1: Phase 1 구조화 결과
        phase2: Phase 2 구조화 결과
        phase3: Phase 3 구조화 결과

    Returns:
        병합된 프로필
    """
    merged = {
        "source_urls": [],
        "raw_content": {},
        "field_provenance": {},
    }

    # Phase 1 필드 (기본 정보, 재무)
    # Note: employee_count, headquarters는 기업개요에서 표시하므로 프로필에서 제외
    p1_numbers = phase1.get("numbers", {})
    p1_names = phase1.get("names", {})
    p1_narrative = phase1.get("narrative", {})

    merged["revenue_krw"] = p1_numbers.get("revenue_krw_int")
    merged["founded_year"] = p1_numbers.get("founded_year")
    merged["ceo_name"] = p1_names.get("ceo_name")
    merged["business_summary"] = p1_narrative.get("business_summary")
    merged["business_model"] = p1_narrative.get("business_model")

    # Phase 1 financial_history (최근 3개년)
    if phase1.get("financial_history"):
        merged["financial_history"] = phase1.get("financial_history")

    # Phase 2 필드 (해외 사업)
    p2_numbers = phase2.get("numbers", {})
    p2_geography = phase2.get("geography", {})

    merged["export_ratio_pct"] = p2_numbers.get("export_ratio_pct") or p1_numbers.get("export_ratio_pct")
    merged["country_exposure"] = p2_geography.get("country_exposure", {})
    merged["overseas_operations"] = p2_geography.get("overseas_operations", [])

    # overseas_business 구조화
    if p2_geography.get("overseas_operations"):
        merged["overseas_business"] = {
            "subsidiaries": [],
            "manufacturing_countries": p2_geography.get("export_countries", []),
        }
        for op in p2_geography.get("overseas_operations", []):
            if isinstance(op, str):
                # "베트남 하노이 공장" 형태 파싱
                merged["overseas_business"]["subsidiaries"].append({
                    "name": op,
                    "country": op.split()[0] if op else "",
                    "type": "생산" if "공장" in op else "판매",
                })

    # Phase 3 필드 (공급망, 고객, 경쟁사)
    p3_names = phase3.get("names", {})
    p3_supply = phase3.get("supply_chain", {})

    merged["key_materials"] = p3_supply.get("key_materials", [])
    merged["key_customers"] = p3_names.get("key_customers", [])

    # supply_chain 구조화
    merged["supply_chain"] = {
        "key_suppliers": p3_names.get("key_suppliers", []),
        "supplier_countries": p3_supply.get("supplier_countries", {}),
        "single_source_risk": normalize_single_source_risk(p3_supply.get("single_source_risk")),
        "material_import_ratio_pct": p3_supply.get("material_import_ratio_pct"),
    }

    # shareholders
    merged["shareholders"] = p3_names.get("shareholders", [])

    # competitors
    competitors_raw = p3_names.get("competitors", [])
    merged["competitors"] = [
        {"name": c, "description": ""} if isinstance(c, str) else c
        for c in competitors_raw
    ]

    # macro_factors (Phase 3에서 추출)
    if phase3.get("macro_factors"):
        merged["macro_factors"] = phase3.get("macro_factors")

    # 출처 URL 병합 (중복 제거)
    all_urls = []
    for phase in [phase1, phase2, phase3]:
        sources = phase.get("sources", {})
        all_urls.extend(sources.get("urls", []))
    merged["source_urls"] = list(set(all_urls))

    # Provenance 병합
    for phase_name, phase_data in [("phase1", phase1), ("phase2", phase2), ("phase3", phase3)]:
        excerpts = phase_data.get("sources", {}).get("excerpts", {})
        for field, excerpt in excerpts.items():
            if excerpt and field not in merged["field_provenance"]:
                merged["field_provenance"][field] = {
                    "source_url": None,
                    "excerpt": excerpt[:200] if excerpt else None,
                    "confidence": "MED",
                    "phase": phase_name,
                }

    # Raw content 보관
    merged["raw_content"] = {
        "phase1": phase1.get("narrative", {}).get("business_summary", ""),
        "phase2": str(phase2.get("geography", {})),
        "phase3": str(phase3.get("supply_chain", {})),
    }

    logger.info(f"Merged 3-phase results: {len(merged['source_urls'])} URLs, fields={list(merged.keys())}")
    return merged


# ============================================================================
# Layer 2: Extraction Guardrails - Prompts
# ============================================================================

PROFILE_EXTRACTION_SYSTEM_PROMPT = """당신은 금융기관 기업심사를 위한 기업 프로파일 추출 및 분석 전문가입니다.

## 핵심 원칙
1. **적극적 추출**: 검색 결과에 정보가 있으면 반드시 추출
2. **분석적 요약**: 단순 나열이 아닌, 은행 심사역 관점의 인사이트 제공
3. **신뢰도 표시**: confidence로 정확성 구분
4. **null 최소화**: 정보가 완전히 없는 경우에만 null
5. **주주 정보 특별 규칙**: 공시 데이터 기반만 허용 (추론 절대 금지)

## ⚠️ 주주 정보 (shareholders) - 특별 규칙 (CRITICAL - Hallucination 방지)

### 절대 금지 사항:
1. **관계 기반 추론 금지**: "A가 B회사 회장" + "A가 C회사와 관련" → B가 C의 주주라는 추론 금지
2. **인물의 다른 회사 혼동 금지**: 특정 인물이 관련된 다른 회사를 주주로 기재하지 마세요
3. **계열사/관계사 혼동 금지**: 지주회사, 계열사, 협력사를 주주로 착각하지 마세요
4. **뉴스 언급만으로 판단 금지**: "~와 협력", "~에 납품" 등은 주주 관계가 아닙니다

### 주주 정보 필수 확인 사항:
- DART 전자공시 (dart.fss.or.kr)에서 직접 확인된 정보만 사용
- 한국거래소 KIND 공시 (kind.krx.co.kr)에서 확인된 정보만 사용
- "지분 X% 보유", "대주주", "주주명부" 등 명시적 표현이 있어야 함

### 업종 불일치 경고 (자동 거부 대상):
다음 유형의 회사가 제조업/IT업의 대주주로 나타나면 Hallucination 의심:
- 토지신탁, 자산운용, 생명보험, 손해보험, 캐피탈, 저축은행
- 단, 5% 미만 지분의 기관투자자는 예외

### 확인 불가 시:
shareholders: null 반환 (추론하지 말 것)

## 규칙 1: business_summary - 분석적 인사이트 (가장 중요!)

**business_summary는 단순 사업 설명이 아닌, 3~5문장의 분석적 요약이어야 합니다:**

포함해야 할 내용:
1. 산업 내 포지션 (시장점유율, 글로벌/국내 순위)
2. 핵심 경쟁력 또는 차별점
3. 현재 직면한 기회 요인 (AI 수요, 친환경 트렌드, 신시장 등)
4. 현재 직면한 위협/리스크 요인
5. 향후 전망

**좋은 예시:**
"글로벌 본딩와이어 시장 1위 기업으로, 반도체 후공정 소재 분야에서 독보적 기술력을 보유하고 있다.
AI 반도체 수요 증가로 HBM용 본딩와이어 매출이 급성장하고 있으나,
금 가격 변동과 중국 경쟁사의 저가 공세가 리스크 요인이다.
주요 고객사인 삼성전자, SK하이닉스의 설비 투자 확대가 성장 동력으로 작용할 전망이다."

**나쁜 예시 (단순 나열):**
"반도체 소재 제조 기업. 본딩와이어와 솔더볼을 생산함."

## 규칙 2: 숫자 데이터 - 적극 추출

**revenue_krw**: "매출 3,000억원" → 300000000000
**export_ratio_pct**: "수출 80%" → 80, "수출 중심" → 70 추정
**employee_count**: "약 800명" → 800

## 규칙 3: 신뢰도 판단
- **HIGH**: DART 공시, IR 자료, 사업보고서
- **MED**: 언론 보도, "약 X", "X 이상"
- **LOW**: 추정치, 업종 평균 기반 추론

## 규칙 4: 업종 기반 합리적 추론 허용

검색 결과에 직접적 정보가 없어도, 업종 특성상 추론 가능한 경우:

**country_exposure 추론:**
- 해외 법인이 있으면 → 해당 국가 노출 추정 (confidence: LOW)
- 수출 기업이면 → 업종 주요 수출국 포함 (confidence: LOW)

**supply_chain 추론:**
- 제조업이면 → 업종별 주요 원자재 포함 (confidence: LOW)
- 예: 반도체 기업 → key_materials: ["실리콘", "금", "구리"]
- **key_suppliers는 반드시 실제 회사명으로 추출** (추상적 표현 금지!)
- 예: "원자재 공급사" (X) → "다나까 금속", "헤라우스 그룹" (O)
- 검색 결과에 "거래처", "공급사", "매입처", "납품" 등이 나오면 해당 회사명 추출

**key_customers 추론:**
- B2B 기업이면 → 업종 내 대기업 고객 추정 (confidence: LOW)

## 규칙 5: null 최소화
- 검색 결과에 힌트가 있으면 → 추출 + confidence 표시
- 업종 특성으로 추론 가능하면 → 추론 + confidence: LOW
- 빈 배열([])보다 추론 데이터가 더 가치 있음
"""

PROFILE_EXTRACTION_USER_PROMPT = """## 검색 결과
{search_results}

## 추출 대상 기업
기업명: {corp_name}
업종: {industry_name}
{industry_hints_text}

## 출력 스키마 (PRD v1.2 - 19개 필드)
다음 JSON 형식으로만 응답하세요. 모든 필드에 대해 value, confidence, source_url, excerpt를 포함해야 합니다.
**null은 정보가 완전히 없을 때만 사용하세요. 업종 특성으로 추론 가능하면 추론값 + confidence: LOW로 작성하세요.**

```json
{{
  "business_summary": {{
    "value": "3~5문장의 분석적 요약. 포함 내용: 1)산업 내 포지션 2)핵심 경쟁력 3)기회 요인 4)위협/리스크 5)전망. 은행 심사역이 '이 기업에 대출해도 될까?'를 판단할 수 있는 인사이트 제공. 단순 사업 나열 금지.",
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
      "key_suppliers": ["원자재 공급 회사 실명 (예: 다나까 금속, 헤라우스 그룹, 니폰 금속, Tanaka, Heraeus 등 - 반드시 실제 거래처 공급사명!)"],
      "supplier_countries": {{"일본": 50, "독일": 30, "국내": 20}},
      "single_source_risk": ["특정 공급사에만 의존하는 원자재/부품 목록"],
      "material_import_ratio_pct": "integer 0-100 (원자재 수입 비율)"
    }} 또는 null,
    "confidence": "HIGH|MED|LOW",
    "source_url": "url 또는 null",
    "excerpt": "원자재 공급사 관련 원문 텍스트"
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
    "source_url": "DART 또는 KIND 공시 URL만 허용 (필수!)",
    "excerpt": "공시문서에서 직접 인용한 주주 정보 텍스트 (필수!)"
  }},
  "_shareholders_validation_note": "⚠️ 주주 정보는 반드시 DART/KIND 공시에서 직접 확인된 경우에만 기재. 추론 금지. 확인 불가 시 null 반환.",
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

        # P1-7 Fix: Nested object validation
        # Rule 8: supply_chain validation
        supply_chain = profile.get("supply_chain")
        if supply_chain and isinstance(supply_chain, dict):
            sc_errors = self._validate_supply_chain(supply_chain)
            errors.extend(sc_errors)
            if sc_errors:
                corrected["supply_chain"] = None

        # Rule 9: overseas_business validation
        overseas_business = profile.get("overseas_business")
        if overseas_business and isinstance(overseas_business, dict):
            ob_errors = self._validate_overseas_business(overseas_business)
            errors.extend(ob_errors)
            if ob_errors:
                corrected["overseas_business"] = None

        # Rule 10: financial_history validation
        financial_history = profile.get("financial_history")
        if financial_history and isinstance(financial_history, list):
            fh_errors = self._validate_financial_history(financial_history)
            errors.extend(fh_errors)
            if fh_errors:
                corrected["financial_history"] = None

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

    # P1-7 Fix: Nested object validation methods
    def _validate_supply_chain(self, supply_chain: dict) -> list[str]:
        """Validate supply_chain nested object structure."""
        errors = []

        # key_suppliers should be a list of strings
        key_suppliers = supply_chain.get("key_suppliers")
        if key_suppliers is not None and not isinstance(key_suppliers, list):
            errors.append("supply_chain.key_suppliers must be a list")

        # supplier_countries should be a dict with numeric values (percentages)
        supplier_countries = supply_chain.get("supplier_countries")
        if supplier_countries is not None:
            if not isinstance(supplier_countries, dict):
                errors.append("supply_chain.supplier_countries must be a dict")
            else:
                for country, pct in supplier_countries.items():
                    if not isinstance(pct, (int, float)):
                        errors.append(f"supply_chain.supplier_countries[{country}] must be numeric")
                    elif not (0 <= pct <= 100):
                        errors.append(f"supply_chain.supplier_countries[{country}] out of range: {pct}")

        # single_source_risk should be a list of strings (단일 조달처 위험 품목 목록)
        # or boolean for backwards compatibility
        single_source_risk = supply_chain.get("single_source_risk")
        if single_source_risk is not None:
            if not isinstance(single_source_risk, (list, bool)):
                errors.append("supply_chain.single_source_risk must be a list or boolean")

        # material_import_ratio_pct should be numeric 0-100
        # Check both field names for backwards compatibility
        import_ratio = supply_chain.get("material_import_ratio_pct") or supply_chain.get("raw_material_import_ratio")
        if import_ratio is not None:
            if not isinstance(import_ratio, (int, float)):
                errors.append("supply_chain.material_import_ratio_pct must be numeric")
            elif not (0 <= import_ratio <= 100):
                errors.append(f"supply_chain.material_import_ratio_pct out of range: {import_ratio}")

        return errors

    def _validate_overseas_business(self, overseas_business: dict) -> list[str]:
        """Validate overseas_business nested object structure."""
        errors = []

        # subsidiaries should be a list
        subsidiaries = overseas_business.get("subsidiaries")
        if subsidiaries is not None:
            if not isinstance(subsidiaries, list):
                errors.append("overseas_business.subsidiaries must be a list")
            else:
                for i, sub in enumerate(subsidiaries):
                    if not isinstance(sub, dict):
                        errors.append(f"overseas_business.subsidiaries[{i}] must be a dict")
                    else:
                        # Each subsidiary should have country and name
                        if not sub.get("country"):
                            errors.append(f"overseas_business.subsidiaries[{i}].country is required")
                        if not sub.get("name"):
                            errors.append(f"overseas_business.subsidiaries[{i}].name is required")

        # manufacturing_countries should be a list of strings
        manufacturing_countries = overseas_business.get("manufacturing_countries")
        if manufacturing_countries is not None and not isinstance(manufacturing_countries, list):
            errors.append("overseas_business.manufacturing_countries must be a list")

        return errors

    def _validate_financial_history(self, financial_history: list) -> list[str]:
        """Validate financial_history list structure."""
        errors = []

        for i, entry in enumerate(financial_history):
            if not isinstance(entry, dict):
                errors.append(f"financial_history[{i}] must be a dict")
                continue

            # year should be a reasonable year
            year = entry.get("year")
            if year is not None:
                if not isinstance(year, int):
                    errors.append(f"financial_history[{i}].year must be an integer")
                elif not (1900 <= year <= 2100):
                    errors.append(f"financial_history[{i}].year out of range: {year}")

            # revenue, operating_profit, net_profit should be numeric
            for field in ["revenue", "operating_profit", "net_profit"]:
                value = entry.get(field)
                if value is not None and not isinstance(value, (int, float)):
                    errors.append(f"financial_history[{i}].{field} must be numeric")

        return errors


# ============================================================================
# Layer 4: Audit Trail - ProvenanceTracker
# ============================================================================


class ProvenanceTracker:
    """Track provenance for all extracted fields (P2-7: timestamp 자동 추가)."""

    def __init__(self):
        self.provenance: dict[str, FieldProvenance] = {}
        self._created_at = datetime.now(UTC)  # P2-7: 트래커 생성 시간

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

    def track_field(
        self,
        field_name: str,
        value: Any,
        source: str = "UNKNOWN",
        source_url: Optional[str] = None,
        excerpt: Optional[str] = None,
        confidence: str = "LOW",
    ):
        """P2-7: track_field() - 간편 기록 메서드 (timestamp 자동 추가)

        Args:
            field_name: 필드명
            value: 값
            source: 소스 타입 (PERPLEXITY, GEMINI_INFERRED, etc.)
            source_url: 출처 URL
            excerpt: 발췌 텍스트
            confidence: 신뢰도 (HIGH/MED/LOW)
        """
        now = datetime.now(UTC)
        self.provenance[field_name] = FieldProvenance(
            field_name=field_name,
            value=value,
            source_url=source_url,
            excerpt=excerpt,
            confidence=confidence,
            extraction_date=now,
        )
        logger.debug(f"[ProvenanceTracker] Tracked {field_name} from {source} at {now.isoformat()}")

    def to_json(self) -> dict:
        """Export provenance for storage (P2-7: 메타데이터 포함)."""
        return {
            "_metadata": {
                "tracker_created_at": self._created_at.isoformat(),
                "last_updated_at": datetime.now(UTC).isoformat(),
                "field_count": len(self.provenance),
            },
            "fields": {
                name: prov.to_dict()
                for name, prov in self.provenance.items()
            },
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

    def get_extraction_timeline(self) -> list[dict]:
        """P2-7: 필드 추출 타임라인 반환 (시간순 정렬)"""
        timeline = [
            {
                "field": name,
                "extracted_at": prov.extraction_date.isoformat(),
                "confidence": prov.confidence,
            }
            for name, prov in self.provenance.items()
        ]
        return sorted(timeline, key=lambda x: x["extracted_at"])


# ============================================================================
# Confidence Determination
# ============================================================================


# P2-8: 소스별 신뢰도 가중치 (외부화)
# 숫자가 높을수록 신뢰도 높음
CONFIDENCE_SOURCE_WEIGHTS: dict[str, int] = {
    # 공시/공공 데이터 (최고 신뢰도)
    "DART": 100,
    "KRX": 100,
    "GOVERNMENT": 95,

    # 검증된 외부 검색
    "PERPLEXITY_VERIFIED": 85,
    "PERPLEXITY": 80,

    # LLM 검증/보완
    "GEMINI_VALIDATED": 75,
    "CLAUDE_SYNTHESIZED": 70,
    "GEMINI_INFERRED": 50,

    # Fallback
    "RULE_BASED": 30,
    "INDUSTRY_DEFAULT": 20,
    "UNKNOWN": 10,
}

# P2-8: 신뢰도 레벨 임계값
CONFIDENCE_LEVEL_THRESHOLDS: dict[str, int] = {
    "HIGH": 80,   # weight >= 80 → HIGH
    "MED": 50,    # 50 <= weight < 80 → MED
    "LOW": 0,     # weight < 50 → LOW
}


def get_confidence_from_source(source: str) -> str:
    """P2-8: 소스에서 신뢰도 레벨 결정"""
    weight = CONFIDENCE_SOURCE_WEIGHTS.get(source.upper(), 10)
    if weight >= CONFIDENCE_LEVEL_THRESHOLDS["HIGH"]:
        return "HIGH"
    if weight >= CONFIDENCE_LEVEL_THRESHOLDS["MED"]:
        return "MED"
    return "LOW"


class ConfidenceDeterminer:
    """Determine field-level and overall profile confidence (P2-8: 가중치 외부화)."""

    # P2-8: 필수 필드별 가중치 (overall confidence 계산용)
    REQUIRED_FIELD_WEIGHTS: dict[str, float] = {
        "business_summary": 1.5,  # 필수 중 가장 중요
        "export_ratio_pct": 1.2,
        "country_exposure": 1.2,
        "key_materials": 1.0,
        "overseas_operations": 1.0,
        "revenue_krw": 0.8,
    }

    def determine_overall_confidence(
        self,
        field_confidences: dict[str, str],
        required_fields: list[str],
    ) -> str:
        """
        Overall profile confidence based on field confidences (P2-8: 가중치 적용).

        Rules:
        - If any required field is LOW, overall is at most MED
        - If >50% of fields are null/empty, overall is LOW
        - If all required fields are HIGH, overall is HIGH
        - P2-8: 가중치 기반 스코어링 추가
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

        # P2-8: 가중치 기반 스코어링
        total_weight = 0.0
        weighted_score = 0.0
        for field, conf in field_confidences.items():
            weight = self.REQUIRED_FIELD_WEIGHTS.get(field, 0.5)
            total_weight += weight
            if conf == "HIGH":
                weighted_score += weight * 1.0
            elif conf == "MED":
                weighted_score += weight * 0.6
            else:  # LOW
                weighted_score += weight * 0.2

        if total_weight > 0:
            avg_score = weighted_score / total_weight
            if avg_score >= 0.8:
                return "HIGH"
            if avg_score >= 0.5:
                return "MED"

        return "MED"

    @staticmethod
    def get_source_weight(source: str) -> int:
        """P2-8: 소스의 가중치 반환"""
        return CONFIDENCE_SOURCE_WEIGHTS.get(source.upper(), 10)


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

# 업종별 힌트 캐시 (메모리 캐시, 서버 재시작 시 초기화)
# P1-4 Fix: Thread-safety를 위한 Lock 추가
_industry_hints_cache: dict[str, dict] = {}
_industry_hints_lock = threading.Lock()


def clear_industry_hints_cache(industry_code: str = None) -> int:
    """
    업종 힌트 캐시 클리어.

    Args:
        industry_code: 특정 업종만 클리어 (None이면 전체 클리어)

    Returns:
        클리어된 항목 수
    """
    with _industry_hints_lock:
        if industry_code:
            if industry_code in _industry_hints_cache:
                del _industry_hints_cache[industry_code]
                logger.info(f"Cleared industry hints cache for {industry_code}")
                return 1
            return 0
        else:
            count = len(_industry_hints_cache)
            _industry_hints_cache.clear()
            logger.info(f"Cleared all industry hints cache ({count} items)")
            return count


def get_industry_name(industry_code: str) -> str:
    """Get industry name from code."""
    return INDUSTRY_NAMES.get(industry_code, f"업종코드 {industry_code}")


INDUSTRY_HINTS_PROMPT = """업종코드 {industry_code} ({industry_name})의 일반적인 특성을 분석하세요.

다음 JSON 형식으로만 응답하세요:
```json
{{
  "typical_materials": ["주요 원자재 5개 이상 - 이 업종에서 일반적으로 사용하는 원자재/부품"],
  "typical_suppliers": ["실제 공급사 회사명 5개 이상 - 이 업종의 한국 기업들이 실제로 거래하는 글로벌 공급사 이름 (예: 다나까 금속, 헤라우스 등)"],
  "export_markets": ["주요 수출 시장 5개 이상 - 이 업종의 한국 기업들이 주로 수출하는 국가"],
  "risk_factors": ["업종 리스크 3개 이상 - 이 업종 특유의 리스크 요인"],
  "growth_drivers": ["성장 동력 3개 이상 - 이 업종의 성장을 이끄는 요인"]
}}
```

예시 (반도체 C26):
- typical_materials: ["실리콘 웨이퍼", "금 (Au)", "은 (Ag)", "구리 (Cu)", "희토류", "화학물질", "리드프레임"]
- typical_suppliers: ["다나까 금속 (Tanaka)", "헤라우스 그룹 (Heraeus)", "니폰 금속 (NIPPON)", "스미토모", "SK실트론", "듀폰", "린데"]
- export_markets: ["중국", "미국", "대만", "베트남", "일본", "유럽"]
- risk_factors: ["반도체 사이클", "미중 무역분쟁", "기술 경쟁", "설비 투자 부담"]
- growth_drivers: ["AI 수요", "전기차", "데이터센터", "IoT"]
"""


async def get_industry_hints(industry_code: str, llm_service=None) -> dict:
    """
    업종 코드에 대한 힌트를 LLM으로 동적 생성 (캐싱 적용)

    Args:
        industry_code: 업종 코드 (예: C26)
        llm_service: LLM 서비스 인스턴스 (없으면 기본 힌트 반환)

    Returns:
        dict with typical_materials, typical_suppliers, export_markets, etc.
    """
    # P1-4 Fix: Thread-safe 캐시 조회
    with _industry_hints_lock:
        if industry_code in _industry_hints_cache:
            logger.debug(f"Industry hints cache hit for {industry_code}")
            return _industry_hints_cache[industry_code]

    industry_name = get_industry_name(industry_code)

    # LLM 서비스가 없으면 기본 힌트 반환
    if llm_service is None:
        # 반도체 업종(C26)인 경우 특화된 힌트 제공
        if industry_code == "C26":
            default_hints = {
                "typical_materials": ["금 (Au)", "은 (Ag)", "구리 (Cu)", "실리콘", "리드프레임"],
                "typical_suppliers": ["다나까 금속 (Tanaka)", "헤라우스 그룹 (Heraeus)", "니폰 금속 (NIPPON)", "스미토모", "듀폰"],
                "export_markets": ["중국", "미국", "대만", "베트남", "일본"],
                "risk_factors": ["반도체 사이클", "미중 무역분쟁", "금 가격 변동"],
                "growth_drivers": ["AI 수요", "전기차", "HBM"],
            }
        else:
            default_hints = {
                "typical_materials": ["원자재", "부품", "소재"],
                "typical_suppliers": ["원자재 공급사", "부품 공급사", "장비 공급사"],
                "export_markets": ["중국", "미국", "베트남", "일본", "유럽"],
                "risk_factors": ["경기 변동", "환율 리스크", "공급망 리스크"],
                "growth_drivers": ["기술 혁신", "시장 확대", "정부 정책"],
            }
        return default_hints

    try:
        # LLM으로 업종 힌트 생성
        prompt = INDUSTRY_HINTS_PROMPT.format(
            industry_code=industry_code,
            industry_name=industry_name
        )

        response = await llm_service.generate(
            prompt=prompt,
            system_prompt="당신은 산업 분석 전문가입니다. JSON 형식으로만 응답하세요.",
            temperature=0.3,
        )

        # JSON 파싱
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            hints = json.loads(json_match.group(1))
        else:
            hints = json.loads(response)

        # P1-4 Fix: Thread-safe 캐시 저장
        with _industry_hints_lock:
            _industry_hints_cache[industry_code] = hints
        logger.info(f"Generated and cached industry hints for {industry_code}")

        return hints

    except Exception as e:
        logger.warning(f"Failed to generate industry hints for {industry_code}: {e}")
        # 실패 시 기본 힌트 반환 (반도체 C26인 경우 특화)
        if industry_code == "C26":
            return {
                "typical_materials": ["금 (Au)", "은 (Ag)", "구리 (Cu)", "실리콘", "리드프레임"],
                "typical_suppliers": ["다나까 금속 (Tanaka)", "헤라우스 그룹 (Heraeus)", "니폰 금속 (NIPPON)"],
                "export_markets": ["중국", "미국", "대만", "베트남", "일본"],
                "risk_factors": ["반도체 사이클", "미중 무역분쟁"],
                "growth_drivers": ["AI 수요", "전기차"],
            }
        return {
            "typical_materials": ["원자재", "부품", "소재"],
            "typical_suppliers": ["원자재 공급사", "부품 공급사"],
            "export_markets": ["중국", "미국", "베트남"],
            "risk_factors": ["경기 변동", "환율 리스크"],
            "growth_drivers": ["기술 혁신", "시장 확대"],
        }


# ============================================================================
# 3-Phase Query Builder (Option B)
# ============================================================================


def build_phase1_query(corp_name: str, industry_name: str) -> str:
    """
    Phase 1: 기본 정보 + 재무 + 사업 개요

    추출 대상: revenue_krw, ceo_name, business_summary, founded_year,
              executives, business_model
    Note: employee_count, headquarters는 기업개요에서 표시하므로 프로필에서 제외
    """
    return f"""{corp_name} 기업 기본 정보 (한국 기업, 2026년 기준):

다음 정보를 정확한 수치와 함께 찾아주세요:

1. **기본 정보**
   - 대표이사 성명
   - 설립연도 (YYYY)
   - 주요 경영진 (CFO, COO 등)

2. **재무 정보** (가장 최근 연도 기준)
   - 연간 매출액 (원화, 정확한 숫자)
   - 영업이익 (원화)
   - 순이익 (원화)
   - 최근 3개년 매출 추이

3. **사업 개요**
   - 주요 사업 내용 및 제품/서비스
   - 비즈니스 모델 (B2B/B2C, 수익 구조)
   - 산업 내 포지션 (시장점유율, 순위)
   - 핵심 경쟁력

공식 출처(DART 공시, 사업보고서, 기업 IR, 금감원)에서 검색해주세요.
출처 URL을 반드시 포함해주세요."""


def build_phase2_query(corp_name: str, industry_name: str, industry_hints: dict = None) -> str:
    """
    Phase 2: 해외 사업 + 국가별 노출

    추출 대상: export_ratio_pct, country_exposure, overseas_operations,
              overseas_business
    """
    markets_hint = ""
    if industry_hints:
        markets = industry_hints.get("export_markets", [])[:5]
        if markets:
            markets_hint = f"\n(참고: {industry_name} 업종 주요 수출국: {', '.join(markets)})"

    return f"""{corp_name} 해외 사업 현황 (한국 기업, 2026년 기준):

다음 정보를 정확한 수치와 함께 찾아주세요:

1. **수출 현황**
   - 수출 비중 (전체 매출 대비 %)
   - 내수 vs 수출 비율

2. **국가별 매출 비중** (구체적 수치 필수){markets_hint}
   - 중국: X%
   - 미국: X%
   - 베트남: X%
   - 일본: X%
   - 유럽: X%
   - 기타: X%

3. **해외 법인/공장**
   - 해외 법인명 및 소재 국가
   - 해외 생산 공장 위치
   - 법인 유형 (생산/판매/R&D)

4. **해외 사업 전략**
   - 주요 수출 제품
   - 해외 시장 확대 계획

공식 출처(DART 공시, 사업보고서, IR 자료, 언론 보도)에서 검색해주세요.
출처 URL을 반드시 포함해주세요."""


def build_phase3_query(corp_name: str, industry_name: str, industry_hints: dict = None) -> str:
    """
    Phase 3: 공급망 + 고객 + 경쟁사 + 주주

    추출 대상: supply_chain, key_materials, key_customers, key_suppliers,
              competitors, shareholders, macro_factors
    """
    materials_hint = ""
    suppliers_hint = ""
    if industry_hints:
        materials = industry_hints.get("typical_materials", [])[:5]
        suppliers = industry_hints.get("typical_suppliers", [])[:5]
        if materials:
            materials_hint = f"\n   (이 업종 주요 원자재: {', '.join(materials)})"
        if suppliers:
            suppliers_hint = f"\n   (이 업종 대표 공급사 예시: {', '.join(suppliers)})"

    return f"""{corp_name} 공급망 및 이해관계자 (한국 기업, 2026년 기준):

다음 정보를 정확한 수치와 함께 찾아주세요:

1. **원자재 공급사/매입처 (가장 중요!)** {materials_hint}{suppliers_hint}
   - {corp_name}에 원자재를 납품하는 **거래처 공급사 회사명** (예: 다나까 금속, 헤라우스, 니폰 금속 등)
   - 반드시 **실제 회사명**을 찾아주세요 (추상적 표현 금지)
   - 공급사 국가별 비중 (일본, 독일, 국내 등)
   - 주요 원자재/부품 목록 (금, 은, 구리, 실리콘 등)
   - 원자재 수입 비율 (%)
   - 단일 조달처 위험 품목 (특정 공급사에만 의존하는 품목)

2. **고객 정보**
   - 주요 고객사 (B2B인 경우 회사명)
   - 매출 비중 상위 고객

3. **경쟁 환경**
   - 주요 경쟁사 (국내/해외)
   - 경쟁 영역 및 차별점
   - 시장점유율 비교

4. **주주 정보**
   - 최대주주 및 지분율 (%)
   - 주요 주주 명단 및 지분율

5. **거시 요인**
   - 이 기업에 영향을 미치는 정책/규제
   - 산업 트렌드 영향 (긍정/부정)

공식 출처(DART 공시, 사업보고서, 애널리스트 리포트)에서 검색해주세요.
출처 URL을 반드시 포함해주세요."""


def build_perplexity_query(corp_name: str, industry_name: str, industry_hints: dict = None) -> str:
    """
    Build comprehensive Perplexity search query for PRD v1.2.

    DEPRECATED: Use build_phase1/2/3_query instead for better results.

    Args:
        corp_name: 기업명
        industry_name: 업종명
        industry_hints: 업종별 힌트 (LLM 생성 또는 캐시)
    """
    # P1-8 Fix: Prompt Injection 방어
    corp_name = sanitize_input_for_prompt(corp_name, "corp_name")
    industry_name = sanitize_input_for_prompt(industry_name, "industry_name")

    # 업종 힌트가 있으면 쿼리에 포함
    materials_hint = ""
    markets_hint = ""
    risk_hint = ""

    if industry_hints:
        materials = industry_hints.get("typical_materials", [])[:5]
        markets = industry_hints.get("export_markets", [])[:5]
        risks = industry_hints.get("risk_factors", [])[:3]
        growth = industry_hints.get("growth_drivers", [])[:3]

        if materials:
            materials_hint = f"\n  (이 업종 주요 원자재: {', '.join(materials)})"
        if markets:
            markets_hint = f"\n  (이 업종 주요 수출 시장: {', '.join(markets)})"
        if risks or growth:
            risk_hint = f"\n  (업종 주요 이슈: {', '.join(risks + growth)})"

    return f"""
{corp_name} ({industry_name}) 기업 종합 분석 (한국 기업, 2026년 기준):

[핵심 분석 - 가장 중요!]
{corp_name}에 대해 다음 관점에서 분석해주세요:
1. 이 기업의 산업 내 포지션 (시장점유율, 글로벌/국내 순위)
2. 핵심 경쟁력과 차별점
3. 현재 직면한 기회 요인 (AI, 친환경, 신시장 등)
4. 현재 직면한 위협/리스크 요인{risk_hint}
5. 은행이 이 기업에 대출할 때 고려해야 할 핵심 사항

[기본 정보]
- 대표이사, 설립연도, 본사 위치, 임직원 수, 주요 경영진

[재무 정보]
- 연간 매출액 (최근 실적, 원화), 영업이익, 순이익
- 재무 건전성 지표

[공급망 정보] - 반드시 찾아주세요{materials_hint}
- {corp_name}의 실제 원자재/부품 공급사 회사명
- 국내 조달 vs 해외 수입 비율
- 특정 공급사에 의존하는 품목 (단일 조달처 위험)

[해외 사업] - 반드시 찾아주세요{markets_hint}
- 수출 비중 (%)
- 국가별 매출 비중 (중국, 미국, 베트남 등 구체적 수치)
- 해외 법인/공장 위치 (법인명, 국가)

[주주 정보]
- 최대주주 및 지분율
- 주요 주주 명단

[경쟁 환경]
- 주요 경쟁사 및 시장점유율 비교
- 경쟁 우위/열위 요인

공식 출처(DART, 금감원, 기업 IR, 사업보고서, 애널리스트 리포트, 주요 언론)에서 검색해주세요.
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

    P0-1 Fix: Orchestrator는 동기 함수이므로 run_in_executor로 래핑하여
    async context에서 Event Loop 블로킹 방지.
    """

    # Thread pool for sync orchestrator execution (P0-1 Fix)
    _executor: Optional[ThreadPoolExecutor] = None

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

        # Initialize thread pool for sync operations (P0-1 Fix)
        if CorpProfilingPipeline._executor is None:
            CorpProfilingPipeline._executor = ThreadPoolExecutor(
                max_workers=4,
                thread_name_prefix="orchestrator_"
            )

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

        # =========================================================================
        # P1+P4: DART Fact-Based Data (100% Hallucination 제거)
        # DART 공시에서 CEO, 설립일, 주소, 최대주주, 임원현황 등을 먼저 가져옴
        # LLM 추출 결과보다 DART 데이터가 우선순위 (100% Fact)
        # =========================================================================
        # P0 Performance: DART + Industry Hints 병렬 실행 (2초 단축)
        dart_fact_data: Optional[ExtendedFactProfile] = None
        self._industry_hints = {}

        async def fetch_dart_data():
            try:
                data = await get_extended_fact_profile(corp_name)
                if data and data.company_info:
                    logger.info(
                        f"[P1+P4-DART] Fact data loaded: CEO={data.ceo_name}, "
                        f"Founded={data.founded_year}, "
                        f"Shareholders={len(data.largest_shareholders)}, "
                        f"Executives={len(data.executives)}"
                    )
                else:
                    logger.info(f"[P1+P4-DART] No DART data available for '{corp_name}'")
                return data
            except Exception as e:
                logger.warning(f"[P1+P4-DART] Failed to fetch DART fact data: {e}")
                return None

        async def fetch_industry_hints():
            try:
                hints = await get_industry_hints(industry_code, llm_service)
                logger.info(f"Industry hints generated for {industry_code}: {list(hints.keys())}")
                return hints
            except Exception as e:
                logger.warning(f"Failed to generate industry hints: {e}")
                return {}

        # 병렬 실행: DART 조회 + Industry Hints 동시 수행
        dart_result, hints_result = await asyncio.gather(
            fetch_dart_data(),
            fetch_industry_hints(),
            return_exceptions=True
        )

        # 결과 처리 (예외 발생 시 기본값 사용)
        dart_fact_data = dart_result if not isinstance(dart_result, Exception) else None
        self._industry_hints = hints_result if not isinstance(hints_result, Exception) else {}

        # P0-2 Fix: 캐시 조회 결과를 orchestrator에 전달 (더블 조회 방지)
        # 캐시 조회는 execute()에서 한 번만 수행하고 그 결과를 람다로 전달
        cached_profile_for_orchestrator = None  # execute()에서 조회 후 전달

        # Configure orchestrator with injectable functions
        # Note: cache lookup은 아래 execute() 호출 전에 수행되므로,
        # 여기서는 None을 반환하고 existing_profile로 전달
        self.orchestrator.set_cache_lookup(
            lambda cn, ic: None  # P0-2: orchestrator 내부 캐시 조회 비활성화
        )
        self.orchestrator.set_perplexity_search(
            lambda cn, ind: self._sync_perplexity_search(cn, ind, perplexity_api_key)
        )
        self.orchestrator.set_claude_synthesis(
            lambda sources, corp_name, industry_name, industry_code, gemini_discrepancies: self._sync_claude_synthesis(
                sources, corp_name, industry_name, industry_code, gemini_discrepancies, llm_service
            )
        )

        # v2.1 Architecture: 항상 병렬 모드로 데이터 최대 수집
        # Perplexity + Gemini 둘 다 호출, Cross-Coverage로 결합
        if USE_V2_ARCHITECTURE:
            # (현재 비활성화됨) 순차 Fallback 모드
            logger.info(f"[v2.0] Using sequential fallback architecture")
            self.orchestrator.set_parallel_mode(False)
            self.orchestrator.set_gemini_search(
                lambda cn, ind: self._sync_gemini_fallback_search(cn, ind)
            )
            self.orchestrator.set_openai_validation(
                lambda profile, cn, ind, src: self._sync_openai_validation(profile, cn, ind, src, llm_service)
            )
            self.orchestrator.enable_multi_search(True)
        else:
            # 병렬 모드: Perplexity + Gemini 동시 실행으로 데이터 최대 수집
            logger.info(f"[v2.1] Using parallel architecture (maximum data collection)")
            self.orchestrator.set_parallel_mode(True)  # 병렬 모드 활성화
            # Gemini 검색도 설정하여 데이터 보완
            self.orchestrator.set_gemini_search(
                lambda cn, ind: self._sync_gemini_fallback_search(cn, ind)
            )
            # OpenAI Validation은 병렬 모드에서도 Cross-Validation에 사용
            self.orchestrator.set_openai_validation(
                lambda profile, cn, ind, src: self._sync_openai_validation(profile, cn, ind, src, llm_service)
            )
            # Multi-Search 활성화 (Cross-Coverage 지원)
            self.orchestrator.enable_multi_search(True)

        # Get existing profile for potential enrichment (but don't use as cache if skip_cache)
        # P0-2 Fix: 캐시 조회는 여기서 한 번만 수행, orchestrator에는 결과 전달
        existing_profile = None if skip_cache else await self._get_cached_profile(corp_id, db_session)

        # P0-1 Fix: Execute orchestrator in thread pool to avoid blocking event loop
        # Orchestrator는 동기 함수이므로 run_in_executor로 래핑
        # P0 Fix: asyncio.get_running_loop() 사용 (async 컨텍스트에서 안전)
        loop = asyncio.get_running_loop()
        orchestrator_result = await loop.run_in_executor(
            self._executor,
            lambda: self.orchestrator.execute(
                corp_name=corp_name,
                industry_name=industry_name,
                industry_code=industry_code,
                existing_profile=existing_profile,
                skip_cache=skip_cache,
            )
        )

        # Build final profile with orchestrator result
        # P1: dart_fact_data 전달하여 DART Fact 데이터 우선 적용
        profile = self._build_final_profile(
            orchestrator_result=orchestrator_result,
            corp_id=corp_id,
            industry_name=industry_name,
            dart_fact_data=dart_fact_data,
        )

        # DART 2-Source Verification for shareholders
        # P1: DART Fact에서 이미 주주 데이터를 가져온 경우 스킵
        dart_shareholders_applied = (
            dart_fact_data and
            dart_fact_data.largest_shareholders and
            len(dart_fact_data.largest_shareholders) > 0
        )
        if DART_VERIFICATION_ENABLED and profile.get("shareholders") and not dart_shareholders_applied:
            try:
                perplexity_shareholders = profile.get("shareholders", [])
                verified_shareholders, dart_metadata = await self._verify_shareholders_with_dart(
                    corp_name=corp_name,
                    perplexity_shareholders=perplexity_shareholders,
                )
                profile["shareholders"] = verified_shareholders
                profile["shareholders_verification"] = dart_metadata

                # Update field_provenance for shareholders
                if dart_metadata.get("verified"):
                    profile["field_provenance"]["shareholders"] = {
                        "source": "DART_VERIFIED",
                        "confidence": "HIGH",
                        "source_url": "https://dart.fss.or.kr",
                        "verification_timestamp": datetime.now(UTC).isoformat(),
                    }
                    # Update field_confidences
                    if "field_confidences" not in profile:
                        profile["field_confidences"] = {}
                    profile["field_confidences"]["shareholders"] = "HIGH"

                logger.info(
                    f"[DART] Shareholders verified: source={dart_metadata.get('source')}, "
                    f"count={len(verified_shareholders)}"
                )
            except Exception as e:
                logger.warning(f"[DART] Shareholder verification failed: {e}")
                profile["shareholders_verification"] = {
                    "source": "PERPLEXITY_ONLY",
                    "verified": False,
                    "error": str(e),
                }

        # Validate the profile
        validation_result = self.validator.validate(profile)
        if not validation_result.is_valid:
            logger.warning(f"Validation errors: {validation_result.errors}")
            profile = validation_result.corrected_profile or profile
        profile["validation_warnings"] = validation_result.warnings

        # P0: Gemini Grounding Fact-Check (프로파일 저장 전 검증)
        # P1: Orchestrator에서 이미 팩트체크된 필드는 스킵 (Gemini 호출 통합)
        fact_check_hints = {}
        if orchestrator_result and hasattr(orchestrator_result, 'provenance'):
            # Gemini Validation 결과에서 fact_check_hints 추출 (provenance에 저장됨)
            fact_check_hints = orchestrator_result.provenance.get("gemini_fact_check_hints", {})
        profile = await self._fact_check_profile(profile, corp_name, fact_check_hints)

        # Save to DB
        if db_session:
            await self._save_profile(profile, db_session)
        else:
            # No async session provided - use sync session (Celery-safe)
            self._save_profile_sync(profile)

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

    async def _fact_check_profile(
        self,
        profile: dict,
        corp_name: str,
        fact_check_hints: Optional[dict] = None
    ) -> dict:
        """
        P0: Gemini Grounding 기반 프로파일 팩트체크
        P1: Orchestrator에서 이미 검증된 필드는 스킵 (Gemini 호출 통합)

        핵심 프로파일 필드를 Google Search로 검증합니다.
        검증 실패 시 confidence 하향 또는 필드 제거.

        Args:
            profile: 프로파일 딕셔너리
            corp_name: 기업명
            fact_check_hints: Orchestrator Gemini Validation에서 받은 사전 팩트체크 결과

        Returns:
            검증된 프로파일 (fact_check_results 포함)
        """
        fact_check_hints = fact_check_hints or {}
        fact_checker = get_fact_checker()

        if not fact_checker.is_available():
            logger.warning("[FactCheck] Gemini not available, skipping profile fact-check")
            profile["fact_check_status"] = "SKIPPED"
            return profile

        try:
            # 팩트체크 대상 필드 선정 (핵심 정보만)
            fields_to_check = self._get_fact_check_fields(profile, corp_name)

            if not fields_to_check:
                logger.info("[FactCheck] No fields to check")
                profile["fact_check_status"] = "NO_FIELDS"
                return profile

            # =========================================================================
            # P0 Performance: 배치 팩트체크로 병렬 실행 (8초 → 2초, 80% 단축)
            # P1 Gemini 호출 통합: Orchestrator에서 이미 검증된 필드는 스킵
            # =========================================================================
            import time
            start_time = time.time()

            # P1: fact_check_hints에서 이미 검증된 필드 분리
            already_checked = {}
            fields_need_check = {}

            for field_name, claim_info in fields_to_check.items():
                hint = fact_check_hints.get(field_name)
                if hint and hint.get("status") in ("VERIFIED", "UNVERIFIED", "SUSPICIOUS"):
                    # Orchestrator에서 이미 검증됨 → Gemini 호출 스킵
                    already_checked[field_name] = {
                        "result": hint["status"],
                        "confidence": 0.8 if hint["status"] == "VERIFIED" else 0.5,
                        "explanation": hint.get("reason", "Validated in Layer 1.5"),
                        "source": "GEMINI_LAYER_1_5",
                    }
                    logger.debug(f"[FactCheck] Skipping {field_name} (already checked in Layer 1.5)")
                else:
                    fields_need_check[field_name] = claim_info

            # 이미 검증된 필드 수 로깅
            if already_checked:
                logger.info(
                    f"[FactCheck] P1 optimization: {len(already_checked)} fields pre-verified, "
                    f"{len(fields_need_check)} fields need checking"
                )

            # 아직 검증 안 된 필드만 pseudo_signal로 변환
            pseudo_signals = []
            for field_name, claim_info in fields_need_check.items():
                pseudo_signal = {
                    "signal_type": "PROFILE",
                    "event_type": "PROFILE_FIELD",
                    "title": f"{corp_name} {field_name}",
                    "summary": claim_info["claim"],
                    "impact_direction": "NEUTRAL",
                    "impact_strength": "LOW",
                    "_field_name": field_name,  # 결과 매핑용
                }
                pseudo_signals.append(pseudo_signal)

            # 배치 병렬 팩트체크 (max_concurrent=5로 Gemini API 부하 분산)
            # P1: 검증 필요한 필드만 배치 팩트체크 (이미 검증된 필드는 스킵)
            fact_check_results = {}
            rejected_fields = []

            # 이미 검증된 필드 결과 먼저 추가
            for field_name, hint_result in already_checked.items():
                fact_check_results[field_name] = hint_result
                # SUSPICIOUS는 confidence 하향
                if hint_result.get("result") == "SUSPICIOUS":
                    if "field_confidences" in profile:
                        current = profile["field_confidences"].get(field_name, "MED")
                        if current == "HIGH":
                            profile["field_confidences"][field_name] = "MED"

            # 나머지 필드 배치 팩트체크 (pseudo_signals가 있을 때만)
            if pseudo_signals:
                batch_results = await fact_checker.check_signals_batch(
                    pseudo_signals,
                    corp_name,
                    max_concurrent=5,
                )

                for signal, result in batch_results:
                    field_name = signal.get("_field_name", "unknown")
                    fact_check_results[field_name] = result.to_dict()

                    # FALSE 결과 처리
                    if result.result == FactCheckResult.FALSE:
                        logger.warning(
                            f"[FactCheck] FALSE detected for {field_name}: {result.explanation}"
                        )
                        rejected_fields.append(field_name)
                        # 허위 필드는 null로 설정
                        if field_name in profile:
                            profile[field_name] = None
                        # field_confidences도 업데이트
                        if "field_confidences" in profile and field_name in profile.get("field_confidences", {}):
                            profile["field_confidences"][field_name] = "REJECTED"

                    # UNVERIFIED 결과 처리: confidence 하향
                    elif result.result == FactCheckResult.UNVERIFIED and result.confidence < 0.5:
                        logger.info(
                            f"[FactCheck] UNVERIFIED for {field_name}, downgrading confidence"
                        )
                        if "field_confidences" in profile and field_name in profile.get("field_confidences", {}):
                            current = profile["field_confidences"].get(field_name, "MED")
                            if current == "HIGH":
                                profile["field_confidences"][field_name] = "MED"
                            elif current == "MED":
                                profile["field_confidences"][field_name] = "LOW"

            elapsed = time.time() - start_time

            # 팩트체크 결과 저장
            profile["fact_check_results"] = fact_check_results
            profile["fact_check_rejected_fields"] = rejected_fields
            profile["fact_check_status"] = "COMPLETED"
            profile["fact_check_elapsed_ms"] = int(elapsed * 1000)
            profile["fact_check_pre_verified"] = len(already_checked)  # P1 메트릭

            logger.info(
                f"[FactCheck] Profile fact-check completed in {elapsed:.1f}s: "
                f"total={len(fields_to_check)}, pre_verified={len(already_checked)}, "
                f"batch_checked={len(pseudo_signals)}, rejected={len(rejected_fields)}"
            )

            return profile

        except Exception as e:
            logger.error(f"[FactCheck] Profile fact-check error: {e}")
            profile["fact_check_status"] = "ERROR"
            profile["fact_check_error"] = str(e)
            return profile

    def _get_fact_check_fields(self, profile: dict, corp_name: str) -> dict:
        """
        팩트체크 대상 필드 추출

        핵심 주장이 포함된 필드만 선별합니다.
        """
        fields = {}

        # 1. business_summary - 가장 중요한 팩트체크 대상
        if profile.get("business_summary"):
            fields["business_summary"] = {
                "claim": f"{corp_name}: {profile['business_summary'][:300]}",
            }

        # 2. revenue_krw - 매출액 검증
        if profile.get("revenue_krw"):
            revenue_billion = profile["revenue_krw"] / 100000000  # 억원 단위
            fields["revenue_krw"] = {
                "claim": f"{corp_name}의 연간 매출액은 약 {revenue_billion:.0f}억원입니다.",
            }

        # 3. ceo_name - 대표이사 검증
        if profile.get("ceo_name"):
            fields["ceo_name"] = {
                "claim": f"{corp_name}의 대표이사는 {profile['ceo_name']}입니다.",
            }

        # 4. shareholders - 주요 주주 검증 (DART 검증되지 않은 경우만)
        shareholders = profile.get("shareholders", [])
        shareholders_verification = profile.get("shareholders_verification", {})
        if shareholders and not shareholders_verification.get("verified"):
            # 상위 3명만 검증
            top_shareholders = shareholders[:3] if isinstance(shareholders, list) else []
            if top_shareholders:
                names = ", ".join([s.get("name", s) if isinstance(s, dict) else str(s) for s in top_shareholders])
                fields["shareholders"] = {
                    "claim": f"{corp_name}의 주요 주주: {names}",
                }

        # 5. export_ratio_pct - 수출 비중 (극단적 값만)
        export_ratio = profile.get("export_ratio_pct")
        if export_ratio is not None and (export_ratio > 90 or export_ratio < 5):
            fields["export_ratio_pct"] = {
                "claim": f"{corp_name}의 수출 비중은 {export_ratio}%입니다.",
            }

        # 6. employee_count - 임직원 수 (대규모 기업만)
        employee_count = profile.get("employee_count")
        if employee_count and employee_count > 1000:
            fields["employee_count"] = {
                "claim": f"{corp_name}의 임직원 수는 약 {employee_count}명입니다.",
            }

        return fields

    def _normalize_supply_chain(self, supply_chain: Any) -> dict:
        """
        Normalize supply_chain data structure.

        Ensures:
        - key_suppliers is a list of strings
        - supplier_countries is a dict with numeric values
        - single_source_risk is a list of strings (normalized from various types)
        - material_import_ratio_pct is numeric or None
        """
        if not supply_chain or not isinstance(supply_chain, dict):
            return {}

        normalized = {
            "key_suppliers": [],
            "supplier_countries": {},
            "single_source_risk": [],
            "material_import_ratio_pct": None,
        }

        # key_suppliers - ensure list of strings
        key_suppliers = supply_chain.get("key_suppliers")
        if key_suppliers:
            if isinstance(key_suppliers, list):
                normalized["key_suppliers"] = [str(s) for s in key_suppliers if s]
            elif isinstance(key_suppliers, str):
                normalized["key_suppliers"] = [key_suppliers]

        # supplier_countries - ensure dict with numeric values
        supplier_countries = supply_chain.get("supplier_countries")
        if supplier_countries and isinstance(supplier_countries, dict):
            normalized["supplier_countries"] = {
                str(k): v if isinstance(v, (int, float)) else 0
                for k, v in supplier_countries.items()
            }

        # single_source_risk - normalize using the helper function
        single_source_risk = supply_chain.get("single_source_risk")
        normalized["single_source_risk"] = normalize_single_source_risk(single_source_risk)

        # material_import_ratio_pct - ensure numeric or None
        import_ratio = supply_chain.get("material_import_ratio_pct") or supply_chain.get("raw_material_import_ratio")
        if import_ratio is not None:
            try:
                ratio_val = float(import_ratio)
                if 0 <= ratio_val <= 100:
                    normalized["material_import_ratio_pct"] = int(ratio_val)
            except (ValueError, TypeError):
                pass

        return normalized

    def _build_final_profile(
        self,
        orchestrator_result: OrchestratorResult,
        corp_id: str,
        industry_name: str,
        dart_fact_data: Optional[FactBasedProfileData] = None,
    ) -> dict:
        """
        Build final profile dict from orchestrator result.

        P1 Enhancement: DART Fact 데이터가 있으면 우선 적용 (100% Hallucination 제거)
        - CEO 이름, 설립연도, 본사 주소, 최대주주: DART 데이터 우선
        - 나머지 필드: Orchestrator 결과 사용

        Args:
            orchestrator_result: Orchestrator 실행 결과
            corp_id: 기업 ID
            industry_name: 업종명
            dart_fact_data: P1 DART Fact 데이터 (Optional)
        """
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

        # P0-1 Fix: Merge provenance from orchestrator AND provenance_tracker
        merged_provenance = {}
        # First, add orchestrator provenance
        if orchestrator_result.provenance:
            merged_provenance.update(orchestrator_result.provenance)
        # Then, merge provenance_tracker (overwrite if exists with more detail)
        tracker_provenance = self.provenance_tracker.to_json()
        if tracker_provenance:
            merged_provenance.update(tracker_provenance)
        # Also check raw_profile for any provenance data
        if raw_profile.get("field_provenance"):
            for field, prov in raw_profile.get("field_provenance", {}).items():
                if field not in merged_provenance:
                    merged_provenance[field] = prov

        # =========================================================================
        # P1+P4: DART Fact 데이터 우선 적용 (100% Hallucination 제거)
        # DART 공시 데이터가 있으면 LLM 추출 결과보다 우선
        # =========================================================================
        dart_ceo_name = None
        dart_founded_year = None
        dart_headquarters = None
        dart_shareholders = []
        dart_executives = []
        dart_jurir_no = None
        dart_corp_name_eng = None
        dart_acc_mt = None

        if dart_fact_data:
            # DART 기업개황에서 CEO, 설립연도, 본사 주소
            if dart_fact_data.company_info:
                dart_ceo_name = dart_fact_data.ceo_name
                dart_founded_year = dart_fact_data.founded_year
                dart_headquarters = dart_fact_data.headquarters
                # P4: 추가 필드 (jurir_no, corp_name_eng, acc_mt)
                dart_jurir_no = dart_fact_data.company_info.jurir_no
                dart_corp_name_eng = dart_fact_data.company_info.corp_name_eng
                dart_acc_mt = dart_fact_data.company_info.acc_mt
                logger.info(
                    f"[P1+P4-DART] Applying Fact data: CEO={dart_ceo_name}, "
                    f"Founded={dart_founded_year}, HQ={dart_headquarters[:30] if dart_headquarters else None}..., "
                    f"JurirNo={dart_jurir_no}, AccMt={dart_acc_mt}"
                )

            # DART 최대주주 현황
            if dart_fact_data.largest_shareholders:
                dart_shareholders = dart_fact_data.shareholders
                logger.info(f"[P1-DART] Applying {len(dart_shareholders)} shareholders from DART")

            # P4: DART 임원현황
            if hasattr(dart_fact_data, 'executives') and dart_fact_data.executives:
                dart_executives = [
                    {
                        "name": exec.nm,
                        "position": exec.ofcps or "",
                        "is_registered": exec.rgist_exctv_at == "등기임원",
                        "is_full_time": exec.fte_at == "상근",
                        "responsibilities": exec.chrg_job or "",
                    }
                    for exec in dart_fact_data.executives
                ]
                logger.info(f"[P4-DART] Applying {len(dart_executives)} executives from DART")

        profile = {
            "profile_id": str(uuid4()),
            "corp_id": corp_id,
            # Basic info
            "business_summary": raw_profile.get("business_summary", f"{industry_name} 업체"),
            "revenue_krw": raw_profile.get("revenue_krw"),
            "export_ratio_pct": raw_profile.get("export_ratio_pct"),
            # PRD v1.2 new fields - Basic info
            # P1+P4: DART Fact 우선, 없으면 LLM 결과 사용
            "ceo_name": dart_ceo_name or raw_profile.get("ceo_name"),
            "employee_count": raw_profile.get("employee_count"),
            "founded_year": dart_founded_year or raw_profile.get("founded_year"),
            "headquarters": dart_headquarters or raw_profile.get("headquarters"),
            # P4: DART 임원현황 우선 적용
            "executives": dart_executives if dart_executives else raw_profile.get("executives", []),
            # P4: DART 추가 필드 (LLM Context에 사용)
            "jurir_no": dart_jurir_no,
            "corp_name_eng": dart_corp_name_eng,
            "acc_mt": dart_acc_mt,
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
            # Normalize supply_chain to ensure proper structure
            "supply_chain": self._normalize_supply_chain(raw_profile.get("supply_chain", {})),
            "overseas_business": raw_profile.get("overseas_business", {}),
            # P1: DART 최대주주 우선, 없으면 LLM 결과 사용
            "shareholders": dart_shareholders if dart_shareholders else raw_profile.get("shareholders", []),
            # Metadata
            "profile_confidence": overall_confidence,
            "field_confidences": raw_profile.get("field_confidences", {}),
            "source_urls": raw_profile.get("source_urls", []),
            "raw_search_result": raw_profile.get("raw_search_result", {}),
            "field_provenance": merged_provenance,  # P0-1 Fix: Use merged provenance
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

        # P1-2 Fix: consensus_metadata 기본값 - consensus_at에 현재 시간 사용
        if orchestrator_result.consensus_metadata:
            profile["consensus_metadata"] = orchestrator_result.consensus_metadata.to_dict()
        else:
            # 캐시 히트 또는 메타데이터 없는 경우 기본값
            is_cache_hit = orchestrator_result.fallback_layer == FallbackLayer.CACHE
            profile["consensus_metadata"] = {
                # P1-2 Fix: None 대신 현재 시간 사용 (Frontend 파싱 오류 방지)
                "consensus_at": datetime.now(UTC).isoformat(),
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

        # =========================================================================
        # P1: DART Fact 데이터 출처 추적 (field_provenance 업데이트)
        # =========================================================================
        if dart_fact_data:
            dart_provenance = {
                "source": "DART",
                "source_url": "https://dart.fss.or.kr",
                "confidence": "HIGH",
                "is_fact": True,  # 100% Fact 데이터 표시
                "fetch_timestamp": dart_fact_data.fetch_timestamp,
            }

            if dart_ceo_name:
                profile["field_provenance"]["ceo_name"] = dart_provenance.copy()
                profile["field_confidences"]["ceo_name"] = "HIGH"

            if dart_founded_year:
                profile["field_provenance"]["founded_year"] = dart_provenance.copy()
                profile["field_confidences"]["founded_year"] = "HIGH"

            if dart_headquarters:
                profile["field_provenance"]["headquarters"] = dart_provenance.copy()
                profile["field_confidences"]["headquarters"] = "HIGH"

            if dart_shareholders:
                profile["field_provenance"]["shareholders"] = dart_provenance.copy()
                profile["field_confidences"]["shareholders"] = "HIGH"
                # 주주 정보는 이미 DART에서 가져왔으므로 검증 스킵 가능
                profile["shareholders_verification"] = {
                    "source": "DART_DIRECT",
                    "verified": True,
                    "dart_available": True,
                }

        return profile

    async def _verify_shareholders_with_dart(
        self,
        corp_name: str,
        perplexity_shareholders: list[dict],
    ) -> tuple[list[dict], dict]:
        """
        DART API를 사용하여 주주 정보 교차 검증

        2-Source Verification:
        1. Perplexity에서 추출한 주주 정보를 DART 공시와 비교
        2. 두 소스에서 일치하는 주주만 HIGH 신뢰도로 표시
        3. DART에만 있는 주주도 포함 (공시 데이터이므로 신뢰)
        4. Perplexity에만 있는 주주는 LOW 신뢰도로 경고

        Args:
            corp_name: 기업명
            perplexity_shareholders: Perplexity에서 추출한 주주 리스트

        Returns:
            (verified_shareholders, verification_metadata)
        """
        if not DART_VERIFICATION_ENABLED:
            logger.debug("[DART] Verification disabled, using Perplexity data as-is")
            return perplexity_shareholders, {"source": "PERPLEXITY_ONLY", "verified": False}

        try:
            verified, metadata = await get_verified_shareholders(
                corp_name=corp_name,
                perplexity_shareholders=perplexity_shareholders,
            )

            logger.info(
                f"[DART] Shareholder verification for '{corp_name}': "
                f"source={metadata.get('source')}, verified={metadata.get('verified')}"
            )

            return verified, metadata

        except Exception as e:
            logger.warning(f"[DART] Verification failed for '{corp_name}': {e}")
            # Fallback to Perplexity data with LOW confidence
            fallback_list = []
            for sh in perplexity_shareholders:
                sh_copy = dict(sh)
                sh_copy["confidence"] = "LOW"
                sh_copy["_note"] = f"DART 검증 실패: {str(e)}"
                fallback_list.append(sh_copy)

            return fallback_list, {
                "source": "PERPLEXITY_FALLBACK",
                "verified": False,
                "error": str(e),
            }

    def _sync_verify_shareholders_with_dart(
        self,
        corp_name: str,
        perplexity_shareholders: list[dict],
    ) -> tuple[list[dict], dict]:
        """
        Sync wrapper for DART verification (for use in _build_final_profile)
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._verify_shareholders_with_dart(corp_name, perplexity_shareholders)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self._verify_shareholders_with_dart(corp_name, perplexity_shareholders)
                )
        except Exception as e:
            logger.warning(f"[DART] Sync verification failed: {e}")
            return perplexity_shareholders, {"source": "PERPLEXITY_ONLY", "verified": False, "error": str(e)}

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
        """
        Sync wrapper for Perplexity search using 3-Phase strategy.

        Option B: 쿼리 분할 (3-Phase)
        - Phase 1: 기본 정보 + 재무
        - Phase 2: 해외 사업
        - Phase 3: 공급망 + 고객 + 경쟁사
        """
        import httpx
        import concurrent.futures

        # Use Key Rotator for Perplexity API key (supports _1, _2, _3 rotation)
        if not api_key:
            key_rotator = get_key_rotator()
            api_key = key_rotator.get_key("perplexity")
        if not api_key:
            logger.warning("Perplexity API key not configured")
            return {}

        industry_hints = getattr(self, '_industry_hints', None)

        # Build 3-Phase queries
        queries = {
            "phase1": build_phase1_query(corp_name, industry_name),
            "phase2": build_phase2_query(corp_name, industry_name, industry_hints),
            "phase3": build_phase3_query(corp_name, industry_name, industry_hints),
        }

        def execute_single_query(phase_name: str, query: str) -> tuple[str, dict]:
            """Execute a single Perplexity query."""
            try:
                with httpx.Client(timeout=45.0) as client:
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
                                    "content": "금융기관 기업심사 전문가입니다. 정확한 수치와 출처를 포함하여 답변합니다.",
                                },
                                {"role": "user", "content": query},
                            ],
                            "temperature": 0.1,
                            "max_tokens": 2500,
                        },
                    )
                    response.raise_for_status()
                    raw_response = response.json()
                    parsed = self.parser.parse_response(raw_response)
                    logger.info(f"{phase_name} search completed: {len(parsed.get('content', ''))} chars")
                    return phase_name, parsed
            except Exception as e:
                logger.error(f"{phase_name} search failed: {e}")
                return phase_name, {"content": "", "citations": [], "error": str(e)}

        # Execute 3 phases in parallel
        logger.info(f"Starting 3-Phase Perplexity search for {corp_name}")
        phase_results = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(execute_single_query, phase, query): phase
                for phase, query in queries.items()
            }

            for future in concurrent.futures.as_completed(futures):
                phase_name, result = future.result()
                phase_results[phase_name] = result

        # Summarize each phase with OpenAI (structured preservation)
        summarized = {}
        for phase_name in ["phase1", "phase2", "phase3"]:
            parsed = phase_results.get(phase_name, {})
            content = parsed.get("content", "")
            citations = parsed.get("citations", [])

            if content and self._llm_service:
                try:
                    summary = summarize_with_preservation(content, citations, self._llm_service)
                    summarized[phase_name] = summary
                    logger.info(f"{phase_name} summarization completed")
                except Exception as e:
                    logger.warning(f"{phase_name} summarization failed: {e}")
                    summarized[phase_name] = {"narrative": {"business_summary": content[:500]}}
            else:
                summarized[phase_name] = {"narrative": {"business_summary": content[:500] if content else ""}}

        # Merge 3-phase results
        merged_profile = merge_phase_results(
            summarized.get("phase1", {}),
            summarized.get("phase2", {}),
            summarized.get("phase3", {}),
        )

        # Add raw search results for audit
        merged_profile["raw_search_result"] = {
            "phase1_content": phase_results.get("phase1", {}).get("content", "")[:2000],
            "phase2_content": phase_results.get("phase2", {}).get("content", "")[:2000],
            "phase3_content": phase_results.get("phase3", {}).get("content", "")[:2000],
        }

        logger.info(f"3-Phase search completed for {corp_name}: {len(merged_profile.get('source_urls', []))} sources")
        return merged_profile

    # =========================================================================
    # v2.0 Architecture Methods
    # =========================================================================

    def _sync_gemini_fallback_search(
        self,
        corp_name: str,
        industry_name: str,
    ) -> dict:
        """
        v2.0: Gemini Grounding을 사용한 Fallback 검색

        Perplexity 실패 시에만 호출됨.
        MultiSearchManager를 통해 Gemini Grounding 검색 수행.
        """
        from app.worker.llm.prompts import build_corp_profile_query

        logger.info(f"[v2.0] Gemini fallback search for {corp_name}")

        # P0 Fix: KeyRotator와 api_key를 try 블록 밖에서 초기화
        # 실패 시에도 동일한 키를 마킹할 수 있도록 함
        key_rotator = get_key_rotator()
        api_key = key_rotator.get_key("google")

        if not api_key:
            logger.warning("[v2.0] Google API key not available")
            return {"error": "Google API key not configured"}

        try:
            # 검색 쿼리 생성
            query = build_corp_profile_query(corp_name, industry_name, group=0)

            # Gemini Grounding 호출
            import google.generativeai as genai
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",
                tools="google_search_retrieval",
            )

            response = model.generate_content(query)
            content = response.text if response.text else ""

            # Citations 추출
            citations = []
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    grounding = candidate.grounding_metadata
                    if hasattr(grounding, 'grounding_chunks'):
                        for chunk in grounding.grounding_chunks:
                            if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
                                citations.append(chunk.web.uri)

            # 성공 기록
            key_rotator.mark_success("google", api_key)

            logger.info(f"[v2.0] Gemini fallback success for {corp_name}: {len(citations)} citations")

            return {
                "content": content,
                "citations": citations,
                "source": "GEMINI_GROUNDING",
                "_search_source": "GEMINI_FALLBACK",
            }

        except Exception as e:
            logger.error(f"[v2.0] Gemini fallback failed for {corp_name}: {e}")
            # P0 Fix: 원래 사용한 api_key를 실패 마킹 (새 키를 가져오지 않음)
            try:
                key_rotator.mark_failed("google", api_key)
            except Exception:
                pass
            return {"error": str(e)}

    def _sync_openai_validation(
        self,
        profile: dict,
        corp_name: str,
        industry_name: str,
        source: str,
        llm_service=None,
    ) -> ValidationResult:
        """
        v2.0: OpenAI를 사용한 프로필 검증

        Layer 2에서 호출됨.
        Hallucination 탐지, 범위 검증, 내부 일관성 검증 수행.
        """
        logger.info(f"[v2.0] OpenAI validation for {corp_name} (source={source})")

        try:
            # Validator 인스턴스 가져오기
            validator = get_validator()

            # 기본 검증 수행
            result = validator.validate(
                profile=profile,
                corp_name=corp_name,
                industry_name=industry_name,
                source=source,
            )

            # 경고 수 기반 로깅
            error_count = len([i for i in result.issues if i.severity.value == "ERROR"])
            warning_count = len([i for i in result.issues if i.severity.value == "WARNING"])

            logger.info(
                f"[v2.0] Validation completed for {corp_name}: "
                f"valid={result.is_valid}, confidence={result.confidence.value}, "
                f"errors={error_count}, warnings={warning_count}"
            )

            return result

        except Exception as e:
            logger.error(f"[v2.0] OpenAI validation failed for {corp_name}: {e}")
            # 검증 실패 시에도 프로필 사용 가능 (경고만)
            from app.worker.llm.validator import (
                ValidationResult, ConfidenceLevel, ValidationIssue, ValidationSeverity
            )
            return ValidationResult(
                is_valid=True,  # 검증 실패해도 프로필은 사용
                confidence=ConfidenceLevel.LOW,
                issues=[ValidationIssue(
                    field_name="validation",
                    severity=ValidationSeverity.WARNING,
                    message=f"Validation failed: {str(e)}",
                )],
                validated_profile=profile,
                validation_metadata={"error": str(e)},
            )

    def _sync_perplexity_search_legacy(
        self,
        corp_name: str,
        industry_name: str,
        api_key: Optional[str],
    ) -> dict:
        """
        Legacy single-query Perplexity search.
        DEPRECATED: Use _sync_perplexity_search (3-Phase) instead.
        """
        import httpx

        # Use Key Rotator for Perplexity API key (supports _1, _2, _3 rotation)
        if not api_key:
            key_rotator = get_key_rotator()
            api_key = key_rotator.get_key("perplexity")
        if not api_key:
            logger.warning("Perplexity API key not configured")
            return {}

        # PRD v1.2: 19개 필드를 위한 종합 쿼리 (업종 힌트 포함)
        industry_hints = getattr(self, '_industry_hints', None)
        query = build_perplexity_query(corp_name, industry_name, industry_hints)

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
        # Build industry hints text for prompt
        industry_hints = getattr(self, '_industry_hints', {})
        industry_hints_text = ""
        if industry_hints:
            materials = industry_hints.get("typical_materials", [])[:5]
            suppliers = industry_hints.get("typical_suppliers", [])[:5]
            markets = industry_hints.get("export_markets", [])[:5]
            risks = industry_hints.get("risk_factors", [])[:3]
            growth = industry_hints.get("growth_drivers", [])[:3]

            hints_parts = []
            if materials:
                hints_parts.append(f"- 이 업종 주요 원자재: {', '.join(materials)}")
            if suppliers:
                hints_parts.append(f"- 이 업종 주요 공급사 유형: {', '.join(suppliers)}")
            if markets:
                hints_parts.append(f"- 이 업종 주요 수출국: {', '.join(markets)}")
            if risks:
                hints_parts.append(f"- 업종 리스크 요인: {', '.join(risks)}")
            if growth:
                hints_parts.append(f"- 업종 성장 동력: {', '.join(growth)}")

            if hints_parts:
                industry_hints_text = "\n## 업종 특성 힌트 (추론 시 참고)\n" + "\n".join(hints_parts)

        system_prompt = PROFILE_EXTRACTION_SYSTEM_PROMPT
        user_prompt = PROFILE_EXTRACTION_USER_PROMPT.format(
            search_results=content[:8000],  # Limit content length
            corp_name=corp_name,
            industry_name=industry_name,
            industry_hints_text=industry_hints_text,
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
                    # P0-2 Fix: Record provenance even for simple values
                    profile[field_name] = field_data
                    # Only record if value is not empty
                    if field_data and field_data not in [[], {}, "", 0]:
                        self.provenance_tracker.record(
                            field_name=field_name,
                            value=field_data,
                            source_url=None,  # Unknown source
                            excerpt=None,
                            confidence="LOW",  # Default to LOW for unstructured responses
                        )

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

        # Build industry hints text (P0-FIX: 누락된 파라미터 추가)
        industry_hints = getattr(self, '_industry_hints', {})
        industry_hints_text = ""
        if industry_hints:
            materials = industry_hints.get("typical_materials", [])[:5]
            suppliers = industry_hints.get("typical_suppliers", [])[:5]
            markets = industry_hints.get("export_markets", [])[:5]
            risks = industry_hints.get("risk_factors", [])[:3]
            growth = industry_hints.get("growth_drivers", [])[:3]

            hints_parts = []
            if materials:
                hints_parts.append(f"- 이 업종 주요 원자재: {', '.join(materials)}")
            if suppliers:
                hints_parts.append(f"- 이 업종 주요 공급사 유형: {', '.join(suppliers)}")
            if markets:
                hints_parts.append(f"- 이 업종 주요 수출국: {', '.join(markets)}")
            if risks:
                hints_parts.append(f"- 업종 리스크 요인: {', '.join(risks)}")
            if growth:
                hints_parts.append(f"- 업종 성장 동력: {', '.join(growth)}")

            if hints_parts:
                industry_hints_text = "\n## 업종 특성 힌트 (추론 시 참고)\n" + "\n".join(hints_parts)

        return PROFILE_EXTRACTION_USER_PROMPT.format(
            corp_name=corp_name,
            industry_name=industry_name,
            search_results=sources_text + discrepancy_text,
            industry_hints_text=industry_hints_text,
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
                    # P0-3 Fix: Include field_provenance and other audit fields
                    "field_provenance": row.field_provenance or {},
                    "field_confidences": row.field_confidences or {},
                    "source_urls": list(row.source_urls or []),
                    # PRD v1.2 fields
                    "ceo_name": row.ceo_name if hasattr(row, 'ceo_name') else None,
                    "employee_count": row.employee_count if hasattr(row, 'employee_count') else None,
                    "founded_year": row.founded_year if hasattr(row, 'founded_year') else None,
                    "headquarters": row.headquarters if hasattr(row, 'headquarters') else None,
                    "executives": row.executives if hasattr(row, 'executives') else [],
                    "industry_overview": row.industry_overview if hasattr(row, 'industry_overview') else None,
                    "business_model": row.business_model if hasattr(row, 'business_model') else None,
                    "supply_chain": row.supply_chain if hasattr(row, 'supply_chain') else {},
                    "overseas_business": row.overseas_business if hasattr(row, 'overseas_business') else {},
                    "shareholders": row.shareholders if hasattr(row, 'shareholders') else [],
                    "competitors": row.competitors if hasattr(row, 'competitors') else [],
                    "macro_factors": row.macro_factors if hasattr(row, 'macro_factors') else [],
                    "consensus_metadata": row.consensus_metadata if hasattr(row, 'consensus_metadata') else None,
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

        # Use Key Rotator for Perplexity API key (supports _1, _2, _3 rotation)
        if not api_key:
            key_rotator = get_key_rotator()
            api_key = key_rotator.get_key("perplexity")
        if not api_key:
            logger.warning("Perplexity API key not configured")
            return {"content": "", "citations": [], "source_quality": "LOW", "raw_response": {}}

        # PRD v1.2: 19개 필드를 위한 종합 쿼리 (업종 힌트 포함)
        industry_hints = getattr(self, '_industry_hints', None)
        query = build_perplexity_query(corp_name, industry_name, industry_hints)

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

        # Build industry hints text (P0-FIX: 누락된 파라미터 추가)
        industry_hints = getattr(self, '_industry_hints', {})
        industry_hints_text = ""
        if industry_hints:
            hints_parts = []
            materials = industry_hints.get("typical_materials", [])[:5]
            if materials:
                hints_parts.append(f"- 이 업종 주요 원자재: {', '.join(materials)}")
            suppliers = industry_hints.get("typical_suppliers", [])[:5]
            if suppliers:
                hints_parts.append(f"- 이 업종 주요 공급사 유형: {', '.join(suppliers)}")
            if hints_parts:
                industry_hints_text = "\n## 업종 특성 힌트 (추론 시 참고)\n" + "\n".join(hints_parts)

        messages = [
            {"role": "system", "content": PROFILE_EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": PROFILE_EXTRACTION_USER_PROMPT.format(
                    corp_name=corp_name,
                    industry_name=industry_name,
                    search_results=raw_results.get("content", "검색 결과 없음"),
                    industry_hints_text=industry_hints_text,
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

    def _save_profile_sync(self, profile: dict) -> None:
        """Save profile to database using sync session (for Celery workers)."""
        from app.worker.db import get_sync_db
        from sqlalchemy import text

        try:
            with get_sync_db() as db:
                # Same query as async version
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
                        -- P2-2 Fix: 조건부 TTL 업데이트 (동기 버전)
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

                db.execute(query, {
                    "profile_id": str(profile.get("profile_id", "")),
                    "corp_id": profile.get("corp_id", ""),
                    "business_summary": profile.get("business_summary"),
                    "revenue_krw": profile.get("revenue_krw"),
                    "export_ratio_pct": profile.get("export_ratio_pct"),
                    "country_exposure": safe_json_dumps(profile.get("country_exposure", {})),
                    "key_materials": profile.get("key_materials", []),
                    "key_customers": profile.get("key_customers", []),
                    "overseas_operations": profile.get("overseas_operations", []),
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
                db.commit()
                logger.info(f"Saved profile (sync) for {profile['corp_id']}")

        except Exception as e:
            logger.error(f"Failed to save profile (sync): {e}")


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
