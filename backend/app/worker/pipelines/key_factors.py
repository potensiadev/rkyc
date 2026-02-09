"""
Key Factors Generation Pipeline
PRD: 핵심 리스크/기회 요인 생성 (AI Analysis) v1.1

탐지된 시그널 + Banking Data를 종합하여 은행 관점의 핵심 요인 자동 생성

v1.1 Changes:
- BUG-01 Fix: ZeroDivisionError 방지
- 업종별 LTV 기준 차등화
- 수출비중 연계 환헤지 기준
- 연체 일수별 자산건전성 분류
- 충당금 적립 리스크 언급
- 한국어 키워드 매칭 개선
"""

import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================
# 0. 은행 실무 기준 상수 (v1.1 추가)
# ============================================================

# 업종별 LTV 기준 (업종코드 첫 글자 기준)
INDUSTRY_LTV_THRESHOLDS = {
    "D": {"warning": 60, "danger": 75},  # 전기/가스/수도 - 안정적
    "K": {"warning": 65, "danger": 80},  # 금융/보험 - 안정적
    "C": {"warning": 70, "danger": 85},  # 제조업 - 보통
    "G": {"warning": 65, "danger": 80},  # 도소매 - 보통
    "F": {"warning": 60, "danger": 75},  # 건설업 - 보수적
    "default": {"warning": 70, "danger": 80},
}

# 수출비중별 권장 환헤지율
def get_recommended_hedge_ratio(export_ratio_pct: float) -> int:
    """수출비중에 따른 권장 환헤지율 반환"""
    if export_ratio_pct >= 70:
        return 60  # 수출 70%+ → 환헤지 60% 권장
    elif export_ratio_pct >= 50:
        return 50  # 수출 50%+ → 환헤지 50% 권장
    elif export_ratio_pct >= 30:
        return 40  # 수출 30%+ → 환헤지 40% 권장
    else:
        return 30  # 수출 30% 미만 → 환헤지 30% 권장

# 연체 일수별 자산건전성 분류 (금감원 기준)
OVERDUE_CLASSIFICATION = {
    (0, 30): ("정상", "NORMAL"),
    (31, 90): ("요주의", "PRECAUTIONARY"),
    (91, 180): ("고정", "SUBSTANDARD"),
    (181, 365): ("회수의문", "DOUBTFUL"),
    (366, 99999): ("추정손실", "ESTIMATED_LOSS"),
}

def classify_overdue(overdue_days: int) -> Tuple[str, str]:
    """연체 일수에 따른 자산건전성 분류"""
    for (min_days, max_days), (label_kr, label_en) in OVERDUE_CLASSIFICATION.items():
        if min_days <= overdue_days <= max_days:
            return label_kr, label_en
    return "정상", "NORMAL"

# 충당금 적립률 (자산건전성 분류별)
PROVISION_RATES = {
    "NORMAL": 0.01,  # 정상: 1%
    "PRECAUTIONARY": 0.02,  # 요주의: 2%
    "SUBSTANDARD": 0.20,  # 고정: 20%
    "DOUBTFUL": 0.50,  # 회수의문: 50%
    "ESTIMATED_LOSS": 1.00,  # 추정손실: 100%
}

# 한국어 불용어 (키워드 매칭 시 제외)
KOREAN_STOPWORDS = {"의", "가", "이", "은", "들", "는", "과", "도", "를", "으로", "자", "에", "와", "한", "하다", "로", "에서", "및", "등"}

# 금지 표현 → 대체 표현 매핑 (v1.1: 문맥 유지)
FORBIDDEN_EXPRESSION_REPLACEMENTS = {
    "즉시": "신속히",
    "반드시": "",
    "확실히": "높은 가능성으로",
    "100%": "매우 높은 확률로",
    "절대": "",
    "무조건": "",
}


# ============================================================
# 1. 시그널-Banking 매핑 테이블 (PRD 섹션 3.3)
# ============================================================

class BankingField(Enum):
    """Banking Data 필드 매핑"""
    LOAN_TOTAL = "loan_exposure.total_exposure_krw"
    LOAN_GRADE = "loan_exposure.risk_indicators.internal_grade"
    LOAN_OVERDUE = "loan_exposure.risk_indicators.overdue_flag"
    COLLATERAL_LTV = "collateral_detail.avg_ltv"
    COLLATERAL_VALUE = "collateral_detail.total_collateral_value"
    FX_HEDGE_RATIO = "trade_finance.fx_exposure.hedge_ratio"
    FX_NET_POSITION = "trade_finance.fx_exposure.net_position_usd"
    TRADE_EXPORT = "trade_finance.export.current_receivables_usd"
    TRADE_IMPORT = "trade_finance.import.current_payables_usd"
    DEPOSIT_BALANCE = "deposit_trend.current_balance"


