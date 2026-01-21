"""
4-Layer LLM Architecture for Enterprise Analysis

Production-grade architecture with:
- Layer 1 (Intake): Input validation, entity matching, source credibility
- Layer 2 (Evidence): Evidence collection, cross-verification, counter-evidence
- Layer 3 (Expert Analysis): Corporation/Signal expert analysis with Wall Street quality
- Layer 4 (Quality Gate): Null-free enforcement, schema validation, final output

Anti-hallucination policy: NULL/빈값/'정보 없음' 금지
All fields must be filled with: 추정값 + 근거 + 범위/신뢰도
"""

import json
import hashlib
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Any

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class SourceCredibility(str, Enum):
    """Source credibility grades (PRD Evidence Map)"""
    A = "A"  # 공시(DART), 정부 발표, 감사보고서
    B = "B"  # 주요 경제지(한경, 매일경제), IR자료
    C = "C"  # 일반 뉴스, 추정 필요한 경우


class ImpactPath(str, Enum):
    """Impact path categories for signal analysis"""
    REVENUE = "REVENUE"              # 매출 영향
    COST = "COST"                    # 원가 영향
    REGULATION = "REGULATION"        # 규제 영향
    DEMAND = "DEMAND"                # 수요 영향
    SUPPLY_CHAIN = "SUPPLY_CHAIN"    # 공급망 영향
    FINANCING = "FINANCING"          # 자금조달 영향
    REPUTATION = "REPUTATION"        # 평판 영향
    OPERATIONAL = "OPERATIONAL"      # 운영 영향


class ConfidenceLevel(str, Enum):
    """Confidence level with clear criteria"""
    HIGH = "HIGH"   # 공시, 정부발표, 내부데이터 (정확도 90%+)
    MED = "MED"     # 주요 언론, IR자료 (정확도 70-90%)
    LOW = "LOW"     # 단일 출처, 추정 필요 (정확도 50-70%)


# Credibility criteria mapping
CREDIBILITY_CRITERIA = {
    SourceCredibility.A: {
        "description": "공시/정부발표/감사보고서",
        "domains": ["dart.fss.or.kr", "kind.krx.co.kr", "gov.kr", "kostat.go.kr"],
        "keywords": ["공시", "감사보고서", "정부 발표", "통계청"],
        "accuracy_range": "90%+"
    },
    SourceCredibility.B: {
        "description": "주요 경제지/IR자료",
        "domains": ["hankyung.com", "mk.co.kr", "sedaily.com", "etnews.com", "thebell.co.kr"],
        "keywords": ["IR", "투자설명서", "사업보고서"],
        "accuracy_range": "70-90%"
    },
    SourceCredibility.C: {
        "description": "일반 뉴스/추정",
        "domains": [],  # Catch-all for others
        "keywords": ["추정", "예상", "전망"],
        "accuracy_range": "50-70%"
    },
}


# =============================================================================
# Data Classes for Layer Outputs
# =============================================================================

@dataclass
class IntakeOutput:
    """Layer 1 (Intake) output schema"""
    # Entity validation
    corp_id: str
    corp_name: str
    corp_reg_no: str
    biz_no: str
    industry_code: str
    industry_name: str

    # Validation results
    entity_match_verified: bool
    entity_match_method: str  # "exact_match", "fuzzy_match", "manual_override"

    # Date validation
    signal_date: str  # ISO format
    signal_date_verified: bool
    date_validation_method: str  # "timestamp", "article_date", "estimated"

    # Entity discrepancies (Moved here to fix non-default argument following default argument error)
    entity_discrepancies: list[dict] = field(default_factory=list)

    # Source labeling
    sources: list[dict] = field(default_factory=list)  # [{url, credibility, domain, validated}]
    primary_source_credibility: str = "C"

    # Processing metadata
    intake_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    intake_version: str = "v2.0"

    # Checklist completion
    checklist: dict = field(default_factory=lambda: {
        "entity_validated": False,
        "date_validated": False,
        "sources_labeled": False,
        "credibility_assigned": False
    })


@dataclass
class EvidenceEntry:
    """Single evidence entry with claim linking"""
    evidence_id: str                      # Unique ID for claim linking
    claim_ids: list[str]                  # Linked claim IDs
    evidence_type: str                    # INTERNAL_FIELD, DOC, EXTERNAL
    ref_type: str                         # SNAPSHOT_KEYPATH, DOC_PAGE, URL
    ref_value: str                        # Actual reference
    snippet: str                          # Evidence text (max 200 chars)
    credibility_grade: str                # A, B, C
    credibility_reason: str               # Why this grade
    is_counter_evidence: bool = False     # Counter-evidence flag
    cross_verified: bool = False          # Cross-verification status
    cross_verification_sources: list[str] = field(default_factory=list)


