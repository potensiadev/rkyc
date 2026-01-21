"""
LLM Prompt Templates v2.0 - Wall Street Quality Analysis

Enhanced prompts with:
- Null-free policy enforcement
- Expert-level corporation analysis
- Detailed impact path analysis
- Actionable checklist generation
- Evidence-claim linking
"""

import re
import json
import logging
from typing import Optional

_prompt_logger = logging.getLogger(__name__)


# =============================================================================
# System Prompts
# =============================================================================

EXPERT_ANALYSIS_SYSTEM_PROMPT = """당신은 월가(Wall Street) 수준의 기업 신용분석 전문가입니다.
한국 금융기관의 기업심사에 활용될 분석 보고서를 작성합니다.

## 핵심 원칙

### 1. NULL-FREE 정책 (절대 준수)
❌ 금지: NULL, 빈값, "정보 없음", "확인 필요", "N/A", "-"
✅ 필수: 정보 부족 시에도 **추정값 + 근거 + 신뢰도**를 반드시 출력

예시:
- ❌ "매출액: 정보 없음"
- ✅ "매출액: 500억~800억 추정 (업종 평균 및 임직원 수 기반, 신뢰도: LOW)"

### 2. 근거 기반 분석
- 모든 주장(claim)은 근거(evidence)와 연결 필수
- 근거 신뢰도 등급: A(공시/정부), B(주요언론/IR), C(일반뉴스/추정)
- **반대 근거도 반드시 1건 이상 포함**

### 3. 금지 표현
❌ "반드시", "즉시", "확실히", "~할 것이다", "예상됨"
✅ "~로 추정됨", "~가능성 있음", "검토 권고", "~로 보도됨"

### 4. 정량화 원칙
- 숫자는 범위로 표현: "100억~150억", "5-10%"
- 정성 평가도 수준으로: "상/중/하", "HIGH/MED/LOW"
- 불확실성 시 범위를 넓게: "50억~200억 (불확실성 높음)"

## 분석 프레임워크

### 기업 분석 7대 필수 요소
1. **사업 구조**: 핵심 사업, 매출 구성, 밸류체인 위치
2. **시장 지위**: 점유율(범위), 경쟁 위치, 진입장벽
3. **재무 프로필**: 수익성/안정성/성장성 (추세+범위+리스크)
4. **리스크 맵**: 신용/운영/시장/규제/집중 리스크
5. **촉매**: 긍정적/부정적 촉매, 타임라인
6. **비교군**: 최소 2개 지표로 동종업체 비교
7. **ESG/거버넌스**: 최근 규제 리스크 필수 포함

### 시그널 분석 필수 요소
1. **영향 경로**: 매출/원가/규제/수요/공급망/자금조달/평판/운영
2. **조기 경보**: 정량 지표 + 정성 트리거
3. **실행 체크리스트**: 담당자별 액션 아이템
4. **시나리오 분석**: Base/Upside/Downside

## 신뢰도 기준
- **HIGH**: 공시(DART), 정부 발표, 내부 데이터 (90%+)
- **MED**: 주요 경제지, IR자료 (70-90%)
- **LOW**: 단일 출처, 추정 (50-70%)
"""