@dataclass
class SignalBankingMapping:
    """시그널-Banking 매핑 정의"""
    signal_type: str
    event_type: str
    banking_fields: List[BankingField]
    analysis_perspective: str  # 분석 관점


# 시그널-Banking 매핑 테이블 (PRD 섹션 3.3)
SIGNAL_BANKING_MAPPINGS: List[SignalBankingMapping] = [
    # DIRECT 시그널
    SignalBankingMapping(
        signal_type="DIRECT",
        event_type="LOAN_EXPOSURE_CHANGE",
        banking_fields=[BankingField.LOAN_TOTAL, BankingField.LOAN_GRADE],
        analysis_perspective="여신 규모 변동이 당행 포트폴리오에 미치는 영향"
    ),
    SignalBankingMapping(
        signal_type="DIRECT",
        event_type="COLLATERAL_CHANGE",
        banking_fields=[BankingField.COLLATERAL_LTV, BankingField.COLLATERAL_VALUE],
        analysis_perspective="담보 가치 변동이 여신 안전성에 미치는 영향"
    ),
    SignalBankingMapping(
        signal_type="DIRECT",
        event_type="OVERDUE_FLAG_ON",
        banking_fields=[BankingField.LOAN_OVERDUE, BankingField.LOAN_TOTAL],
        analysis_perspective="연체 발생이 여신 회수에 미치는 영향"
    ),
    SignalBankingMapping(
        signal_type="DIRECT",
        event_type="INTERNAL_RISK_GRADE_CHANGE",
        banking_fields=[BankingField.LOAN_GRADE, BankingField.LOAN_TOTAL],
        analysis_perspective="신용등급 변동이 여신 건전성에 미치는 영향"
    ),
    SignalBankingMapping(
        signal_type="DIRECT",
        event_type="FINANCIAL_STATEMENT_UPDATE",
        banking_fields=[BankingField.LOAN_TOTAL, BankingField.COLLATERAL_LTV],
        analysis_perspective="재무제표 변동이 여신 심사에 미치는 영향"
    ),
    SignalBankingMapping(
        signal_type="DIRECT",
        event_type="OWNERSHIP_CHANGE",
        banking_fields=[BankingField.LOAN_TOTAL, BankingField.LOAN_GRADE],
        analysis_perspective="소유구조 변동이 기업 신용도에 미치는 영향"
    ),
    SignalBankingMapping(
        signal_type="DIRECT",
        event_type="GOVERNANCE_CHANGE",
        banking_fields=[BankingField.LOAN_TOTAL, BankingField.LOAN_GRADE],
        analysis_perspective="지배구조 변동이 기업 안정성에 미치는 영향"
    ),
    SignalBankingMapping(
        signal_type="DIRECT",
        event_type="KYC_REFRESH",
        banking_fields=[BankingField.LOAN_TOTAL],
        analysis_perspective="KYC 갱신에 따른 여신 재검토 필요성"
    ),

    # INDUSTRY 시그널
    SignalBankingMapping(
        signal_type="INDUSTRY",
        event_type="INDUSTRY_SHOCK",
        banking_fields=[BankingField.LOAN_TOTAL, BankingField.TRADE_EXPORT, BankingField.TRADE_IMPORT],
        analysis_perspective="산업 충격이 해당 기업을 통해 당행 여신에 미치는 영향"
    ),

    # ENVIRONMENT 시그널
    SignalBankingMapping(
        signal_type="ENVIRONMENT",
        event_type="POLICY_REGULATION_CHANGE",
        banking_fields=[BankingField.FX_HEDGE_RATIO, BankingField.FX_NET_POSITION,
                       BankingField.TRADE_EXPORT, BankingField.LOAN_TOTAL],
        analysis_perspective="정책/규제 변화가 기업 경영환경 및 당행 여신에 미치는 영향"
    ),
]


def get_mapping_for_signal(signal_type: str, event_type: str) -> Optional[SignalBankingMapping]:
    """시그널 유형에 맞는 Banking 매핑 반환"""
    for mapping in SIGNAL_BANKING_MAPPINGS:
        if mapping.signal_type == signal_type and mapping.event_type == event_type:
            return mapping
    # event_type이 정확히 매칭 안 되면 signal_type만으로 매핑
    for mapping in SIGNAL_BANKING_MAPPINGS:
        if mapping.signal_type == signal_type:
            return mapping
    return None


def get_banking_value(banking_data: Dict[str, Any], field: BankingField) -> Any:
    """Banking Data에서 특정 필드 값 추출"""
    if not banking_data:
        return None

    path = field.value.split(".")
    value = banking_data
    for key in path:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
        if value is None:
            return None
    return value