@dataclass
class EvidenceMapOutput:
    """Layer 2 (Evidence) output schema"""
    corp_id: str

    # Claims list
    claims: list[dict] = field(default_factory=list)  # [{claim_id, statement, category}]

    # Evidence entries linked to claims
    evidence_entries: list[EvidenceEntry] = field(default_factory=list)

    # Counter-evidence (minimum 1 required)
    counter_evidence: list[EvidenceEntry] = field(default_factory=list)

    # Cross-verification summary
    cross_verification_summary: dict = field(default_factory=lambda: {
        "total_claims": 0,
        "verified_claims": 0,
        "verification_rate": 0.0,
        "duplicate_sources_removed": 0
    })

    # Evidence quality metrics
    quality_metrics: dict = field(default_factory=lambda: {
        "grade_a_count": 0,
        "grade_b_count": 0,
        "grade_c_count": 0,
        "average_credibility_score": 0.0
    })

    evidence_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class CorporationAnalysis:
    """Expert corporation analysis output (Wall Street quality)"""

    # 1. 사업 구조 (Business Structure) - REQUIRED
    business_structure: dict = field(default_factory=lambda: {
        "core_business": "",           # 핵심 사업 (추정값 허용 + 근거)
        "revenue_segments": [],        # 매출 구성 [{segment, ratio_pct, trend}]
        "value_chain_position": "",    # 밸류체인 위치
        "key_assets": [],              # 핵심 자산
        "business_model": "",          # 비즈니스 모델
        "_evidence_ids": [],           # Linked evidence
        "_estimation_basis": ""        # 추정 근거 (정보 부족 시)
    })

    # 2. 시장 지위 (Market Position) - REQUIRED
    market_position: dict = field(default_factory=lambda: {
        "market_share_range": "",      # 시장점유율 범위 (예: "5-10%")
        "market_share_confidence": "", # HIGH/MED/LOW
        "competitive_position": "",    # 1위/상위권/중위권/하위권
        "market_size_estimate": "",    # 시장 규모 추정
        "market_growth_trend": "",     # 성장/정체/축소
        "entry_barriers": [],          # 진입장벽
        "_evidence_ids": [],
        "_estimation_basis": ""
    })

    # 3. 재무 프로필 (Financial Profile) - REQUIRED
    financial_profile: dict = field(default_factory=lambda: {
        # 수익성 (Profitability)
        "profitability": {
            "revenue_trend": "",       # 증가/정체/감소
            "revenue_range_krw": "",   # 매출 범위 (예: "500억-1000억")
            "margin_trend": "",        # 개선/유지/악화
            "margin_range_pct": "",    # 마진 범위 (예: "5-10%")
            "risk_factors": []         # 수익성 리스크 요인
        },
        # 안정성 (Stability)
        "stability": {
            "debt_level": "",          # 상/중/하
            "debt_ratio_range": "",    # 부채비율 범위
            "liquidity_level": "",     # 상/중/하
            "liquidity_trend": "",     # 개선/유지/악화
            "risk_factors": []         # 안정성 리스크 요인
        },
        # 성장성 (Growth)
        "growth": {
            "revenue_growth_trend": "",    # 고성장/성장/정체/역성장
            "investment_intensity": "",    # 상/중/하
            "capex_trend": "",             # 확대/유지/축소
            "risk_factors": []             # 성장성 리스크 요인
        },
        "_evidence_ids": [],
        "_estimation_basis": ""
    })

    # 4. 리스크 맵 (Risk Map) - REQUIRED
    risk_map: dict = field(default_factory=lambda: {
        "credit_risks": [],            # 신용 리스크 [{risk, severity, likelihood}]
        "operational_risks": [],       # 운영 리스크
        "market_risks": [],            # 시장 리스크
        "regulatory_risks": [],        # 규제 리스크
        "concentration_risks": [],     # 집중 리스크 (고객, 공급사, 지역)
        "overall_risk_level": "",      # 상/중/하
        "_evidence_ids": [],
        "_estimation_basis": ""
    })

    # 5. 촉매 (Catalysts) - REQUIRED
    catalysts: dict = field(default_factory=lambda: {
        "positive_catalysts": [],      # 긍정적 촉매 [{catalyst, timeline, probability}]
        "negative_catalysts": [],      # 부정적 촉매
        "near_term_events": [],        # 단기 이벤트 (3개월 내)
        "medium_term_events": [],      # 중기 이벤트 (1년 내)
        "_evidence_ids": [],
        "_estimation_basis": ""
    })

    # 6. 비교군 (Peer Comparison) - REQUIRED (최소 2개 지표)
    peer_comparison: dict = field(default_factory=lambda: {
        "peer_companies": [],          # 비교 대상 기업들
        "comparison_metrics": [],      # 비교 지표 [{metric, company_value, peer_avg, position}]
        "relative_position": "",       # 업종 대비 위치
        "competitive_advantages": [],  # 경쟁 우위
        "competitive_disadvantages": [],  # 경쟁 열위
        "_evidence_ids": [],
        "_estimation_basis": ""
    })

    # 7. ESG/거버넌스 (ESG & Governance) - REQUIRED
    esg_governance: dict = field(default_factory=lambda: {
        # Environmental
        "environmental": {
            "carbon_risk_level": "",       # 상/중/하/해당없음
            "environmental_compliance": "",  # 양호/주의/경고
            "recent_issues": []
        },
        # Social
        "social": {
            "labor_relations": "",         # 양호/주의/경고
            "safety_record": "",           # 양호/주의/경고
            "recent_issues": []
        },
        # Governance
        "governance": {
            "board_independence": "",      # 상/중/하
            "ownership_concentration": "", # 집중/분산
            "related_party_risk": "",      # 상/중/하
            "recent_regulatory_risks": [], # 최근 규제 리스크 (필수)
            "recent_issues": []
        },
        "overall_esg_rating": "",          # A/B/C/D/N/A
        "_evidence_ids": [],
        "_estimation_basis": ""
    })


@dataclass
class SignalAnalysis:
    """Expert signal analysis output (Wall Street quality)"""

    signal_id: str
    signal_type: str    # DIRECT, INDUSTRY, ENVIRONMENT
    event_type: str     # 10 event types

    # 1. 영향 경로 (Impact Path) - REQUIRED with sub-paths
    impact_paths: list[dict] = field(default_factory=list)
    # [{
    #   "path": "REVENUE|COST|REGULATION|DEMAND|...",
    #   "direction": "POSITIVE|NEGATIVE|NEUTRAL",
    #   "magnitude": "HIGH|MED|LOW",
    #   "timeline": "즉시|단기(3M)|중기(1Y)|장기(3Y+)",
    #   "mechanism": "영향 메커니즘 설명",
    #   "quantitative_estimate": "정량 추정 (범위)",
    #   "_evidence_ids": []
    # }]

    # 2. 조기 경보 지표 (Early Indicators) - REQUIRED
    early_indicators: dict = field(default_factory=lambda: {
        # 정량 지표 (Quantitative)
        "quantitative_indicators": [],
        # [{
        #   "indicator": "지표명",
        #   "current_value": "현재값",
        #   "threshold": "임계값",
        #   "monitoring_frequency": "일간/주간/월간",
        #   "data_source": "데이터 소스"
        # }]

        # 정성 트리거 (Qualitative)
        "qualitative_triggers": [],
        # [{
        #   "trigger": "트리거 설명",
        #   "detection_method": "탐지 방법",
        #   "escalation_criteria": "에스컬레이션 기준"
        # }]

        "_evidence_ids": []
    })

    # 3. 실행 가능 체크리스트 (Actionable Checks) - REQUIRED
    actionable_checks: list[dict] = field(default_factory=list)
    # [{
    #   "check_id": "CHK-001",
    #   "action": "수행할 액션",
    #   "responsible_role": "담당자 역할 (RM/심사역/리스크관리자)",
    #   "deadline_type": "즉시/24시간/1주일/정기",
    #   "verification_method": "검증 방법",
    #   "escalation_path": "에스컬레이션 경로",
    #   "priority": "HIGH/MED/LOW"
    # }]

    # 4. 시나리오 분석 (Scenario Analysis)
    scenario_analysis: dict = field(default_factory=lambda: {
        "base_case": {
            "description": "",
            "probability": "",  # 상/중/하
            "impact_summary": ""
        },
        "upside_case": {
            "description": "",
            "probability": "",
            "impact_summary": ""
        },
        "downside_case": {
            "description": "",
            "probability": "",
            "impact_summary": ""
        },
        "_evidence_ids": []
    })

    # 5. 연관 시그널 (Related Signals)
    related_signals: list[dict] = field(default_factory=list)
    # [{signal_id, relationship_type, correlation_strength}]

    # 6. 영향 요약 (Impact Summary)
    impact_summary: dict = field(default_factory=lambda: {
        "overall_direction": "",      # RISK/OPPORTUNITY/NEUTRAL
        "overall_strength": "",       # HIGH/MED/LOW
        "confidence": "",             # HIGH/MED/LOW
        "primary_concern": "",        # 핵심 우려/기회 사항
        "recommended_stance": "",     # 모니터링/주의/경계/적극대응
        "_evidence_ids": []
    })


@dataclass
class QualityGateOutput:
    """Layer 4 (Quality Gate) final output schema"""

    # Metadata
    analysis_id: str
    corp_id: str
    corp_name: str
    analysis_timestamp: str
    analysis_version: str = "v2.0"

    # Layer outputs
    intake: IntakeOutput = None
    evidence_map: EvidenceMapOutput = None
    corporation_analysis: CorporationAnalysis = None
    signal_analyses: list[SignalAnalysis] = field(default_factory=list)

    # Quality metrics
    quality_metrics: dict = field(default_factory=lambda: {
        "null_free_compliance": True,
        "null_violations": [],         # List of fields that were null
        "evidence_coverage": 0.0,      # % of claims with evidence
        "counter_evidence_included": False,
        "peer_comparison_count": 0,    # Must be >= 2
        "regulatory_risk_checked": False,
        "actionable_checks_count": 0,
        "overall_quality_score": 0.0   # 0-100
    })

    # Validation results
    validation_passed: bool = False
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)

    # Final output status
    output_status: str = "DRAFT"  # DRAFT, VALIDATED, APPROVED, REJECTED


# =============================================================================
# Null-Free Policy Enforcement
# =============================================================================