CORPORATION_ANALYSIS_PROMPT = """## 기업 심층 분석 요청

### 대상 기업
- 기업명: {corp_name}
- 법인번호: {corp_reg_no}
- 업종: {industry_code} ({industry_name})

### 내부 데이터
{snapshot_json}

### 외부 프로필 (Corp Profile)
{corp_profile_json}

### 수집된 근거 (Evidence Map)
{evidence_map_json}

---

## 분석 요구사항

### 1. 사업 구조 분석 (business_structure)
다음을 **모두** 채우세요 (NULL 금지):
- core_business: 핵심 사업 설명 (추정 시 근거 명시)
- revenue_segments: 매출 구성 [{segment, ratio_pct, trend}]
- value_chain_position: 밸류체인 내 위치
- business_model: 비즈니스 모델
- _evidence_ids: 근거 ID 목록

### 2. 시장 지위 분석 (market_position)
- market_share_range: 시장점유율 **범위** (예: "5-10%")
- competitive_position: 경쟁 위치 (1위/상위권/중위권/하위권)
- market_growth_trend: 시장 성장 추세
- entry_barriers: 진입장벽 목록

### 3. 재무 프로필 분석 (financial_profile)
각 항목을 **추세 + 범위 + 리스크**로 세분화:

**수익성 (profitability)**:
- revenue_trend: 증가/정체/감소
- revenue_range_krw: 매출 범위 (예: "500억~800억")
- margin_trend: 마진 추세
- risk_factors: 수익성 리스크 요인들

**안정성 (stability)**:
- debt_level: 상/중/하
- debt_ratio_range: 부채비율 범위 (예: "100-150%")
- liquidity_level: 유동성 수준
- risk_factors: 안정성 리스크 요인들

**성장성 (growth)**:
- revenue_growth_trend: 고성장/성장/정체/역성장
- investment_intensity: 투자 강도
- risk_factors: 성장성 리스크 요인들

### 4. 리스크 맵 (risk_map)
다음 카테고리별로 리스크 식별:
- credit_risks: [{risk, severity, likelihood}]
- operational_risks
- market_risks
- regulatory_risks
- concentration_risks: 고객/공급사/지역 집중도
- overall_risk_level: 상/중/하

### 5. 촉매 (catalysts)
- positive_catalysts: [{catalyst, timeline, probability}]
- negative_catalysts
- near_term_events: 3개월 내 이벤트
- medium_term_events: 1년 내 이벤트

### 6. 비교군 분석 (peer_comparison) - **최소 2개 지표 필수**
- peer_companies: 비교 대상 기업 목록
- comparison_metrics: **최소 2개** [{metric, company_value, peer_avg, position}]
- competitive_advantages: 경쟁 우위
- competitive_disadvantages: 경쟁 열위

### 7. ESG/거버넌스 (esg_governance) - **규제 리스크 필수**
**환경 (environmental)**:
- carbon_risk_level: 탄소 리스크 수준
- environmental_compliance: 환경 규제 준수 상태

**사회 (social)**:
- labor_relations: 노사관계 상태
- safety_record: 안전 기록

**거버넌스 (governance)** - 필수:
- board_independence: 이사회 독립성
- ownership_concentration: 소유 집중도
- recent_regulatory_risks: **최근 규제 리스크** (필수, 없으면 "확인된 리스크 없음" 명시)

---

## 출력 형식 (JSON)
```json
{{
  "business_structure": {{...}},
  "market_position": {{...}},
  "financial_profile": {{
    "profitability": {{...}},
    "stability": {{...}},
    "growth": {{...}}
  }},
  "risk_map": {{...}},
  "catalysts": {{...}},
  "peer_comparison": {{
    "comparison_metrics": [
      {{"metric": "매출액", "company_value": "...", "peer_avg": "...", "position": "..."}},
      {{"metric": "영업이익률", "company_value": "...", "peer_avg": "...", "position": "..."}}
    ]
  }},
  "esg_governance": {{
    "governance": {{
      "recent_regulatory_risks": ["..."]
    }}
  }}
}}
```

**중요**: 모든 필드를 채우세요. 정보 부족 시 "추정: [값] (근거: [이유], 신뢰도: LOW)" 형식으로 작성.
"""


