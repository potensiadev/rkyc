"""
Field Assignment Configuration
한국어 특화 - Perplexity vs Gemini 필드 분담

설계 원칙:
1. Perplexity: 한국 공시/뉴스 데이터에 강점 (DART, 무역협회 등)
2. Gemini: 일반 정보/글로벌 정보에 적합
3. Cross-Validation: 정확도가 중요한 필드는 둘 다 검색 후 비교

사용법:
    from app.worker.llm.field_assignment import (
        get_field_assignment,
        is_perplexity_primary,
        is_gemini_acceptable,
        requires_cross_validation,
    )

    assignment = get_field_assignment("revenue_krw")
    # → FieldAssignment(provider=PERPLEXITY_PRIMARY, cross_validate=True)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class FieldProvider(str, Enum):
    """필드 담당 Provider"""
    PERPLEXITY_PRIMARY = "PERPLEXITY_PRIMARY"  # Perplexity가 주로 담당
    GEMINI_ACCEPTABLE = "GEMINI_ACCEPTABLE"    # Gemini도 허용 가능
    CROSS_VALIDATION = "CROSS_VALIDATION"      # 둘 다 검색 후 비교 필수


@dataclass
class FieldAssignment:
    """필드별 할당 정보"""
    field_name: str
    provider: FieldProvider
    cross_validate: bool  # True면 두 Provider 모두 검색 후 비교
    confidence_weight: float  # 해당 Provider의 신뢰도 가중치 (0.0 ~ 1.0)
    description: str = ""


# ============================================================================
# Perplexity 전담 필드 (한국 공시/뉴스 강점)
# ============================================================================

PERPLEXITY_PRIMARY_FIELDS: dict[str, FieldAssignment] = {
    # 재무 정보 (DART 공시 데이터)
    "revenue_krw": FieldAssignment(
        field_name="revenue_krw",
        provider=FieldProvider.PERPLEXITY_PRIMARY,
        cross_validate=True,  # 정확도 중요
        confidence_weight=0.95,
        description="매출액 - DART 공시 데이터 기반",
    ),
    "financial_history": FieldAssignment(
        field_name="financial_history",
        provider=FieldProvider.PERPLEXITY_PRIMARY,
        cross_validate=False,
        confidence_weight=0.90,
        description="재무제표 3개년 - DART 공시",
    ),
    # 수출/무역 정보 (한국무역협회)
    "export_ratio_pct": FieldAssignment(
        field_name="export_ratio_pct",
        provider=FieldProvider.PERPLEXITY_PRIMARY,
        cross_validate=True,  # 시그널 트리거 필드
        confidence_weight=0.90,
        description="수출 비중 - 한국무역협회 데이터",
    ),
    # 주주/지배구조 (공시)
    "shareholders": FieldAssignment(
        field_name="shareholders",
        provider=FieldProvider.PERPLEXITY_PRIMARY,
        cross_validate=True,  # 지배구조 분석 중요
        confidence_weight=0.95,
        description="주주 구성 - 공시 데이터",
    ),
    # 한국 시장 정보
    "key_customers": FieldAssignment(
        field_name="key_customers",
        provider=FieldProvider.PERPLEXITY_PRIMARY,
        cross_validate=False,
        confidence_weight=0.85,
        description="주요 고객사 - 한국 시장 뉴스",
    ),
    "key_materials": FieldAssignment(
        field_name="key_materials",
        provider=FieldProvider.PERPLEXITY_PRIMARY,
        cross_validate=False,
        confidence_weight=0.85,
        description="주요 원자재 - 한국 무역 데이터",
    ),
    "competitors": FieldAssignment(
        field_name="competitors",
        provider=FieldProvider.PERPLEXITY_PRIMARY,
        cross_validate=False,
        confidence_weight=0.80,
        description="경쟁사 - 한국 시장 분석",
    ),
    "industry_overview": FieldAssignment(
        field_name="industry_overview",
        provider=FieldProvider.PERPLEXITY_PRIMARY,
        cross_validate=False,
        confidence_weight=0.80,
        description="업종 현황 - 한국 산업 동향",
    ),
}


# ============================================================================
# Gemini 허용 필드 (일반/글로벌 정보)
# ============================================================================

GEMINI_ACCEPTABLE_FIELDS: dict[str, FieldAssignment] = {
    # 기본 정보 (변동 적음)
    "ceo_name": FieldAssignment(
        field_name="ceo_name",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.85,
        description="CEO 이름 - 변동 적음",
    ),
    "employee_count": FieldAssignment(
        field_name="employee_count",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.75,
        description="직원 수 - 대략적 OK",
    ),
    "founded_year": FieldAssignment(
        field_name="founded_year",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.95,
        description="설립 연도 - 고정값",
    ),
    "headquarters": FieldAssignment(
        field_name="headquarters",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.90,
        description="본사 위치",
    ),
    # 사업 개요
    "business_summary": FieldAssignment(
        field_name="business_summary",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.80,
        description="사업 개요",
    ),
    "business_model": FieldAssignment(
        field_name="business_model",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.80,
        description="비즈니스 모델",
    ),
    # 글로벌 정보
    "overseas_operations": FieldAssignment(
        field_name="overseas_operations",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.80,
        description="해외 사업 - 글로벌 정보",
    ),
    "overseas_business": FieldAssignment(
        field_name="overseas_business",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.80,
        description="해외 법인",
    ),
    "country_exposure": FieldAssignment(
        field_name="country_exposure",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.75,
        description="국가별 노출도",
    ),
    "supply_chain": FieldAssignment(
        field_name="supply_chain",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.75,
        description="글로벌 공급망",
    ),
    "macro_factors": FieldAssignment(
        field_name="macro_factors",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.70,
        description="거시 요인",
    ),
    "executives": FieldAssignment(
        field_name="executives",
        provider=FieldProvider.GEMINI_ACCEPTABLE,
        cross_validate=False,
        confidence_weight=0.80,
        description="주요 경영진",
    ),
}


# ============================================================================
# Cross-Validation 필수 필드 (둘 다 검색 후 비교)
# ============================================================================

CROSS_VALIDATION_REQUIRED: set[str] = {
    "revenue_krw",       # 매출 - 정확도 critical
    "export_ratio_pct",  # 수출비중 - 시그널 트리거
    "shareholders",      # 주주 - 지배구조 분석
}


# ============================================================================
# 출처 신뢰도 (Domain-based)
# ============================================================================

SOURCE_CREDIBILITY = {
    # 공시 (최고 신뢰도)
    "dart.fss.or.kr": 100,
    "kind.krx.co.kr": 100,
    "opendart.fss.or.kr": 100,
    # 공식 IR
    "ir.": 90,  # prefix match
    "investor.": 90,
    # 정부/공공 통계
    "kostat.go.kr": 95,
    "kita.net": 90,  # 한국무역협회
    "kosis.kr": 90,
    # 주요 언론
    "hankyung.com": 80,
    "mk.co.kr": 80,
    "sedaily.com": 80,
    "reuters.com": 85,
    "bloomberg.com": 85,
    # 일반 뉴스
    "news.": 60,  # prefix match
    "default": 50,
}


def get_source_credibility(url: str) -> int:
    """URL에서 출처 신뢰도 점수 반환"""
    if not url:
        return SOURCE_CREDIBILITY["default"]

    url_lower = url.lower()

    # 정확한 도메인 매칭 (전체 도메인 먼저)
    exact_domains = [
        "dart.fss.or.kr", "kind.krx.co.kr", "opendart.fss.or.kr",
        "kostat.go.kr", "kita.net", "kosis.kr",
        "hankyung.com", "mk.co.kr", "sedaily.com",
        "reuters.com", "bloomberg.com",
    ]
    for domain in exact_domains:
        if domain in url_lower:
            return SOURCE_CREDIBILITY[domain]

    # Prefix 매칭 (서브도메인으로 시작하는 경우)
    # "ir.company.com" 또는 "investor.company.com" 패턴
    import re
    if re.search(r'https?://ir\.', url_lower) or re.search(r'https?://[^/]*\.ir\.', url_lower):
        return 90  # ir. prefix
    if re.search(r'https?://investor\.', url_lower):
        return 90  # investor. prefix
    if re.search(r'https?://news\.', url_lower) or '/news/' in url_lower:
        return 60  # news. prefix or /news/ path

    # 기본값
    return SOURCE_CREDIBILITY["default"]


# ============================================================================
# Helper Functions
# ============================================================================

# 통합 필드 맵
_ALL_FIELDS: dict[str, FieldAssignment] = {
    **PERPLEXITY_PRIMARY_FIELDS,
    **GEMINI_ACCEPTABLE_FIELDS,
}


def get_field_assignment(field_name: str) -> Optional[FieldAssignment]:
    """필드별 할당 정보 조회"""
    return _ALL_FIELDS.get(field_name)


def is_perplexity_primary(field_name: str) -> bool:
    """Perplexity 전담 필드인지 확인"""
    return field_name in PERPLEXITY_PRIMARY_FIELDS


def is_gemini_acceptable(field_name: str) -> bool:
    """Gemini 허용 필드인지 확인"""
    return field_name in GEMINI_ACCEPTABLE_FIELDS


def requires_cross_validation(field_name: str) -> bool:
    """Cross-Validation 필수 필드인지 확인"""
    return field_name in CROSS_VALIDATION_REQUIRED


def get_perplexity_fields() -> list[str]:
    """Perplexity 전담 필드 목록"""
    return list(PERPLEXITY_PRIMARY_FIELDS.keys())


def get_gemini_fields() -> list[str]:
    """Gemini 허용 필드 목록"""
    return list(GEMINI_ACCEPTABLE_FIELDS.keys())


def get_cross_validation_fields() -> list[str]:
    """Cross-Validation 필수 필드 목록"""
    return list(CROSS_VALIDATION_REQUIRED)


def get_all_profile_fields() -> list[str]:
    """모든 프로필 필드 목록"""
    return list(_ALL_FIELDS.keys())


def get_field_confidence_weight(field_name: str, provider: str) -> float:
    """
    필드별 Provider의 신뢰도 가중치 반환

    Args:
        field_name: 필드명
        provider: "perplexity" 또는 "gemini"

    Returns:
        신뢰도 가중치 (0.0 ~ 1.0)
    """
    assignment = get_field_assignment(field_name)
    if not assignment:
        return 0.5  # 알 수 없는 필드

    # Perplexity Primary 필드를 Gemini가 제공하면 신뢰도 낮춤
    if provider.lower() == "gemini" and is_perplexity_primary(field_name):
        return assignment.confidence_weight * 0.7

    # Gemini Acceptable 필드를 Perplexity가 제공해도 OK
    return assignment.confidence_weight


def select_best_value(
    field_name: str,
    perplexity_value: Any,
    gemini_value: Any,
    perplexity_source: Optional[str] = None,
    gemini_source: Optional[str] = None,
) -> tuple[Any, str, float]:
    """
    두 Provider의 값 중 최선 선택

    Args:
        field_name: 필드명
        perplexity_value: Perplexity 검색 결과
        gemini_value: Gemini 검색 결과
        perplexity_source: Perplexity 출처 URL
        gemini_source: Gemini 출처 URL

    Returns:
        (선택된 값, 선택된 Provider, 신뢰도)
    """
    # 둘 다 없으면 None
    if perplexity_value is None and gemini_value is None:
        return None, "NONE", 0.0

    # 하나만 있으면 그 값 반환
    if perplexity_value is None:
        weight = get_field_confidence_weight(field_name, "gemini")
        return gemini_value, "GEMINI", weight
    if gemini_value is None:
        weight = get_field_confidence_weight(field_name, "perplexity")
        return perplexity_value, "PERPLEXITY", weight

    # 둘 다 있으면 출처 신뢰도 + 필드 할당 기반 선택
    p_source_score = get_source_credibility(perplexity_source)
    g_source_score = get_source_credibility(gemini_source)

    p_field_weight = get_field_confidence_weight(field_name, "perplexity")
    g_field_weight = get_field_confidence_weight(field_name, "gemini")

    # 최종 점수 = 출처 신뢰도 × 필드 가중치
    p_score = p_source_score * p_field_weight
    g_score = g_source_score * g_field_weight

    if p_score >= g_score:
        return perplexity_value, "PERPLEXITY", p_field_weight
    else:
        return gemini_value, "GEMINI", g_field_weight