class NullFreePolicy:
    """
    Null-Free Policy Enforcer

    Policy: 모든 필드는 필수이며 빈 문자열/NULL/'정보 없음' 금지
    정보 부족 시에도 추정값 + 근거 + 범위를 반드시 출력
    """

    FORBIDDEN_VALUES = [
        None, "", "null", "NULL", "N/A", "n/a", "정보 없음", "정보없음",
        "확인 필요", "확인필요", "미확인", "불명", "알 수 없음", "-", "—", "–"
    ]

    ESTIMATION_MARKERS = {
        "numeric": {
            "prefix": "추정: ",
            "range_format": "{min}~{max}",
            "confidence_suffix": " (신뢰도: {confidence})"
        },
        "categorical": {
            "levels": ["상", "중", "하"],
            "confidence_suffix": " (추정, 근거: {basis})"
        },
        "textual": {
            "prefix": "추정: ",
            "suffix": " (근거: {basis}, 신뢰도: {confidence})"
        }
    }

    @classmethod
    def is_null_or_empty(cls, value: Any) -> bool:
        """Check if value is null or forbidden empty value"""
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() in cls.FORBIDDEN_VALUES or value.strip() == ""
        if isinstance(value, (list, dict)):
            return len(value) == 0
        return False

    @classmethod
    def create_estimation(
        cls,
        field_type: str,  # "numeric", "categorical", "textual"
        field_name: str,
        basis: str,
        confidence: str = "LOW",
        min_value: Any = None,
        max_value: Any = None,
        estimated_value: Any = None
    ) -> dict:
        """
        Create an estimation object when actual data is unavailable

        Returns:
            dict with estimated_value, basis, confidence, range (if applicable)
        """
        result = {
            "is_estimated": True,
            "confidence": confidence,
            "basis": basis,
            "field_name": field_name
        }

        if field_type == "numeric":
            if min_value is not None and max_value is not None:
                result["value"] = f"{min_value}~{max_value}"
                result["min"] = min_value
                result["max"] = max_value
            elif estimated_value is not None:
                result["value"] = f"약 {estimated_value}"
            else:
                result["value"] = "범위 추정 불가 (추가 조사 필요)"

        elif field_type == "categorical":
            if estimated_value in cls.ESTIMATION_MARKERS["categorical"]["levels"]:
                result["value"] = estimated_value
            else:
                result["value"] = "중"  # Default to middle

        elif field_type == "textual":
            if estimated_value:
                result["value"] = f"추정: {estimated_value}"
            else:
                result["value"] = f"추정 불가 (근거 부족, 추가 조사 권고)"

        return result

    @classmethod
    def fill_required_field(
        cls,
        current_value: Any,
        field_type: str,
        field_name: str,
        industry_default: Any = None,
        estimation_basis: str = "업종 평균 기반 추정"
    ) -> tuple[Any, bool]:
        """
        Fill a required field with estimation if null

        Returns:
            tuple of (filled_value, was_estimated)
        """
        if not cls.is_null_or_empty(current_value):
            return current_value, False

        # Use industry default if available
        if industry_default is not None:
            estimation = cls.create_estimation(
                field_type=field_type,
                field_name=field_name,
                basis=estimation_basis,
                confidence="LOW",
                estimated_value=industry_default
            )
            return estimation, True

        # Create minimal estimation
        estimation = cls.create_estimation(
            field_type=field_type,
            field_name=field_name,
            basis="데이터 부재로 인한 최소 추정",
            confidence="LOW"
        )
        return estimation, True


# =============================================================================
# Layer Implementations
# =============================================================================