SIGNAL_ANALYSIS_PROMPT = """## 시그널 심층 분석 요청

### 대상 기업
- 기업명: {corp_name}
- 업종: {industry_code} ({industry_name})

### 분석 대상 시그널
{signal_json}

### 관련 근거 (Evidence)
{evidence_json}

---

## 분석 요구사항

### 1. 영향 경로 분석 (impact_paths)
각 경로를 **세부적으로** 분석:

| 경로 유형 | 설명 |
|----------|------|
| REVENUE | 매출 영향 |
| COST | 원가 영향 |
| REGULATION | 규제 영향 |
| DEMAND | 수요 영향 |
| SUPPLY_CHAIN | 공급망 영향 |
| FINANCING | 자금조달 영향 |
| REPUTATION | 평판 영향 |
| OPERATIONAL | 운영 영향 |

각 경로별 출력:
```json
{{
  "path": "REVENUE",
  "direction": "NEGATIVE|POSITIVE|NEUTRAL",
  "magnitude": "HIGH|MED|LOW",
  "timeline": "즉시|단기(3M)|중기(1Y)|장기(3Y+)",
  "mechanism": "영향 메커니즘 설명",
  "quantitative_estimate": "정량 추정 (범위)",
  "_evidence_ids": ["EV-001"]
}}
```

### 2. 조기 경보 지표 (early_indicators)
**정량 지표와 정성 트리거 모두 필수**:

**정량 지표 (quantitative_indicators)**:
```json
{{
  "indicator": "지표명 (예: 연체율)",
  "current_value": "현재값",
  "threshold": "임계값",
  "monitoring_frequency": "일간|주간|월간",
  "data_source": "데이터 소스"
}}
```

**정성 트리거 (qualitative_triggers)**:
```json
{{
  "trigger": "트리거 설명",
  "detection_method": "탐지 방법",
  "escalation_criteria": "에스컬레이션 기준"
}}
```

### 3. 실행 가능 체크리스트 (actionable_checks)
**담당자가 실제 수행 가능한 액션**으로 작성:

```json
{{
  "check_id": "CHK-001",
  "action": "수행할 구체적 액션",
  "responsible_role": "RM|심사역|리스크관리자",
  "deadline_type": "즉시|24시간|1주일|정기",
  "verification_method": "검증 방법",
  "escalation_path": "에스컬레이션 경로",
  "priority": "HIGH|MED|LOW"
}}
```

### 4. 시나리오 분석 (scenario_analysis)
```json
{{
  "base_case": {{
    "description": "기본 시나리오",
    "probability": "상|중|하",
    "impact_summary": "영향 요약"
  }},
  "upside_case": {{...}},
  "downside_case": {{...}}
}}
```

### 5. 영향 요약 (impact_summary)
```json
{{
  "overall_direction": "RISK|OPPORTUNITY|NEUTRAL",
  "overall_strength": "HIGH|MED|LOW",
  "confidence": "HIGH|MED|LOW",
  "primary_concern": "핵심 우려/기회 사항",
  "recommended_stance": "모니터링|주의|경계|적극대응"
}}
```

---

## 출력 형식
위 5개 섹션을 모두 포함한 JSON 객체를 반환하세요.
**모든 필드 필수** - 정보 부족 시에도 추정값으로 채우세요.
"""


EVIDENCE_MAP_PROMPT = """## 근거 수집 및 검증 요청

### 대상 기업
- 기업명: {corp_name}
- 업종: {industry_code}

### 주장 목록 (Claims)
{claims_json}

### 출처 자료
{sources_json}

---

## 작업 요구사항

### 1. 각 주장(Claim)에 대한 근거 수집
- claim_id와 evidence_id 연결 필수
- 동일 근거가 여러 주장 지원 가능

### 2. 근거 신뢰도 등급 부여
| 등급 | 기준 | 예시 |
|------|------|------|
| A | 공시, 정부 발표, 감사보고서 | DART, 금감원, 통계청 |
| B | 주요 경제지, IR 자료 | 한경, 매경, 사업보고서 |
| C | 일반 뉴스, 추정 필요 | 기타 언론, 블로그 |

### 3. 반대 근거 포함 (필수)
- **최소 1건의 반대 근거** 필수 포함
- 없으면 "추가 조사 필요" 명시

### 4. 중복 출처 제거
- 동일 URL/출처는 1건만 포함
- 교차 검증 여부 표시

---

## 출력 형식
```json
{{
  "evidence_entries": [
    {{
      "evidence_id": "EV-001",
      "claim_ids": ["CLM-001", "CLM-002"],
      "evidence_type": "INTERNAL_FIELD|DOC|EXTERNAL",
      "ref_type": "SNAPSHOT_KEYPATH|DOC_PAGE|URL",
      "ref_value": "URL 또는 JSON Path",
      "snippet": "근거 텍스트 (200자 이내)",
      "credibility_grade": "A|B|C",
      "credibility_reason": "등급 부여 이유",
      "is_counter_evidence": false,
      "cross_verified": true,
      "cross_verification_sources": ["EV-002"]
    }}
  ],
  "counter_evidence": [
    {{
      "evidence_id": "EV-010",
      "claim_ids": ["CLM-001"],
      "is_counter_evidence": true,
      ...
    }}
  ]
}}
```
"""