# ============================================================
# 2. Pre-processing (PRD 섹션 4.1 Step 1)
# ============================================================

@dataclass
class EnrichedSignal:
    """Banking 데이터가 연결된 시그널"""
    signal_id: str
    signal_type: str
    event_type: str
    title: str
    summary: str
    impact_direction: str  # RISK, OPPORTUNITY, NEUTRAL
    impact_strength: str   # HIGH, MED, LOW
    confidence: str
    source_urls: List[str] = field(default_factory=list)
    # Banking 연결 정보
    banking_mapping: Optional[SignalBankingMapping] = None
    banking_values: Dict[str, Any] = field(default_factory=dict)
    analysis_perspective: str = ""


def enrich_signal_with_banking(
    signal: Dict[str, Any],
    banking_data: Dict[str, Any]
) -> EnrichedSignal:
    """시그널에 Banking 데이터 연결"""
    signal_type = signal.get("signal_type", "")
    event_type = signal.get("event_type", "")

    mapping = get_mapping_for_signal(signal_type, event_type)

    banking_values = {}
    if mapping and banking_data:
        for field in mapping.banking_fields:
            value = get_banking_value(banking_data, field)
            if value is not None:
                banking_values[field.name] = value

    return EnrichedSignal(
        signal_id=signal.get("signal_id", ""),
        signal_type=signal_type,
        event_type=event_type,
        title=signal.get("title", ""),
        summary=signal.get("summary", ""),
        impact_direction=signal.get("impact_direction", "NEUTRAL"),
        impact_strength=signal.get("impact_strength", "MED"),
        confidence=signal.get("confidence", "MED"),
        source_urls=signal.get("source_urls", []),
        banking_mapping=mapping,
        banking_values=banking_values,
        analysis_perspective=mapping.analysis_perspective if mapping else ""
    )