class IntakeLayer:
    """
    Layer 1: Intake

    Responsibilities:
    - Entity matching verification (corp_name, biz_no)
    - Signal date validation
    - Source credibility labeling
    """

    def __init__(self):
        self.null_policy = NullFreePolicy()

    def execute(self, context: dict) -> IntakeOutput:
        """Execute intake layer processing"""
        logger.info(f"[INTAKE] Starting for corp_id={context.get('corp_id')}")

        # 1. Entity validation
        entity_result = self._validate_entity(context)

        # 2. Date validation
        date_result = self._validate_date(context)

        # 3. Source labeling
        sources_result = self._label_sources(context)

        # Build output
        output = IntakeOutput(
            corp_id=context.get("corp_id", ""),
            corp_name=context.get("corp_name", ""),
            corp_reg_no=context.get("corp_reg_no", ""),
            biz_no=context.get("biz_no", ""),
            industry_code=context.get("industry_code", ""),
            industry_name=context.get("industry_name", ""),
            entity_match_verified=entity_result["verified"],
            entity_match_method=entity_result["method"],
            entity_discrepancies=entity_result.get("discrepancies", []),
            signal_date=date_result["date"],
            signal_date_verified=date_result["verified"],
            date_validation_method=date_result["method"],
            sources=sources_result["sources"],
            primary_source_credibility=sources_result["primary_credibility"]
        )

        # Update checklist
        output.checklist = {
            "entity_validated": entity_result["verified"],
            "date_validated": date_result["verified"],
            "sources_labeled": len(sources_result["sources"]) > 0,
            "credibility_assigned": sources_result["primary_credibility"] != ""
        }

        logger.info(f"[INTAKE] Completed. Checklist: {output.checklist}")
        return output

    def _validate_entity(self, context: dict) -> dict:
        """Validate entity matching between snapshot and external data"""
        result = {
            "verified": False,
            "method": "exact_match",
            "discrepancies": []
        }

        corp_name = context.get("corp_name", "")
        biz_no = context.get("biz_no", "")
        snapshot = context.get("snapshot_json", {})

        # Check snapshot corp info
        snapshot_corp = snapshot.get("corp", {})
        snapshot_name = snapshot_corp.get("corp_name", "")
        snapshot_biz_no = snapshot_corp.get("biz_no", "")

        # Exact match check
        if corp_name and snapshot_name:
            if corp_name == snapshot_name:
                result["verified"] = True
            else:
                # Fuzzy match check
                if self._fuzzy_match(corp_name, snapshot_name):
                    result["verified"] = True
                    result["method"] = "fuzzy_match"
                else:
                    result["discrepancies"].append({
                        "field": "corp_name",
                        "context_value": corp_name,
                        "snapshot_value": snapshot_name
                    })

        # Business number check
        if biz_no and snapshot_biz_no:
            normalized_biz = self._normalize_biz_no(biz_no)
            normalized_snapshot = self._normalize_biz_no(snapshot_biz_no)
            if normalized_biz != normalized_snapshot:
                result["discrepancies"].append({
                    "field": "biz_no",
                    "context_value": biz_no,
                    "snapshot_value": snapshot_biz_no
                })
                result["verified"] = False

        return result

    def _validate_date(self, context: dict) -> dict:
        """Validate signal date"""
        result = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "verified": False,
            "method": "estimated"
        }

        # Check external events for dates
        external_events = context.get("external_events", [])
        if external_events:
            # Find most recent event date
            dates = []
            for event in external_events:
                if event.get("event_date"):
                    dates.append(event["event_date"])
                elif event.get("published_at"):
                    dates.append(event["published_at"])

            if dates:
                result["date"] = max(dates)
                result["verified"] = True
                result["method"] = "article_date"

        return result

    def _label_sources(self, context: dict) -> dict:
        """Label source credibility"""
        result = {
            "sources": [],
            "primary_credibility": "C"
        }

        external_events = context.get("external_events", [])
        for event in external_events:
            url = event.get("source_url", "")
            credibility = self._determine_credibility(url, event)
            result["sources"].append({
                "url": url,
                "credibility": credibility.value,
                "domain": self._extract_domain(url),
                "validated": True
            })

        # Determine primary credibility (highest grade)
        grades = [s["credibility"] for s in result["sources"]]
        if "A" in grades:
            result["primary_credibility"] = "A"
        elif "B" in grades:
            result["primary_credibility"] = "B"
        else:
            result["primary_credibility"] = "C"

        return result

    def _determine_credibility(self, url: str, event: dict) -> SourceCredibility:
        """Determine source credibility grade"""
        domain = self._extract_domain(url)

        # Check grade A domains
        for a_domain in CREDIBILITY_CRITERIA[SourceCredibility.A]["domains"]:
            if a_domain in domain:
                return SourceCredibility.A

        # Check grade B domains
        for b_domain in CREDIBILITY_CRITERIA[SourceCredibility.B]["domains"]:
            if b_domain in domain:
                return SourceCredibility.B

        # Check keywords in content
        content = event.get("content", "") + event.get("title", "")
        for keyword in CREDIBILITY_CRITERIA[SourceCredibility.A]["keywords"]:
            if keyword in content:
                return SourceCredibility.A

        return SourceCredibility.C

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""

    def _normalize_biz_no(self, biz_no: str) -> str:
        """Normalize business number (remove dashes)"""
        return re.sub(r'[^0-9]', '', biz_no)

    def _fuzzy_match(self, str1: str, str2: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy matching"""
        # Normalize strings
        s1 = str1.replace(" ", "").lower()
        s2 = str2.replace(" ", "").lower()

        # Check if one contains the other
        if s1 in s2 or s2 in s1:
            return True

        # Simple character overlap ratio
        common = set(s1) & set(s2)
        if len(common) / max(len(set(s1)), len(set(s2))) >= threshold:
            return True

        return False


class EvidenceLayer:
    """
    Layer 2: Evidence Collection and Verification

    Responsibilities:
    - Collect evidence linked to claims
    - Cross-verify evidence
    - Include counter-evidence (minimum 1)
    - Remove duplicate sources
    """

    def __init__(self):
        self.null_policy = NullFreePolicy()
        self._evidence_counter = 0
        self._claim_counter = 0

    def execute(self, context: dict, intake: IntakeOutput) -> EvidenceMapOutput:
        """Execute evidence layer processing"""
        logger.info(f"[EVIDENCE] Starting for corp_id={context.get('corp_id')}")

        output = EvidenceMapOutput(corp_id=context.get("corp_id", ""))

        # 1. Extract claims from context
        claims = self._extract_claims(context)
        output.claims = claims

        # 2. Collect evidence for each claim
        evidence_entries = []
        for claim in claims:
            evidences = self._collect_evidence_for_claim(claim, context, intake)
            evidence_entries.extend(evidences)

        # 3. Remove duplicates
        unique_evidence, removed_count = self._remove_duplicates(evidence_entries)
        output.evidence_entries = unique_evidence

        # 4. Cross-verify evidence
        verified_evidence = self._cross_verify(unique_evidence)
        output.evidence_entries = verified_evidence

        # 5. Ensure counter-evidence (minimum 1)
        counter_evidence = self._find_counter_evidence(context, claims)
        if not counter_evidence:
            # Create placeholder counter-evidence
            counter_evidence = [self._create_placeholder_counter_evidence(claims)]
        output.counter_evidence = counter_evidence

        # 6. Calculate quality metrics
        output.cross_verification_summary = {
            "total_claims": len(claims),
            "verified_claims": len([e for e in verified_evidence if e.cross_verified]),
            "verification_rate": len([e for e in verified_evidence if e.cross_verified]) / max(len(claims), 1),
            "duplicate_sources_removed": removed_count
        }

        grade_counts = {"A": 0, "B": 0, "C": 0}
        for e in verified_evidence:
            grade_counts[e.credibility_grade] = grade_counts.get(e.credibility_grade, 0) + 1

        output.quality_metrics = {
            "grade_a_count": grade_counts["A"],
            "grade_b_count": grade_counts["B"],
            "grade_c_count": grade_counts["C"],
            "average_credibility_score": self._calculate_credibility_score(grade_counts)
        }

        logger.info(f"[EVIDENCE] Completed. {len(output.evidence_entries)} entries, {len(output.counter_evidence)} counter-evidence")
        return output

    def _generate_evidence_id(self) -> str:
        """Generate unique evidence ID"""
        self._evidence_counter += 1
        return f"EV-{self._evidence_counter:04d}"

    def _generate_claim_id(self) -> str:
        """Generate unique claim ID"""
        self._claim_counter += 1
        return f"CLM-{self._claim_counter:04d}"

    def _extract_claims(self, context: dict) -> list[dict]:
        """Extract claims from context data"""
        claims = []

        # Claims from snapshot changes
        snapshot = context.get("snapshot_json", {})
        if snapshot:
            # Financial claims
            credit = snapshot.get("credit", {})
            if credit.get("loan_summary", {}).get("overdue_flag"):
                claims.append({
                    "claim_id": self._generate_claim_id(),
                    "statement": "연체 발생",
                    "category": "CREDIT_RISK",
                    "source_type": "INTERNAL"
                })

        # Claims from external events
        for event in context.get("external_events", []):
            claims.append({
                "claim_id": self._generate_claim_id(),
                "statement": event.get("title", "외부 이벤트"),
                "category": "EXTERNAL_EVENT",
                "source_type": "EXTERNAL"
            })

        return claims

    def _collect_evidence_for_claim(
        self, claim: dict, context: dict, intake: IntakeOutput
    ) -> list[EvidenceEntry]:
        """Collect evidence entries for a specific claim"""
        evidences = []
        claim_id = claim["claim_id"]

        # Find matching sources from intake
        for source in intake.sources:
            if source["credibility"]:
                evidence = EvidenceEntry(
                    evidence_id=self._generate_evidence_id(),
                    claim_ids=[claim_id],
                    evidence_type="EXTERNAL",
                    ref_type="URL",
                    ref_value=source["url"],
                    snippet=claim["statement"][:200],
                    credibility_grade=source["credibility"],
                    credibility_reason=f"Domain: {source['domain']}"
                )
                evidences.append(evidence)

        # Add internal evidence if applicable
        if claim["source_type"] == "INTERNAL":
            snapshot = context.get("snapshot_json", {})
            evidence = EvidenceEntry(
                evidence_id=self._generate_evidence_id(),
                claim_ids=[claim_id],
                evidence_type="INTERNAL_FIELD",
                ref_type="SNAPSHOT_KEYPATH",
                ref_value=self._find_keypath_for_claim(claim, snapshot),
                snippet=claim["statement"][:200],
                credibility_grade="A",
                credibility_reason="내부 데이터"
            )
            evidences.append(evidence)

        return evidences

    def _find_keypath_for_claim(self, claim: dict, snapshot: dict) -> str:
        """Find JSON keypath for a claim"""
        category = claim.get("category", "")

        keypath_mapping = {
            "CREDIT_RISK": "/credit/loan_summary/overdue_flag",
            "FINANCIAL": "/financial/summary",
            "OWNERSHIP": "/corp/ownership",
            "GOVERNANCE": "/corp/governance"
        }

        return keypath_mapping.get(category, "/corp/status")

    def _remove_duplicates(self, evidences: list[EvidenceEntry]) -> tuple[list[EvidenceEntry], int]:
        """Remove duplicate evidence entries"""
        seen_refs = set()
        unique = []
        removed = 0

        for ev in evidences:
            ref_key = f"{ev.ref_type}:{ev.ref_value}"
            if ref_key not in seen_refs:
                seen_refs.add(ref_key)
                unique.append(ev)
            else:
                removed += 1

        return unique, removed

    def _cross_verify(self, evidences: list[EvidenceEntry]) -> list[EvidenceEntry]:
        """Cross-verify evidence entries"""
        # Group by claim_id
        claim_evidences = {}
        for ev in evidences:
            for claim_id in ev.claim_ids:
                if claim_id not in claim_evidences:
                    claim_evidences[claim_id] = []
                claim_evidences[claim_id].append(ev)

        # Mark as cross-verified if multiple sources
        for ev in evidences:
            for claim_id in ev.claim_ids:
                if len(claim_evidences.get(claim_id, [])) > 1:
                    ev.cross_verified = True
                    ev.cross_verification_sources = [
                        e.ref_value for e in claim_evidences[claim_id]
                        if e.evidence_id != ev.evidence_id
                    ]

        return evidences

    def _find_counter_evidence(self, context: dict, claims: list[dict]) -> list[EvidenceEntry]:
        """Find counter-evidence for claims"""
        counter_evidence = []

        # Look for positive indicators against negative claims
        snapshot = context.get("snapshot_json", {})

        # Example: If there's a risk claim, look for mitigating factors
        for claim in claims:
            if claim["category"] == "CREDIT_RISK":
                # Check for positive financial indicators
                financial = snapshot.get("financial", {})
                if financial.get("net_income", 0) > 0:
                    counter_evidence.append(EvidenceEntry(
                        evidence_id=self._generate_evidence_id(),
                        claim_ids=[claim["claim_id"]],
                        evidence_type="INTERNAL_FIELD",
                        ref_type="SNAPSHOT_KEYPATH",
                        ref_value="/financial/net_income",
                        snippet="순이익 흑자 유지",
                        credibility_grade="A",
                        credibility_reason="내부 재무데이터",
                        is_counter_evidence=True
                    ))

        return counter_evidence

    def _create_placeholder_counter_evidence(self, claims: list[dict]) -> EvidenceEntry:
        """Create placeholder counter-evidence when none found"""
        claim_ids = [c["claim_id"] for c in claims[:3]]  # Link to first 3 claims

        return EvidenceEntry(
            evidence_id=self._generate_evidence_id(),
            claim_ids=claim_ids,
            evidence_type="EXTERNAL",
            ref_type="URL",
            ref_value="추가 조사 필요",
            snippet="반대 근거 미발견 - 추가 조사를 통한 균형잡힌 분석 권고",
            credibility_grade="C",
            credibility_reason="반대 근거 부재 (추가 조사 필요)",
            is_counter_evidence=True
        )

    def _calculate_credibility_score(self, grade_counts: dict) -> float:
        """Calculate average credibility score (A=3, B=2, C=1)"""
        weights = {"A": 3, "B": 2, "C": 1}
        total = sum(grade_counts.values())
        if total == 0:
            return 0.0

        weighted_sum = sum(weights.get(g, 1) * c for g, c in grade_counts.items())
        return round(weighted_sum / total, 2)


class ExpertAnalysisLayer:
    """
    Layer 3: Expert Analysis

    Generates Wall Street quality corporation and signal analysis
    with null-free policy enforcement
    """

    def __init__(self, llm_service=None):
        self.llm = llm_service
        self.null_policy = NullFreePolicy()

    def execute(
        self,
        context: dict,
        intake: IntakeOutput,
        evidence_map: EvidenceMapOutput
    ) -> tuple[CorporationAnalysis, list[SignalAnalysis]]:
        """Execute expert analysis layer"""
        logger.info(f"[EXPERT] Starting for corp_id={context.get('corp_id')}")

        # Generate corporation analysis
        corp_analysis = self._generate_corporation_analysis(context, evidence_map)

        # Generate signal analyses
        signal_analyses = self._generate_signal_analyses(context, evidence_map)

        # Apply null-free policy
        corp_analysis = self._enforce_null_free_corp(corp_analysis, context)
        signal_analyses = [self._enforce_null_free_signal(s) for s in signal_analyses]

        logger.info(f"[EXPERT] Completed. Corp analysis + {len(signal_analyses)} signal analyses")
        return corp_analysis, signal_analyses

    def _generate_corporation_analysis(
        self, context: dict, evidence_map: EvidenceMapOutput
    ) -> CorporationAnalysis:
        """Generate comprehensive corporation analysis"""
        corp = CorporationAnalysis()
        snapshot = context.get("snapshot_json", {})
        profile = context.get("corp_profile", {})

        # Link evidence IDs
        evidence_ids = [e.evidence_id for e in evidence_map.evidence_entries]

        # 1. Business Structure
        corp.business_structure = {
            "core_business": profile.get("business_summary", ""),
            "revenue_segments": profile.get("revenue_segments", []),
            "value_chain_position": profile.get("value_chain_position", ""),
            "key_assets": profile.get("key_assets", []),
            "business_model": profile.get("business_model", ""),
            "_evidence_ids": evidence_ids[:2],
            "_estimation_basis": ""
        }

        # 2. Market Position
        corp.market_position = {
            "market_share_range": profile.get("market_share", ""),
            "market_share_confidence": "MED",
            "competitive_position": profile.get("competitive_position", ""),
            "market_size_estimate": profile.get("market_size", ""),
            "market_growth_trend": profile.get("market_growth", ""),
            "entry_barriers": profile.get("entry_barriers", []),
            "_evidence_ids": evidence_ids[:2],
            "_estimation_basis": ""
        }

        # 3. Financial Profile
        financial = snapshot.get("financial", {})
        corp.financial_profile = {
            "profitability": {
                "revenue_trend": self._determine_trend(financial.get("revenue_history", [])),
                "revenue_range_krw": self._format_revenue_range(financial),
                "margin_trend": self._determine_trend(financial.get("margin_history", [])),
                "margin_range_pct": "",
                "risk_factors": []
            },
            "stability": {
                "debt_level": self._categorize_level(financial.get("debt_ratio", 0), [50, 100, 200]),
                "debt_ratio_range": f"{financial.get('debt_ratio', 0)}%",
                "liquidity_level": self._categorize_level(financial.get("current_ratio", 0), [100, 150, 200]),
                "liquidity_trend": "",
                "risk_factors": []
            },
            "growth": {
                "revenue_growth_trend": "",
                "investment_intensity": "",
                "capex_trend": "",
                "risk_factors": []
            },
            "_evidence_ids": evidence_ids[:2],
            "_estimation_basis": ""
        }

        # 4. Risk Map
        corp.risk_map = {
            "credit_risks": [],
            "operational_risks": [],
            "market_risks": [],
            "regulatory_risks": [],
            "concentration_risks": [],
            "overall_risk_level": "중",
            "_evidence_ids": evidence_ids[:2],
            "_estimation_basis": ""
        }

        # 5. Catalysts
        corp.catalysts = {
            "positive_catalysts": [],
            "negative_catalysts": [],
            "near_term_events": [],
            "medium_term_events": [],
            "_evidence_ids": evidence_ids[:2],
            "_estimation_basis": ""
        }

        # 6. Peer Comparison (minimum 2 metrics required)
        corp.peer_comparison = {
            "peer_companies": profile.get("competitors", [])[:3],
            "comparison_metrics": [
                {"metric": "매출액", "company_value": "", "peer_avg": "", "position": ""},
                {"metric": "영업이익률", "company_value": "", "peer_avg": "", "position": ""}
            ],
            "relative_position": "",
            "competitive_advantages": profile.get("competitive_advantages", []),
            "competitive_disadvantages": [],
            "_evidence_ids": evidence_ids[:2],
            "_estimation_basis": ""
        }

        # 7. ESG & Governance
        corp.esg_governance = {
            "environmental": {
                "carbon_risk_level": "",
                "environmental_compliance": "",
                "recent_issues": []
            },
            "social": {
                "labor_relations": "",
                "safety_record": "",
                "recent_issues": []
            },
            "governance": {
                "board_independence": "",
                "ownership_concentration": "",
                "related_party_risk": "",
                "recent_regulatory_risks": [],  # Required
                "recent_issues": []
            },
            "overall_esg_rating": "",
            "_evidence_ids": evidence_ids[:2],
            "_estimation_basis": ""
        }

        return corp

    def _generate_signal_analyses(
        self, context: dict, evidence_map: EvidenceMapOutput
    ) -> list[SignalAnalysis]:
        """Generate signal analyses with impact paths and actionable checks"""
        analyses = []
        signals = context.get("signals", [])
        evidence_ids = [e.evidence_id for e in evidence_map.evidence_entries]

        for i, signal in enumerate(signals):
            analysis = SignalAnalysis(
                signal_id=signal.get("event_signature", f"SIG-{i:04d}"),
                signal_type=signal.get("signal_type", "DIRECT"),
                event_type=signal.get("event_type", "")
            )

            # Generate impact paths
            analysis.impact_paths = self._generate_impact_paths(signal, evidence_ids)

            # Generate early indicators
            analysis.early_indicators = self._generate_early_indicators(signal, evidence_ids)

            # Generate actionable checks
            analysis.actionable_checks = self._generate_actionable_checks(signal)

            # Generate scenario analysis
            analysis.scenario_analysis = self._generate_scenario_analysis(signal, evidence_ids)

            # Impact summary
            analysis.impact_summary = {
                "overall_direction": signal.get("impact_direction", "NEUTRAL"),
                "overall_strength": signal.get("impact_strength", "MED"),
                "confidence": signal.get("confidence", "MED"),
                "primary_concern": signal.get("summary", "")[:100],
                "recommended_stance": self._determine_stance(signal),
                "_evidence_ids": evidence_ids[:2]
            }

            analyses.append(analysis)

        return analyses

    def _generate_impact_paths(self, signal: dict, evidence_ids: list) -> list[dict]:
        """Generate detailed impact paths"""
        paths = []
        event_type = signal.get("event_type", "")
        direction = signal.get("impact_direction", "NEUTRAL")

        # Map event types to impact paths
        event_path_mapping = {
            "OVERDUE_FLAG_ON": [ImpactPath.FINANCING, ImpactPath.REPUTATION],
            "INTERNAL_RISK_GRADE_CHANGE": [ImpactPath.FINANCING],
            "LOAN_EXPOSURE_CHANGE": [ImpactPath.FINANCING],
            "INDUSTRY_SHOCK": [ImpactPath.DEMAND, ImpactPath.REVENUE],
            "POLICY_REGULATION_CHANGE": [ImpactPath.REGULATION, ImpactPath.COST],
            "FINANCIAL_STATEMENT_UPDATE": [ImpactPath.REVENUE, ImpactPath.COST],
        }

        impact_paths = event_path_mapping.get(event_type, [ImpactPath.OPERATIONAL])

        for path in impact_paths:
            paths.append({
                "path": path.value,
                "direction": "NEGATIVE" if direction == "RISK" else "POSITIVE" if direction == "OPPORTUNITY" else "NEUTRAL",
                "magnitude": signal.get("impact_strength", "MED"),
                "timeline": "단기(3M)",
                "mechanism": f"{path.value} 경로를 통한 영향",
                "quantitative_estimate": "정량 추정 필요",
                "_evidence_ids": evidence_ids[:1]
            })

        return paths

    def _generate_early_indicators(self, signal: dict, evidence_ids: list) -> dict:
        """Generate early warning indicators"""
        return {
            "quantitative_indicators": [
                {
                    "indicator": "연체율",
                    "current_value": "확인 필요",
                    "threshold": "1%",
                    "monitoring_frequency": "일간",
                    "data_source": "내부 여신시스템"
                },
                {
                    "indicator": "여신 집중도",
                    "current_value": "확인 필요",
                    "threshold": "30%",
                    "monitoring_frequency": "월간",
                    "data_source": "내부 여신시스템"
                }
            ],
            "qualitative_triggers": [
                {
                    "trigger": "경영진 변동",
                    "detection_method": "공시 모니터링",
                    "escalation_criteria": "CEO 교체 시"
                },
                {
                    "trigger": "대형 계약 체결/해지",
                    "detection_method": "뉴스 모니터링",
                    "escalation_criteria": "매출 10% 이상 영향 시"
                }
            ],
            "_evidence_ids": evidence_ids[:1]
        }

    def _generate_actionable_checks(self, signal: dict) -> list[dict]:
        """Generate actionable checklist for practitioners"""
        checks = []
        event_type = signal.get("event_type", "")
        direction = signal.get("impact_direction", "NEUTRAL")

        # Base checks for all signals
        base_checks = [
            {
                "check_id": "CHK-001",
                "action": "시그널 내용 확인 및 1차 검증",
                "responsible_role": "RM",
                "deadline_type": "24시간",
                "verification_method": "내부 데이터 대조",
                "escalation_path": "팀장 → 부서장",
                "priority": "HIGH"
            }
        ]

        # Event-specific checks
        if event_type == "OVERDUE_FLAG_ON":
            checks.extend([
                {
                    "check_id": "CHK-002",
                    "action": "연체 현황 및 사유 파악",
                    "responsible_role": "RM",
                    "deadline_type": "즉시",
                    "verification_method": "고객 연락 및 여신시스템 확인",
                    "escalation_path": "심사역 → 리스크관리부",
                    "priority": "HIGH"
                },
                {
                    "check_id": "CHK-003",
                    "action": "담보 현황 점검",
                    "responsible_role": "심사역",
                    "deadline_type": "24시간",
                    "verification_method": "담보평가 시스템",
                    "escalation_path": "담보관리팀",
                    "priority": "HIGH"
                }
            ])
        elif event_type == "INDUSTRY_SHOCK":
            checks.extend([
                {
                    "check_id": "CHK-002",
                    "action": "업종 내 타 여신처 영향도 점검",
                    "responsible_role": "리스크관리자",
                    "deadline_type": "1주일",
                    "verification_method": "포트폴리오 분석",
                    "escalation_path": "리스크관리부서장",
                    "priority": "MED"
                }
            ])
        elif event_type == "POLICY_REGULATION_CHANGE":
            checks.extend([
                {
                    "check_id": "CHK-002",
                    "action": "규제 영향 분석",
                    "responsible_role": "심사역",
                    "deadline_type": "1주일",
                    "verification_method": "법무팀 자문",
                    "escalation_path": "준법감시부",
                    "priority": "MED"
                }
            ])

        # Add follow-up check
        checks.append({
            "check_id": f"CHK-{len(checks)+1:03d}",
            "action": "후속 모니터링 일정 수립",
            "responsible_role": "RM",
            "deadline_type": "정기",
            "verification_method": "모니터링 시스템 등록",
            "escalation_path": "해당 없음",
            "priority": "LOW"
        })

        return base_checks + checks

    def _generate_scenario_analysis(self, signal: dict, evidence_ids: list) -> dict:
        """Generate scenario analysis"""
        direction = signal.get("impact_direction", "NEUTRAL")

        if direction == "RISK":
            return {
                "base_case": {
                    "description": "현 상황 유지, 모니터링 강화",
                    "probability": "중",
                    "impact_summary": "여신 건전성 주의 관찰 필요"
                },
                "upside_case": {
                    "description": "조기 정상화, 리스크 해소",
                    "probability": "하",
                    "impact_summary": "정상 여신으로 복귀"
                },
                "downside_case": {
                    "description": "상황 악화, 추가 조치 필요",
                    "probability": "중",
                    "impact_summary": "여신 회수 또는 구조조정 검토"
                },
                "_evidence_ids": evidence_ids[:1]
            }
        else:
            return {
                "base_case": {
                    "description": "현 상황 유지",
                    "probability": "중",
                    "impact_summary": "기존 관계 유지"
                },
                "upside_case": {
                    "description": "추가 기회 발굴",
                    "probability": "중",
                    "impact_summary": "여신 확대 또는 신규 상품 제안 기회"
                },
                "downside_case": {
                    "description": "기회 소멸",
                    "probability": "하",
                    "impact_summary": "경쟁사 이동 가능성"
                },
                "_evidence_ids": evidence_ids[:1]
            }

    def _enforce_null_free_corp(self, corp: CorporationAnalysis, context: dict) -> CorporationAnalysis:
        """Enforce null-free policy on corporation analysis"""
        industry_code = context.get("industry_code", "")

        # Industry defaults
        industry_defaults = self._get_industry_defaults(industry_code)

        # Check and fill business_structure
        if self.null_policy.is_null_or_empty(corp.business_structure.get("core_business")):
            corp.business_structure["core_business"], _ = self.null_policy.fill_required_field(
                None, "textual", "core_business",
                industry_defaults.get("core_business"),
                "업종 기반 추정"
            )
            corp.business_structure["_estimation_basis"] = "업종 기반 추정"

        # Check market_position
        if self.null_policy.is_null_or_empty(corp.market_position.get("market_share_range")):
            corp.market_position["market_share_range"] = "5-15% (업종 평균 기반 추정)"
            corp.market_position["market_share_confidence"] = "LOW"
            corp.market_position["_estimation_basis"] = "업종 평균 기반 추정"

        # Ensure peer comparison has at least 2 metrics
        if len(corp.peer_comparison.get("comparison_metrics", [])) < 2:
            corp.peer_comparison["comparison_metrics"] = [
                {"metric": "매출액", "company_value": "추정 필요", "peer_avg": "업종 평균", "position": "추정 불가"},
                {"metric": "영업이익률", "company_value": "추정 필요", "peer_avg": "업종 평균", "position": "추정 불가"}
            ]
            corp.peer_comparison["_estimation_basis"] = "최소 2개 지표 강제 포함"

        # Ensure ESG regulatory risk check
        if not corp.esg_governance.get("governance", {}).get("recent_regulatory_risks"):
            corp.esg_governance["governance"]["recent_regulatory_risks"] = [
                "확인된 최근 규제 리스크 없음 (추가 조사 권고)"
            ]

        return corp

    def _enforce_null_free_signal(self, signal: SignalAnalysis) -> SignalAnalysis:
        """Enforce null-free policy on signal analysis"""

        # Ensure at least one impact path
        if not signal.impact_paths:
            signal.impact_paths = [{
                "path": "OPERATIONAL",
                "direction": "NEUTRAL",
                "magnitude": "LOW",
                "timeline": "추정 필요",
                "mechanism": "영향 경로 분석 필요",
                "quantitative_estimate": "추정 불가",
                "_evidence_ids": []
            }]

        # Ensure early indicators
        if not signal.early_indicators.get("quantitative_indicators"):
            signal.early_indicators["quantitative_indicators"] = [{
                "indicator": "모니터링 지표 설정 필요",
                "current_value": "-",
                "threshold": "설정 필요",
                "monitoring_frequency": "미정",
                "data_source": "확인 필요"
            }]

        # Ensure actionable checks
        if not signal.actionable_checks:
            signal.actionable_checks = [{
                "check_id": "CHK-001",
                "action": "시그널 상세 분석 필요",
                "responsible_role": "RM",
                "deadline_type": "1주일",
                "verification_method": "상세 분석 후 결정",
                "escalation_path": "팀장",
                "priority": "MED"
            }]

        return signal

    def _determine_trend(self, history: list) -> str:
        """Determine trend from historical data"""
        if not history or len(history) < 2:
            return "추정 불가"

        # Simple trend detection
        if history[-1] > history[0] * 1.05:
            return "증가"
        elif history[-1] < history[0] * 0.95:
            return "감소"
        else:
            return "정체"

    def _format_revenue_range(self, financial: dict) -> str:
        """Format revenue as range"""
        revenue = financial.get("revenue", 0)
        if revenue == 0:
            return "추정 필요"

        # Format with ±10% range
        min_rev = int(revenue * 0.9)
        max_rev = int(revenue * 1.1)

        if revenue >= 1e12:
            return f"{min_rev/1e12:.1f}조~{max_rev/1e12:.1f}조"
        elif revenue >= 1e8:
            return f"{min_rev/1e8:.0f}억~{max_rev/1e8:.0f}억"
        else:
            return f"{min_rev/1e4:.0f}만~{max_rev/1e4:.0f}만"

    def _categorize_level(self, value: float, thresholds: list) -> str:
        """Categorize value into 상/중/하"""
        if value < thresholds[0]:
            return "하"
        elif value < thresholds[1]:
            return "중"
        else:
            return "상"

    def _determine_stance(self, signal: dict) -> str:
        """Determine recommended stance"""
        direction = signal.get("impact_direction", "NEUTRAL")
        strength = signal.get("impact_strength", "MED")

        if direction == "RISK":
            if strength == "HIGH":
                return "적극대응"
            elif strength == "MED":
                return "경계"
            else:
                return "주의"
        elif direction == "OPPORTUNITY":
            if strength == "HIGH":
                return "적극검토"
            else:
                return "모니터링"
        else:
            return "모니터링"

    def _get_industry_defaults(self, industry_code: str) -> dict:
        """Get industry-specific defaults for estimation"""
        defaults = {
            "C26": {
                "core_business": "전자부품 제조 및 판매",
                "market_share": "5-15%",
                "debt_ratio": "100-150%"
            },
            "C21": {
                "core_business": "의약품 제조 및 판매",
                "market_share": "3-10%",
                "debt_ratio": "50-100%"
            },
            "F41": {
                "core_business": "건축 및 토목 건설업",
                "market_share": "1-5%",
                "debt_ratio": "150-250%"
            },
            "C10": {
                "core_business": "식품 제조 및 가공",
                "market_share": "2-8%",
                "debt_ratio": "80-120%"
            },
            "D35": {
                "core_business": "전기 생산 및 공급",
                "market_share": "5-20%",
                "debt_ratio": "100-200%"
            }
        }

        return defaults.get(industry_code, {
            "core_business": "사업 내용 확인 필요",
            "market_share": "추정 불가",
            "debt_ratio": "업종 평균 참조"
        })


class QualityGateLayer:
    """
    Layer 4: Quality Gate

    Final validation and null-free enforcement
    """

    def __init__(self):
        self.null_policy = NullFreePolicy()

    def execute(
        self,
        intake: IntakeOutput,
        evidence_map: EvidenceMapOutput,
        corp_analysis: CorporationAnalysis,
        signal_analyses: list[SignalAnalysis]
    ) -> QualityGateOutput:
        """Execute quality gate validation"""
        logger.info(f"[QUALITY_GATE] Starting validation for corp_id={intake.corp_id}")

        output = QualityGateOutput(
            analysis_id=hashlib.sha256(
                f"{intake.corp_id}:{intake.intake_timestamp}".encode()
            ).hexdigest()[:16],
            corp_id=intake.corp_id,
            corp_name=intake.corp_name,
            analysis_timestamp=datetime.utcnow().isoformat(),
            intake=intake,
            evidence_map=evidence_map,
            corporation_analysis=corp_analysis,
            signal_analyses=signal_analyses
        )

        # Run validations
        errors = []
        warnings = []

        # 1. Check null-free compliance
        null_violations = self._check_null_free_compliance(corp_analysis, signal_analyses)
        if null_violations:
            errors.extend([f"NULL violation: {v}" for v in null_violations])

        # 2. Check evidence coverage
        evidence_coverage = self._calculate_evidence_coverage(evidence_map)
        if evidence_coverage < 0.5:
            warnings.append(f"Low evidence coverage: {evidence_coverage:.0%}")

        # 3. Check counter-evidence
        has_counter = len(evidence_map.counter_evidence) > 0
        if not has_counter:
            errors.append("Missing required counter-evidence")

        # 4. Check peer comparison (minimum 2 metrics)
        peer_metrics = len(corp_analysis.peer_comparison.get("comparison_metrics", []))
        if peer_metrics < 2:
            errors.append(f"Insufficient peer comparison metrics: {peer_metrics} < 2")

        # 5. Check regulatory risk assessment
        reg_risks = corp_analysis.esg_governance.get("governance", {}).get("recent_regulatory_risks", [])
        if not reg_risks:
            errors.append("Missing regulatory risk assessment")

        # 6. Check actionable checks count
        total_checks = sum(len(s.actionable_checks) for s in signal_analyses)
        if total_checks == 0 and signal_analyses:
            warnings.append("No actionable checks defined")

        # Calculate quality score
        quality_score = self._calculate_quality_score(
            null_violations, evidence_coverage, has_counter,
            peer_metrics, bool(reg_risks), total_checks
        )

        # Update output
        output.quality_metrics = {
            "null_free_compliance": len(null_violations) == 0,
            "null_violations": null_violations,
            "evidence_coverage": evidence_coverage,
            "counter_evidence_included": has_counter,
            "peer_comparison_count": peer_metrics,
            "regulatory_risk_checked": bool(reg_risks),
            "actionable_checks_count": total_checks,
            "overall_quality_score": quality_score
        }

        output.validation_passed = len(errors) == 0
        output.validation_errors = errors
        output.validation_warnings = warnings
        output.output_status = "VALIDATED" if output.validation_passed else "DRAFT"

        logger.info(
            f"[QUALITY_GATE] Completed. Status={output.output_status}, "
            f"Score={quality_score:.1f}, Errors={len(errors)}, Warnings={len(warnings)}"
        )

        return output

    def _check_null_free_compliance(
        self,
        corp: CorporationAnalysis,
        signals: list[SignalAnalysis]
    ) -> list[str]:
        """Check for null/empty values in required fields"""
        violations = []

        # Check corporation analysis required fields
        required_corp_fields = [
            ("business_structure.core_business", corp.business_structure.get("core_business")),
            ("market_position.market_share_range", corp.market_position.get("market_share_range")),
            ("financial_profile.profitability.revenue_trend",
             corp.financial_profile.get("profitability", {}).get("revenue_trend")),
            ("risk_map.overall_risk_level", corp.risk_map.get("overall_risk_level")),
            ("peer_comparison.comparison_metrics", corp.peer_comparison.get("comparison_metrics")),
            ("esg_governance.governance.recent_regulatory_risks",
             corp.esg_governance.get("governance", {}).get("recent_regulatory_risks")),
        ]

        for field_name, value in required_corp_fields:
            if self.null_policy.is_null_or_empty(value):
                violations.append(f"corp.{field_name}")

        # Check signal analysis required fields
        for i, signal in enumerate(signals):
            if not signal.impact_paths:
                violations.append(f"signal[{i}].impact_paths")
            if not signal.early_indicators.get("quantitative_indicators"):
                violations.append(f"signal[{i}].early_indicators.quantitative")
            if not signal.actionable_checks:
                violations.append(f"signal[{i}].actionable_checks")

        return violations

    def _calculate_evidence_coverage(self, evidence_map: EvidenceMapOutput) -> float:
        """Calculate evidence coverage ratio"""
        total_claims = evidence_map.cross_verification_summary.get("total_claims", 0)
        if total_claims == 0:
            return 0.0

        # Count claims with evidence
        claim_ids_with_evidence = set()
        for ev in evidence_map.evidence_entries:
            claim_ids_with_evidence.update(ev.claim_ids)

        return len(claim_ids_with_evidence) / total_claims

    def _calculate_quality_score(
        self,
        null_violations: list,
        evidence_coverage: float,
        has_counter: bool,
        peer_metrics: int,
        has_reg_check: bool,
        actionable_count: int
    ) -> float:
        """Calculate overall quality score (0-100)"""
        score = 100.0

        # Deduct for null violations (critical)
        score -= len(null_violations) * 10

        # Deduct for low evidence coverage
        if evidence_coverage < 0.8:
            score -= (0.8 - evidence_coverage) * 25

        # Deduct for missing counter-evidence
        if not has_counter:
            score -= 15

        # Deduct for insufficient peer comparison
        if peer_metrics < 2:
            score -= 10

        # Deduct for missing regulatory check
        if not has_reg_check:
            score -= 10

        # Bonus for actionable checks
        score += min(actionable_count, 5) * 2

        return max(0.0, min(100.0, score))


# =============================================================================
# Main Orchestrator
# =============================================================================

class FourLayerAnalysisPipeline:
    """
    Main orchestrator for 4-layer analysis pipeline

    Layers:
    1. Intake: Input validation and source labeling
    2. Evidence: Evidence collection and verification
    3. Expert Analysis: Corporation and signal analysis
    4. Quality Gate: Final validation
    """

    def __init__(self, llm_service=None):
        self.intake_layer = IntakeLayer()
        self.evidence_layer = EvidenceLayer()
        self.expert_layer = ExpertAnalysisLayer(llm_service)
        self.quality_gate = QualityGateLayer()

    def execute(self, context: dict) -> QualityGateOutput:
        """
        Execute full 4-layer analysis pipeline

        Args:
            context: Analysis context with corp data, snapshot, external events

        Returns:
            QualityGateOutput with validated analysis
        """
        logger.info(f"[4-LAYER] Starting pipeline for corp_id={context.get('corp_id')}")

        # Layer 1: Intake
        intake = self.intake_layer.execute(context)

        # Layer 2: Evidence
        evidence_map = self.evidence_layer.execute(context, intake)

        # Layer 3: Expert Analysis
        corp_analysis, signal_analyses = self.expert_layer.execute(
            context, intake, evidence_map
        )

        # Layer 4: Quality Gate
        output = self.quality_gate.execute(
            intake, evidence_map, corp_analysis, signal_analyses
        )

        logger.info(
            f"[4-LAYER] Pipeline completed. Status={output.output_status}, "
            f"Quality={output.quality_metrics['overall_quality_score']:.1f}"
        )

        return output

    def to_dict(self, output: QualityGateOutput) -> dict:
        """Convert output to dictionary for JSON serialization"""
        return {
            "analysis_id": output.analysis_id,
            "corp_id": output.corp_id,
            "corp_name": output.corp_name,
            "analysis_timestamp": output.analysis_timestamp,
            "analysis_version": output.analysis_version,
            "quality_metrics": output.quality_metrics,
            "validation_passed": output.validation_passed,
            "validation_errors": output.validation_errors,
            "validation_warnings": output.validation_warnings,
            "output_status": output.output_status,
            "intake": asdict(output.intake) if output.intake else None,
            "evidence_map": {
                "corp_id": output.evidence_map.corp_id,
                "claims": output.evidence_map.claims,
                "evidence_entries": [asdict(e) for e in output.evidence_map.evidence_entries],
                "counter_evidence": [asdict(e) for e in output.evidence_map.counter_evidence],
                "cross_verification_summary": output.evidence_map.cross_verification_summary,
                "quality_metrics": output.evidence_map.quality_metrics
            } if output.evidence_map else None,
            "corporation_analysis": asdict(output.corporation_analysis) if output.corporation_analysis else None,
            "signal_analyses": [asdict(s) for s in output.signal_analyses]
        }