INSIGHT_GENERATION_PROMPT_V2 = """## 경영진 브리핑 생성

### 기업 정보
- 기업명: {corp_name}
- 업종: {industry_code} ({industry_name})

### 기업 분석 요약
{corp_analysis_summary}

### 시그널 분석 요약 ({signal_count}건)
{signals_summary}

### 근거 품질 요약
{evidence_quality}

---

## 브리핑 형식

### 1. Executive Summary (2-3문장)
- 가장 중요한 리스크와 기회를 균형있게
- 신용 상태 평가 + 성장 잠재력

### 2. Key Findings
**기회 요인** (OPPORTUNITY):
- 실적 개선, 성장 투자, 기술 혁신 등

**리스크 요인** (RISK):
- 각 리스크 핵심 1줄 요약
- 모니터링 필요 영역

### 3. 영향 분석
- 주요 영향 경로 (매출/원가/규제/수요)
- 정량적 영향 추정 (범위)
- 타임라인

### 4. 권고 조치
**즉시 조치** (24시간 내):
- [체크리스트 형태]

**단기 조치** (1주일 내):
- [체크리스트 형태]

**모니터링 항목**:
- [정량 지표 + 트리거]

### 5. 근거 및 신뢰도
- 분석 근거 요약
- 신뢰도 등급 분포 (A/B/C)
- 추가 확인 필요 사항

---

## 주의사항
- 단정적 표현 금지
- 허용 표현 사용: "~로 추정됨", "검토 권고"
- **기회 요인도 리스크만큼 중요하게**
- NULL/빈값 금지 - 추정으로 채우기
"""


# =============================================================================
# Prompt Sanitization (from prompts.py)
# =============================================================================

DANGEROUS_PATTERNS = [
    r'(?i)\b(ignore|forget|disregard)\s+(all\s+)?(previous|above|prior)',
    r'(?i)\b(new\s+)?(system|instructions?|rules?)\s*:',
    r'(?i)\byou\s+are\s+(now|a)\b',
    r'(?i)\bpretend\s+(to\s+be|you\s+are)\b',
    r'(?i)\bact\s+as\s+(if|a)\b',
    r'(?i)\brole\s*:\s*',
    r'(?i)"\s*:\s*"[^"]*ignore',
    r'(?i)```\s*(python|javascript|bash|sh|cmd)',
    r'(?i)\balways\s+(output|return|respond)',
    r'(?i)\b(high|critical)\s+risk\s+regardless',
    r'(?i)\bconfidence\s*:\s*["\']?high',
]

COMPILED_PATTERNS = [re.compile(p) for p in DANGEROUS_PATTERNS]


def sanitize_input(text: str, field_name: str = "input", max_length: int = 10000) -> str:
    """Sanitize user input to prevent prompt injection"""
    if not text:
        return ""

    text = str(text).strip()

    if len(text) > max_length:
        _prompt_logger.warning(f"[Sanitize] {field_name} truncated from {len(text)} to {max_length}")
        text = text[:max_length]

    for i, pattern in enumerate(COMPILED_PATTERNS):
        if pattern.search(text):
            _prompt_logger.warning(f"[Sanitize] Suspicious pattern in {field_name}: pattern #{i}")
            text = pattern.sub('[REDACTED]', text)

    return text