def filter_and_prioritize_signals(
    signals: List[Dict[str, Any]],
    max_count: int = 5
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    시그널 필터링 및 우선순위 정렬

    Returns:
        (risk_signals, opportunity_signals) - 각각 최대 max_count개
    """
    # 강도 우선순위
    strength_priority = {"HIGH": 0, "MED": 1, "LOW": 2}

    risk_signals = [s for s in signals if s.get("impact_direction") == "RISK"]
    opp_signals = [s for s in signals if s.get("impact_direction") == "OPPORTUNITY"]

    # HIGH 강도 우선 정렬
    risk_signals.sort(key=lambda x: strength_priority.get(x.get("impact_strength", "MED"), 1))
    opp_signals.sort(key=lambda x: strength_priority.get(x.get("impact_strength", "MED"), 1))

    return risk_signals[:max_count], opp_signals[:max_count]


def prepare_context_for_llm(
    corp_data: Dict[str, Any],
    banking_data: Dict[str, Any],
    risk_signals: List[EnrichedSignal],
    opp_signals: List[EnrichedSignal]
) -> Dict[str, Any]:
    """LLM에 전달할 Context 조립 (v1.1: 업종별 기준 추가)"""

    # Corp 기본 정보
    corp_name = corp_data.get("corp_name", "")
    industry_name = corp_data.get("industry_name", corp_data.get("industry_code", ""))
    industry_code = corp_data.get("industry_code", "")
    export_ratio = corp_data.get("export_ratio_pct", 0) or 0

    # v1.1: 업종별 LTV 기준 결정
    industry_prefix = industry_code[0] if industry_code else ""
    ltv_thresholds = INDUSTRY_LTV_THRESHOLDS.get(
        industry_prefix, INDUSTRY_LTV_THRESHOLDS["default"]
    )

    # v1.1: 수출비중 기반 권장 환헤지율
    recommended_hedge = get_recommended_hedge_ratio(export_ratio)

    # Banking 핵심 지표 추출
    total_exposure = 0
    avg_ltv = 0
    hedge_ratio = 100

    if banking_data:
        loan = banking_data.get("loan_exposure", {})
        total_exposure = loan.get("total_exposure_krw", 0)

        collateral = banking_data.get("collateral_detail", {})
        avg_ltv = collateral.get("avg_ltv", 0)

        trade = banking_data.get("trade_finance", {})
        fx = trade.get("fx_exposure", {})
        hedge_ratio = fx.get("hedge_ratio", 100)

    # 시그널 포맷팅
    def format_signal(s: EnrichedSignal, idx: int) -> str:
        banking_info = ""
        if s.banking_values:
            parts = []
            if "LOAN_TOTAL" in s.banking_values:
                loan_val = s.banking_values['LOAN_TOTAL']
                if loan_val and loan_val > 0:
                    parts.append(f"여신: {loan_val / 1_0000_0000:.0f}억원")
            if "COLLATERAL_LTV" in s.banking_values:
                parts.append(f"LTV: {s.banking_values['COLLATERAL_LTV']}%")
            if "FX_HEDGE_RATIO" in s.banking_values:
                parts.append(f"환헤지: {s.banking_values['FX_HEDGE_RATIO']}%")
            if parts:
                banking_info = f" [관련 Banking: {', '.join(parts)}]"

        return f"{idx}. [{s.impact_strength}] {s.title}\n   - {s.summary[:150]}\n   - ID: {s.signal_id}{banking_info}"

    risk_text = "\n".join(format_signal(s, i+1) for i, s in enumerate(risk_signals)) or "(없음)"
    opp_text = "\n".join(format_signal(s, i+1) for i, s in enumerate(opp_signals)) or "(없음)"

    return {
        "corp_name": corp_name,
        "industry_name": industry_name,
        "industry_code": industry_code,
        "total_exposure_krw": total_exposure,
        "total_exposure_str": f"{total_exposure / 1_0000_0000:.0f}억원" if total_exposure else "0원",
        "avg_ltv": avg_ltv,
        "hedge_ratio": hedge_ratio,
        # v1.1: 업종별 기준 추가
        "ltv_warning": ltv_thresholds["warning"],
        "ltv_danger": ltv_thresholds["danger"],
        "recommended_hedge": recommended_hedge,
        "export_ratio": export_ratio,
        # 시그널 관련
        "risk_count": len(risk_signals),
        "opp_count": len(opp_signals),
        "risk_signals": risk_text,
        "opp_signals": opp_text,
        "risk_signals_list": risk_signals,
        "opp_signals_list": opp_signals,
    }


# ============================================================
# 3. LLM 프롬프트 (PRD 섹션 4.2)
# ============================================================

SYSTEM_PROMPT_V4 = """은행 여신 심사역으로서 시그널을 분석하세요.

규칙:
1. 각 리스크/기회에 시그널 제목을 '따옴표'로 인용
2. Banking Data 숫자를 정확히 인용 (아래 제공된 숫자만 사용)
3. "검토 권고", "가능성 있음" 등 완곡한 표현 사용
4. JSON 형식으로만 응답
5. key_risks와 key_opportunities는 각각 최대 5개

은행 실무 기준 (v1.1):
- LTV: 업종별 기준 상이 (제조업 85%, 건설업 75%, 기타 80%)
- 환헤지: 수출비중 70%+ → 헤지 60% 권장, 50%+ → 50% 권장
- 연체: 31일+ 요주의, 91일+ 고정 (충당금 적립 필요)
- 금지 표현: "즉시", "반드시", "확실히", "100%", "절대", "무조건" """


USER_PROMPT_V4 = """## 기업: {corp_name} ({industry_name})

## 당행 거래 현황
- 총 여신: {total_exposure_str}
- LTV: {avg_ltv}% (업종 기준: 경고 {ltv_warning}%, 위험 {ltv_danger}%)
- 환헤지율: {hedge_ratio}% (권고치: {recommended_hedge}%)

## 분석 대상 시그널

### RISK ({risk_count}건)
{risk_signals}

### OPPORTUNITY ({opp_count}건)
{opp_signals}

## 출력 (JSON만, 마크다운 코드블록 없이)
{{
  "key_risks": [
    {{"priority": 1, "text": "당행 관점: '시그널 제목'에 따르면, 당행 여신 X억원이 ~에 노출됨. ~검토 권고.", "source_signal_id": "uuid"}}
  ],
  "key_opportunities": [
    {{"priority": 1, "text": "당행 관점: '시그널 제목'에 따라, ~기회. ~검토 권고.", "source_signal_id": "uuid"}}
  ],
  "stance_level": "CAUTION|MONITORING|STABLE|POSITIVE",
  "stance_label": "주의 요망|모니터링 필요|안정적|긍정적"
}}"""


# ============================================================
# 4. Post-validation (PRD 섹션 4.3)
# ============================================================

def extract_numbers_from_text(text: str) -> List[str]:
    """텍스트에서 숫자 추출 (억원, 달러, % 포함, 음수 지원)"""
    # v1.1: 음수 패턴 추가 (-5.2%, -10억원 등)
    patterns = [
        r'(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*억원',
        r'(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*만원',
        r'(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*원',
        r'(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*달러',
        r'(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*%',
        r'\$\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)',
        r'(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*M',  # Million USD
    ]
    numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        numbers.extend(matches)
    return numbers


def validate_number_against_banking(
    number_str: str,
    banking_data: Dict[str, Any],
    tolerance: float = 0.1  # 10% 허용 오차
) -> bool:
    """숫자가 Banking Data에 존재하는지 검증 (v1.1: ZeroDivisionError 방지)"""
    if not banking_data:
        return True  # Banking 없으면 검증 스킵

    try:
        number = float(number_str.replace(",", ""))
    except ValueError:
        return True

    # 0은 항상 허용 (BUG-01 수정: 0원, 0% 등 유효한 값)
    if number == 0:
        return True

    # Banking Data의 모든 숫자 추출
    valid_numbers = set()

    loan = banking_data.get("loan_exposure", {})
    if loan.get("total_exposure_krw"):
        valid_numbers.add(loan["total_exposure_krw"])
        valid_numbers.add(loan["total_exposure_krw"] / 1_0000_0000)  # 억원 단위

    collateral = banking_data.get("collateral_detail", {})
    if collateral.get("avg_ltv") is not None:
        valid_numbers.add(collateral["avg_ltv"])
    if collateral.get("total_collateral_value"):
        valid_numbers.add(collateral["total_collateral_value"])
        valid_numbers.add(collateral["total_collateral_value"] / 1_0000_0000)

    trade = banking_data.get("trade_finance", {})
    fx = trade.get("fx_exposure", {})
    if fx.get("hedge_ratio") is not None:
        valid_numbers.add(fx["hedge_ratio"])
    if fx.get("net_position_usd"):
        valid_numbers.add(fx["net_position_usd"])
        valid_numbers.add(fx["net_position_usd"] / 1_000_000)  # M 단위

    export = trade.get("export", {})
    if export.get("current_receivables_usd"):
        valid_numbers.add(export["current_receivables_usd"])
        valid_numbers.add(export["current_receivables_usd"] / 1_000_000)

    imp = trade.get("import", {})
    if imp.get("current_payables_usd"):
        valid_numbers.add(imp["current_payables_usd"])
        valid_numbers.add(imp["current_payables_usd"] / 1_000_000)

    # 허용 오차 내에서 검증 (BUG-01 수정: valid_num == 0 체크 강화)
    for valid_num in valid_numbers:
        if valid_num is None or valid_num == 0:
            continue  # BUG-01: ZeroDivisionError 방지
        try:
            if abs(number - valid_num) / abs(valid_num) <= tolerance:
                return True
        except (ZeroDivisionError, TypeError):
            continue  # 안전한 예외 처리

    return False


def validate_source_signal_id(signal_id: str, signals: List[EnrichedSignal]) -> bool:
    """source_signal_id가 유효한지 검증"""
    if not signal_id:
        return False
    valid_ids = {s.signal_id for s in signals}
    return signal_id in valid_ids


def extract_korean_keywords(text: str) -> List[str]:
    """한국어 텍스트에서 의미 있는 키워드 추출 (v1.1 개선)"""
    # 조사/어미 패턴 제거
    cleaned = re.sub(r'[은는이가을를에서으로와과의도만](?=\s|$)', '', text)
    # 공백 기준 분리
    words = cleaned.split()
    # 불용어 제거 및 길이 필터링
    keywords = [w for w in words if len(w) >= 2 and w not in KOREAN_STOPWORDS]
    return keywords


def find_most_relevant_signal(
    text: str,
    signals: List[EnrichedSignal],
    min_score_threshold: int = 1
) -> Optional[str]:
    """텍스트와 가장 관련성 높은 시그널 찾기 (v1.1 개선: 한국어 키워드 매칭)"""
    if not signals:
        return None

    text_keywords = set(extract_korean_keywords(text.lower()))
    best_match = None
    best_score = 0

    for signal in signals:
        score = 0
        # 제목 키워드 매칭 (가중치 2)
        title_keywords = set(extract_korean_keywords(signal.title.lower()))
        title_matches = len(text_keywords & title_keywords)
        score += title_matches * 2

        # 요약 키워드 매칭 (가중치 1)
        summary_keywords = set(extract_korean_keywords(signal.summary.lower()))
        summary_matches = len(text_keywords & summary_keywords)
        score += summary_matches

        # 시그널 ID가 텍스트에 직접 언급되면 최고 점수
        if signal.signal_id in text:
            score += 100

        if score > best_score:
            best_score = score
            best_match = signal.signal_id

    # v1.1: 최소 점수 미달 시 None 반환 (EDGE-04 해결)
    if best_score < min_score_threshold:
        return None

    return best_match


# 금지 표현 목록 (레거시 호환)
FORBIDDEN_EXPRESSIONS = list(FORBIDDEN_EXPRESSION_REPLACEMENTS.keys())


def validate_and_fix_output(
    llm_output: Dict[str, Any],
    banking_data: Dict[str, Any],
    risk_signals: List[EnrichedSignal],
    opp_signals: List[EnrichedSignal]
) -> Dict[str, Any]:
    """LLM 출력 검증 및 보정 (PRD 섹션 4.3, v1.1 개선)"""

    validated = {
        "key_risks": [],
        "key_opportunities": [],
        "stance_level": llm_output.get("stance_level", "STABLE"),
        "stance_label": llm_output.get("stance_label", "안정적"),
        "_validation_applied": True,
        "_corrections": []
    }

    def fix_forbidden_expressions(text: str) -> Tuple[str, bool]:
        """금지 표현을 대체 표현으로 변환 (v1.1: 문맥 유지)"""
        corrected = False
        for forbidden, replacement in FORBIDDEN_EXPRESSION_REPLACEMENTS.items():
            if forbidden in text:
                # 대체어가 있으면 대체, 없으면 제거
                if replacement:
                    text = text.replace(forbidden, replacement)
                else:
                    text = text.replace(forbidden, "").replace("  ", " ")
                corrected = True
        return text.strip(), corrected

    # key_risks 검증 (최대 5개)
    for idx, risk in enumerate(llm_output.get("key_risks", [])[:5]):
        if not isinstance(risk, dict):
            continue

        text = risk.get("text", "")
        source_id = risk.get("source_signal_id", "")

        corrected_risk = {
            "priority": idx + 1,
            "text": text,
            "source_signal_id": source_id,
            "_corrected": False
        }

        # 1. 금지 표현 필터링 (v1.1: 대체 표현 사용)
        fixed_text, was_corrected = fix_forbidden_expressions(text)
        if was_corrected:
            corrected_risk["text"] = fixed_text
            corrected_risk["_corrected"] = True
            validated["_corrections"].append("금지 표현 대체됨")

        # 2. source_signal_id 검증 (v1.1: null 허용)
        if not validate_source_signal_id(source_id, risk_signals):
            new_id = find_most_relevant_signal(corrected_risk["text"], risk_signals)
            if new_id:
                corrected_risk["source_signal_id"] = new_id
                corrected_risk["_corrected"] = True
                validated["_corrections"].append(f"source_signal_id 보정")
            else:
                # v1.1: 매칭 실패 시 null 허용 (EDGE-04)
                corrected_risk["source_signal_id"] = None
                corrected_risk["_corrected"] = True

        # 3. 숫자 검증 (경고만, 자동 보정은 위험)
        numbers = extract_numbers_from_text(corrected_risk["text"])
        for num in numbers:
            if not validate_number_against_banking(num, banking_data):
                validated["_corrections"].append(f"경고: 검증 불가 숫자 '{num}'")

        validated["key_risks"].append(corrected_risk)

    # key_opportunities 검증 (최대 5개)
    for idx, opp in enumerate(llm_output.get("key_opportunities", [])[:5]):
        if not isinstance(opp, dict):
            continue

        text = opp.get("text", "")
        source_id = opp.get("source_signal_id", "")

        corrected_opp = {
            "priority": idx + 1,
            "text": text,
            "source_signal_id": source_id,
            "_corrected": False
        }

        # 1. 금지 표현 필터링
        fixed_text, was_corrected = fix_forbidden_expressions(text)
        if was_corrected:
            corrected_opp["text"] = fixed_text
            corrected_opp["_corrected"] = True

        # 2. source_signal_id 검증
        if not validate_source_signal_id(source_id, opp_signals):
            new_id = find_most_relevant_signal(corrected_opp["text"], opp_signals)
            if new_id:
                corrected_opp["source_signal_id"] = new_id
                corrected_opp["_corrected"] = True
            else:
                corrected_opp["source_signal_id"] = None
                corrected_opp["_corrected"] = True

        validated["key_opportunities"].append(corrected_opp)

    return validated


# ============================================================
# 5. Fallback 로직 (PRD 섹션 4.4)
# ============================================================

def generate_fallback_key_factors(
    risk_signals: List[EnrichedSignal],
    opp_signals: List[EnrichedSignal],
    banking_data: Dict[str, Any],
    corp_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """LLM 실패 시 Rule-based 생성 (PRD 섹션 4.4, v1.1 개선)"""

    key_risks = []
    key_opportunities = []
    industry_code = ""
    export_ratio = 0

    # Corp Data에서 업종코드, 수출비중 추출
    if corp_data:
        industry_code = corp_data.get("industry_code", "")
        export_ratio = corp_data.get("export_ratio_pct", 0) or 0

    # 업종별 LTV 기준 결정 (v1.1)
    industry_prefix = industry_code[0] if industry_code else ""
    ltv_thresholds = INDUSTRY_LTV_THRESHOLDS.get(
        industry_prefix, INDUSTRY_LTV_THRESHOLDS["default"]
    )

    # 1. Banking Data 기반 자동 리스크 감지
    if banking_data:
        loan = banking_data.get("loan_exposure", {})
        total_exposure = loan.get("total_exposure_krw", 0)
        exposure_str = f"{total_exposure / 1_0000_0000:.0f}억원" if total_exposure else ""

        # 1-1. 연체 상태 및 자산건전성 분류 (v1.1: 금감원 기준)
        risk_ind = loan.get("risk_indicators", {})
        overdue_flag = risk_ind.get("overdue_flag", False)
        overdue_days = risk_ind.get("overdue_days", 0)

        if overdue_flag or overdue_days > 0:
            classification_kr, classification_en = classify_overdue(overdue_days)
            provision_rate = PROVISION_RATES.get(classification_en, 0.01)

            if classification_en != "NORMAL":
                provision_amount = total_exposure * provision_rate if total_exposure else 0
                key_risks.append({
                    "priority": len(key_risks) + 1,
                    "text": f"당행 관점: 연체 {overdue_days}일로 자산건전성 '{classification_kr}' 분류. "
                           f"충당금 적립 필요 (적립률 {provision_rate*100:.0f}%, "
                           f"예상 {provision_amount / 1_0000_0000:.1f}억원). 즉각 조치 검토 권고.",
                    "source_signal_id": None,
                    "_auto_generated": True
                })

        # 1-2. LTV 검증 (v1.1: 업종별 차등 기준)
        collateral = banking_data.get("collateral_detail", {})
        ltv = collateral.get("avg_ltv", 0)
        if ltv >= ltv_thresholds["danger"]:
            key_risks.append({
                "priority": len(key_risks) + 1,
                "text": f"당행 관점: LTV {ltv}%로 업종({industry_prefix or '일반'}) 기준 "
                       f"{ltv_thresholds['danger']}% 초과. 담보 부족 상태. 추가 담보 확보 검토 권고.",
                "source_signal_id": None,
                "_auto_generated": True
            })
        elif ltv >= ltv_thresholds["warning"]:
            key_risks.append({
                "priority": len(key_risks) + 1,
                "text": f"당행 관점: LTV {ltv}%로 업종 기준 주의 수준({ltv_thresholds['warning']}%+). 모니터링 권고.",
                "source_signal_id": None,
                "_auto_generated": True
            })

        # 1-3. 환헤지 검증 (v1.1: 수출비중 연계)
        trade = banking_data.get("trade_finance", {})
        fx = trade.get("fx_exposure", {})
        hedge = fx.get("hedge_ratio", 100)
        recommended_hedge = get_recommended_hedge_ratio(export_ratio)

        if hedge < recommended_hedge - 20:  # 권고치 대비 20%p 이상 미달
            key_risks.append({
                "priority": len(key_risks) + 1,
                "text": f"당행 관점: 환헤지율 {hedge}%로 수출비중({export_ratio:.0f}%) 감안 "
                       f"권고치 {recommended_hedge}% 대비 크게 미달. 환리스크 관리 검토 권고.",
                "source_signal_id": None,
                "_auto_generated": True
            })
        elif hedge < recommended_hedge:
            key_risks.append({
                "priority": len(key_risks) + 1,
                "text": f"당행 관점: 환헤지율 {hedge}%로 권고치 {recommended_hedge}% 미달. 헤지 비율 상향 검토 권고.",
                "source_signal_id": None,
                "_auto_generated": True
            })

        # 1-4. Risk Alerts에서 추가
        risk_alerts = banking_data.get("risk_alerts", [])
        for alert in risk_alerts[:2]:
            if len(key_risks) >= 5:
                break
            key_risks.append({
                "priority": len(key_risks) + 1,
                "text": f"당행 시스템 감지: {alert.get('title', '')} - {alert.get('description', '')[:50]}",
                "source_signal_id": None,
                "_auto_generated": True
            })

        # 1-5. Opportunity Signals에서 추가
        opp_alerts = banking_data.get("opportunity_signals", [])
        for opp in opp_alerts[:2]:
            if len(key_opportunities) >= 5:
                break
            opp_text = opp if isinstance(opp, str) else opp.get("title", str(opp))
            key_opportunities.append({
                "priority": len(key_opportunities) + 1,
                "text": f"당행 영업기회: {opp_text}",
                "source_signal_id": None,
                "_auto_generated": True
            })

        # 1-6. 담보 여력 충분 시 기회 (v1.1)
        if ltv > 0 and ltv < ltv_thresholds["warning"] - 10:
            key_opportunities.append({
                "priority": len(key_opportunities) + 1,
                "text": f"당행 관점: LTV {ltv}%로 담보 여력 양호. 여신 한도 확대 검토 가능.",
                "source_signal_id": None,
                "_auto_generated": True
            })

    # 2. 시그널 기반 자동 생성
    for signal in risk_signals:
        if len(key_risks) >= 5:
            break

        banking_info = ""
        if signal.banking_values:
            if "LOAN_TOTAL" in signal.banking_values:
                banking_info = f" 당행 여신 {signal.banking_values['LOAN_TOTAL'] / 1_0000_0000:.0f}억원 관련."

        key_risks.append({
            "priority": len(key_risks) + 1,
            "text": f"당행 관점: '{signal.title}' 시그널 감지됨.{banking_info} 상세 검토 권고.",
            "source_signal_id": signal.signal_id,
            "_auto_generated": True
        })

    for signal in opp_signals:
        if len(key_opportunities) >= 5:
            break

        key_opportunities.append({
            "priority": len(key_opportunities) + 1,
            "text": f"당행 관점: '{signal.title}' 시그널에 따른 영업 기회. 검토 권고.",
            "source_signal_id": signal.signal_id,
            "_auto_generated": True
        })

    # 3. Stance 결정 (v1.1: 연체/충당금 반영)
    high_risk_count = sum(1 for s in risk_signals if s.impact_strength == "HIGH")

    # 연체 발생 시 무조건 CAUTION
    has_overdue = False
    if banking_data:
        risk_ind = banking_data.get("loan_exposure", {}).get("risk_indicators", {})
        has_overdue = risk_ind.get("overdue_flag", False) or risk_ind.get("overdue_days", 0) > 0

    if has_overdue or high_risk_count > 0 or len(key_risks) > len(key_opportunities) * 2:
        stance_level = "CAUTION"
        stance_label = "주의 요망"
    elif len(key_risks) > len(key_opportunities):
        stance_level = "MONITORING"
        stance_label = "모니터링 필요"
    elif len(key_opportunities) > len(key_risks):
        stance_level = "POSITIVE"
        stance_label = "긍정적"
    else:
        stance_level = "STABLE"
        stance_label = "안정적"

    return {
        "key_risks": key_risks[:5],  # v1.1: 명시적 최대 5개 제한
        "key_opportunities": key_opportunities[:5],  # v1.1: 명시적 최대 5개 제한
        "stance_level": stance_level,
        "stance_label": stance_label,
        "_is_fallback": True
    }


# ============================================================
# 6. Main Pipeline
# ============================================================

class KeyFactorsGenerator:
    """핵심 리스크/기회 요인 생성기"""

    def __init__(self, llm_service=None):
        self.llm = llm_service

    def generate(
        self,
        signals: List[Dict[str, Any]],
        corp_data: Dict[str, Any],
        banking_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        핵심 리스크/기회 요인 생성

        Args:
            signals: 탐지된 시그널 목록
            corp_data: 기업 정보 (corp 테이블)
            banking_data: Banking Data (rkyc_banking_data)

        Returns:
            {
                "key_risks": [...],
                "key_opportunities": [...],
                "stance_level": "...",
                "stance_label": "..."
            }
        """
        logger.info(f"KeyFactorsGenerator starting: {len(signals)} signals")

        # Step 1: Pre-processing
        risk_signals_raw, opp_signals_raw = filter_and_prioritize_signals(signals, max_count=5)

        risk_signals = [enrich_signal_with_banking(s, banking_data) for s in risk_signals_raw]
        opp_signals = [enrich_signal_with_banking(s, banking_data) for s in opp_signals_raw]

        logger.info(f"Pre-processing done: {len(risk_signals)} risks, {len(opp_signals)} opportunities")

        # 시그널도 Banking도 없으면 기본 응답
        if not risk_signals and not opp_signals and not banking_data:
            logger.info("No signals and no banking data - returning minimal response")
            return {
                "key_risks": [],
                "key_opportunities": [],
                "stance_level": "STABLE",
                "stance_label": "안정적",
                "_no_data": True
            }

        # Step 2: LLM 호출 시도
        if self.llm and (risk_signals or opp_signals):
            try:
                context = prepare_context_for_llm(corp_data, banking_data, risk_signals, opp_signals)

                user_prompt = USER_PROMPT_V4.format(**context)

                llm_response = self.llm.call_with_json_response(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_V4},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1
                )

                # Step 3: Post-validation
                validated = validate_and_fix_output(
                    llm_response, banking_data, risk_signals, opp_signals
                )

                logger.info(f"LLM generation successful: {len(validated['key_risks'])} risks, {len(validated['key_opportunities'])} opps")
                return validated

            except Exception as e:
                logger.warning(f"LLM generation failed, using fallback: {e}")

        # Fallback (v1.1: corp_data 전달)
        fallback_result = generate_fallback_key_factors(
            risk_signals, opp_signals, banking_data, corp_data
        )
        logger.info(f"Fallback generation: {len(fallback_result['key_risks'])} risks, {len(fallback_result['key_opportunities'])} opps")
        return fallback_result