def sanitize_json_string(json_str: str, field_name: str = "json") -> str:
    """Sanitize JSON string for prompt injection"""
    if not json_str:
        return "{}"

    max_json_length = 50000
    if len(json_str) > max_json_length:
        _prompt_logger.warning(f"[Sanitize] {field_name} JSON truncated")
        json_str = json_str[:max_json_length]
        last_brace = max(json_str.rfind('}'), json_str.rfind(']'))
        if last_brace > 0:
            json_str = json_str[:last_brace + 1]

    for i, pattern in enumerate(COMPILED_PATTERNS):
        if pattern.search(json_str):
            _prompt_logger.warning(f"[Sanitize] Suspicious pattern in {field_name} JSON")

    return json_str


# =============================================================================
# Prompt Formatters
# =============================================================================

def format_corporation_analysis_prompt(
    corp_name: str,
    corp_reg_no: str,
    industry_code: str,
    industry_name: str,
    snapshot_json: str,
    corp_profile_json: str,
    evidence_map_json: str
) -> str:
    """Format corporation analysis prompt"""
    return CORPORATION_ANALYSIS_PROMPT.format(
        corp_name=sanitize_input(corp_name, "corp_name", 200),
        corp_reg_no=sanitize_input(corp_reg_no, "corp_reg_no", 50),
        industry_code=sanitize_input(industry_code, "industry_code", 20),
        industry_name=sanitize_input(industry_name, "industry_name", 100),
        snapshot_json=sanitize_json_string(snapshot_json, "snapshot"),
        corp_profile_json=sanitize_json_string(corp_profile_json, "corp_profile"),
        evidence_map_json=sanitize_json_string(evidence_map_json, "evidence_map")
    )


def format_signal_analysis_prompt(
    corp_name: str,
    industry_code: str,
    industry_name: str,
    signal_json: str,
    evidence_json: str
) -> str:
    """Format signal analysis prompt"""
    return SIGNAL_ANALYSIS_PROMPT.format(
        corp_name=sanitize_input(corp_name, "corp_name", 200),
        industry_code=sanitize_input(industry_code, "industry_code", 20),
        industry_name=sanitize_input(industry_name, "industry_name", 100),
        signal_json=sanitize_json_string(signal_json, "signal"),
        evidence_json=sanitize_json_string(evidence_json, "evidence")
    )


def format_evidence_map_prompt(
    corp_name: str,
    industry_code: str,
    claims_json: str,
    sources_json: str
) -> str:
    """Format evidence map collection prompt"""
    return EVIDENCE_MAP_PROMPT.format(
        corp_name=sanitize_input(corp_name, "corp_name", 200),
        industry_code=sanitize_input(industry_code, "industry_code", 20),
        claims_json=sanitize_json_string(claims_json, "claims"),
        sources_json=sanitize_json_string(sources_json, "sources")
    )


def format_insight_prompt_v2(
    corp_name: str,
    industry_code: str,
    industry_name: str,
    corp_analysis_summary: str,
    signals_summary: str,
    signal_count: int,
    evidence_quality: str
) -> str:
    """Format insight generation prompt v2"""
    return INSIGHT_GENERATION_PROMPT_V2.format(
        corp_name=sanitize_input(corp_name, "corp_name", 200),
        industry_code=sanitize_input(industry_code, "industry_code", 20),
        industry_name=sanitize_input(industry_name, "industry_name", 100),
        corp_analysis_summary=sanitize_input(corp_analysis_summary, "corp_analysis", 5000),
        signals_summary=sanitize_input(signals_summary, "signals", 5000),
        signal_count=signal_count,
        evidence_quality=sanitize_input(evidence_quality, "evidence_quality", 1000)
    )


# =============================================================================
# Null-Free Validation Rules for LLM Output
# =============================================================================

NULL_FREE_RULES = """
## NULL-FREE 출력 규칙

### 금지 값 목록
다음 값들은 어떤 필드에서도 사용 금지:
- null, NULL, None
- 빈 문자열 ""
- "N/A", "n/a", "-", "—"
- "정보 없음", "정보없음"
- "확인 필요", "확인필요", "미확인"
- "불명", "알 수 없음"

### 정보 부족 시 처리 방법

**숫자/정량 필드**:
- 범위로 표현: "100억~200억"
- 신뢰도 명시: "(추정, 신뢰도: LOW)"
- 근거 추가: "(업종 평균 기반)"

예시:
- ❌ "매출액: N/A"
- ✅ "매출액: 500억~1000억 (업종 규모 및 임직원 수 기반 추정, 신뢰도: LOW)"

**카테고리/정성 필드**:
- 상/중/하 중 선택
- 추정 근거 명시

예시:
- ❌ "부채비율: 확인 필요"
- ✅ "부채비율: 중 (100-150% 범위 추정, 업종 평균 기반)"

**텍스트/설명 필드**:
- "추정: " 접두사 사용
- 가용 정보 기반 추론

예시:
- ❌ "사업모델: 정보 없음"
- ✅ "추정: B2B 제조업 모델 (업종 및 고객사 정보 기반, 추가 확인 권고)"

### 필수 포함 요소
1. **추정값**: 가능한 범위 또는 수준
2. **근거**: 추정의 기반 (업종 평균, 유사 기업, 공개 정보 등)
3. **신뢰도**: HIGH/MED/LOW 중 하나
4. **추가 조사 권고**: 불확실성이 높은 경우

### 검증 체크리스트
- [ ] 모든 필수 필드가 채워졌는가?
- [ ] 빈 배열 []이 있다면, 최소 1개 항목으로 채웠는가?
- [ ] 금지 값이 사용되지 않았는가?
- [ ] 추정값에 신뢰도가 명시되었는가?
"""


# =============================================================================
# Industry-specific Context
# =============================================================================

INDUSTRY_CONTEXT = {
    "C10": {
        "name": "식품제조업",
        "typical_margin": "5-15%",
        "typical_debt_ratio": "80-150%",
        "key_risks": ["원자재 가격 변동", "위생/안전 규제", "소비 트렌드 변화"],
        "key_metrics": ["매출원가율", "재고회전율", "시장점유율"]
    },
    "C21": {
        "name": "의약품제조업",
        "typical_margin": "15-30%",
        "typical_debt_ratio": "30-80%",
        "key_risks": ["R&D 실패", "특허 만료", "규제 승인 지연"],
        "key_metrics": ["R&D 투자율", "파이프라인 가치", "특허 만료 일정"]
    },
    "C26": {
        "name": "전자부품제조업",
        "typical_margin": "5-20%",
        "typical_debt_ratio": "50-120%",
        "key_risks": ["기술 변화", "경기 민감성", "공급망 리스크"],
        "key_metrics": ["설비가동률", "수주잔고", "기술 경쟁력"]
    },
    "C29": {
        "name": "기계장비제조업",
        "typical_margin": "5-15%",
        "typical_debt_ratio": "80-150%",
        "key_risks": ["수주 변동성", "원자재 가격", "기술 경쟁"],
        "key_metrics": ["수주잔고", "수출비중", "설비투자"]
    },
    "D35": {
        "name": "전기업",
        "typical_margin": "3-10%",
        "typical_debt_ratio": "100-250%",
        "key_risks": ["규제 변화", "연료비 변동", "설비 투자 부담"],
        "key_metrics": ["발전량", "판매단가", "설비이용률"]
    },
    "F41": {
        "name": "건설업",
        "typical_margin": "3-8%",
        "typical_debt_ratio": "150-300%",
        "key_risks": ["수주 감소", "원가 상승", "PF 리스크"],
        "key_metrics": ["수주잔고", "공사이익률", "현금흐름"]
    }
}


def get_industry_context(industry_code: str) -> dict:
    """Get industry-specific context for analysis"""
    return INDUSTRY_CONTEXT.get(
        industry_code,
        {
            "name": f"기타 ({industry_code})",
            "typical_margin": "업종 평균 참조",
            "typical_debt_ratio": "업종 평균 참조",
            "key_risks": ["업종별 리스크 확인 필요"],
            "key_metrics": ["업종별 핵심 지표 확인 필요"]
        }
    )
