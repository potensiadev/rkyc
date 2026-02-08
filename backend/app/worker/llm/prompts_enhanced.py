"""
LLM Prompt Templates - Enhanced Edition (Sprint 1)

Sprint 1 Implementation:
- 37 Few-Shot Examples (16 DIRECT + 10 INDUSTRY + 11 ENVIRONMENT)
- Strict JSON Schema with Required Fields
- 50+ Expanded Forbidden Expression Patterns
- Closed-World Assumption (CWA)
- Chain-of-Verification (CoV)

Author: Silicon Valley Senior PM
Version: 1.0.0
Date: 2026-02-08
"""

import re
import json
import logging
from typing import Optional, Tuple
from enum import Enum

_logger = logging.getLogger(__name__)


# =============================================================================
# EXPANDED FORBIDDEN PATTERNS (50+)
# =============================================================================

class ForbiddenCategory(str, Enum):
    CERTAINTY = "단정적 표현"
    PREDICTION = "예측/전망"
    ESTIMATION = "추정"
    UNCERTAINTY = "불확실성"
    URGENCY = "즉시성"
    EXAGGERATION = "과장"


# Category 1: 단정적 표현 (Certainty Expressions)
CERTAINTY_PATTERNS = [
    "반드시", "무조건", "확실히", "틀림없이", "분명히",
    "당연히", "필연적으로", "절대적으로", "명백히", "확정적으로",
]

# Category 2: 예측/전망 표현 (Prediction Expressions)
PREDICTION_PATTERNS = [
    "예상됨", "예상된다", "예상할 수 있다",
    "전망됨", "전망된다", "전망이다",
    "예측됨", "예측된다", "예측할 수 있다",
    "~할 것이다", "~할 것으로", "~일 것이다", "~일 것으로",
    "~할 것임", "~일 것임",
    "~할 전망", "~할 가능성이 높다",
]

# Category 3: 추정 표현 (Estimation Expressions)
ESTIMATION_PATTERNS = [
    "추정됨", "추정된다", "추정할 수 있다",
    "추산됨", "추산된다",
    "것으로 보인다", "것으로 보임", "것으로 판단된다",
    "것으로 추측된다", "것으로 예상된다",
    "~로 보인다", "~로 보임",
]

# Category 4: 불확실성 표현 (Uncertainty Expressions)
UNCERTAINTY_PATTERNS = [
    "약 ", "대략 ", "대충 ", "정도 ", "가량 ", "내외 ",
    "~쯤", "~경", "~여",
    "일반적으로", "통상적으로", "보통",
    "아마도", "어쩌면", "혹시",
]

# Category 5: 즉시성 표현 (Urgency Expressions)
URGENCY_PATTERNS = [
    "즉시", "당장", "시급히", "긴급", "급히",
    "조속히", "빨리", "지체없이",
]

# Category 6: 과장 표현 (Exaggeration Expressions)
EXAGGERATION_PATTERNS = [
    "매우 심각", "극심한", "엄청난", "대폭",
    "급격히", "급속히", "폭발적",
    "사상 최대", "사상 최고", "역대 최대",
]

# Compile all patterns
ALL_FORBIDDEN_LITERALS = (
    CERTAINTY_PATTERNS +
    PREDICTION_PATTERNS +
    ESTIMATION_PATTERNS +
    UNCERTAINTY_PATTERNS +
    URGENCY_PATTERNS +
    EXAGGERATION_PATTERNS
)

COMPILED_FORBIDDEN_LITERALS = [re.compile(re.escape(p)) for p in ALL_FORBIDDEN_LITERALS]

# Category 7: 위험 정규식 패턴 (Advanced Regex Patterns)
REGEX_FORBIDDEN_PATTERNS = [
    r"\d{2,3}%\s*(급등|폭등|급락|폭락)",  # 극단적 수치 + 과장
    r"(사상|역대)\s*(최고|최대|최저|최악)",  # 사상 최대류
    r"전년\s*대비\s*\d{3,}%",  # 비현실적 전년대비 (100%+)
    r"(곧|조만간|머지않아|향후)",  # 불명확한 시간
    r"(예정|계획|검토)\s*(중|이다)",  # 미확정 사항
    r"(관계자|소식통|업계)\s*(에\s*)?따르면",  # 익명 소스
    r"(것으로\s*)?(알려졌다|전해졌다|밝혀졌다)",  # 간접 정보
    r"~(할|될)\s*(것으로|수)\s*(있|보)",  # 추측 표현
]

COMPILED_REGEX_FORBIDDEN = [re.compile(p) for p in REGEX_FORBIDDEN_PATTERNS]


def check_forbidden_patterns(text: str) -> list[dict]:
    """
    Check text for forbidden patterns.

    Returns:
        list of dicts with 'pattern' and 'category' keys
    """
    matches = []

    # Check literal patterns with categories
    for i, pattern in enumerate(COMPILED_FORBIDDEN_LITERALS):
        if pattern.search(text):
            # Determine category
            if i < len(CERTAINTY_PATTERNS):
                category = ForbiddenCategory.CERTAINTY
            elif i < len(CERTAINTY_PATTERNS) + len(PREDICTION_PATTERNS):
                category = ForbiddenCategory.PREDICTION
            elif i < len(CERTAINTY_PATTERNS) + len(PREDICTION_PATTERNS) + len(ESTIMATION_PATTERNS):
                category = ForbiddenCategory.ESTIMATION
            elif i < len(CERTAINTY_PATTERNS) + len(PREDICTION_PATTERNS) + len(ESTIMATION_PATTERNS) + len(UNCERTAINTY_PATTERNS):
                category = ForbiddenCategory.UNCERTAINTY
            elif i < len(CERTAINTY_PATTERNS) + len(PREDICTION_PATTERNS) + len(ESTIMATION_PATTERNS) + len(UNCERTAINTY_PATTERNS) + len(URGENCY_PATTERNS):
                category = ForbiddenCategory.URGENCY
            else:
                category = ForbiddenCategory.EXAGGERATION

            matches.append({
                "pattern": pattern.pattern,
                "category": category.value
            })

    # Check regex patterns
    for pattern in COMPILED_REGEX_FORBIDDEN:
        if pattern.search(text):
            matches.append({
                "pattern": pattern.pattern,
                "category": "고급 패턴"
            })

    return matches


# =============================================================================
# CORE PRINCIPLES v2.0
# =============================================================================

V2_CORE_PRINCIPLES = """
## 핵심 원칙 (Hallucination Zero Tolerance)

### 원칙 1: Closed-World Assumption (CWA)
- 제공된 데이터에 있는 정보**만** 추출
- 제공되지 않은 정보 → null (생성 절대 금지)
- "확인 불가"는 정답, 추측은 오답

### 원칙 2: Evidence-First (근거 우선)
- 모든 수치/금액/날짜는 Evidence에서 **직접** 확인
- 확인 불가 시 해당 정보 사용 금지
- Evidence 없는 시그널 = 무효

### 원칙 3: Verbatim Extraction (원문 추출)
- 가능하면 원문 그대로 인용
- 요약 시에도 핵심 수치는 원문 유지
- "~로 보도됨", "~에 따르면" 출처 명시

### 원칙 4: Retrieval Confidence (추출 신뢰도)
모든 정보에 다음 태그 중 하나 **필수**:
- `VERBATIM`: 원문 그대로 복사 (최우선)
- `PARAPHRASED`: 원문 기반 정리 (허용)
- `INFERRED`: 추론 (**confidence_reason 필수**, 없으면 거부)
"""

# =============================================================================
# STRICT JSON SCHEMA
# =============================================================================

STRICT_JSON_SCHEMA = """
## Strict JSON Schema (필수 준수)

### Signal Object (* = 필수)
```json
{
  "signal_type": "DIRECT|INDUSTRY|ENVIRONMENT",  // *
  "event_type": "<10종 중 하나>",  // *
  "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",  // *
  "impact_strength": "HIGH|MED|LOW",  // *
  "confidence": "HIGH|MED|LOW",  // * (출처 등급 기반)
  "retrieval_confidence": "VERBATIM|PARAPHRASED|INFERRED",  // *
  "confidence_reason": "string",  // INFERRED인 경우 필수
  "title": "string, max 50자, 기업명 포함",  // *
  "summary": "string, 80-200자, 정량정보 필수",  // *
  "evidence": [  // * 최소 1개
    {
      "evidence_type": "INTERNAL_FIELD|DOC|EXTERNAL",  // *
      "ref_type": "SNAPSHOT_KEYPATH|DOC_PAGE|URL",  // *
      "ref_value": "경로 또는 URL",  // *
      "snippet": "원문 발췌 20-100자"  // *
    }
  ]
}
```

### Confidence 결정 규칙
| Confidence | 조건 |
|------------|------|
| HIGH | Tier1 출처 + 정량정보 직접 확인 + VERBATIM |
| MED | Tier2 출처 + 핵심사실 확인 + PARAPHRASED 허용 |
| LOW | 단일 출처 또는 INFERRED |

### Tier 분류
- Tier 1: dart.fss.or.kr, *.go.kr, 내부 스냅샷 (HIGH 가능)
- Tier 2: hankyung.com, mk.co.kr, reuters, bloomberg (MED 가능)
- Tier 3: 일반 뉴스, 블로그 (시그널 생성 불가)
"""

# =============================================================================
# CHAIN OF VERIFICATION
# =============================================================================

CHAIN_OF_VERIFICATION = """
## Chain-of-Verification (CoV)

시그널 생성 완료 후, 다음 체크리스트 **반드시** 수행:

### 1. Evidence 존재 검증
- [ ] summary의 모든 수치가 evidence[].snippet에 있는가?
  → 없다 → 해당 수치 삭제
- [ ] evidence[].ref_value가 입력 데이터에 실제 존재하는가?
  → 없다 → evidence 삭제 → 시그널 무효

### 2. 기업명 검증
- [ ] title에 기업명이 포함되어 있는가?
- [ ] summary에 기업명이 포함되어 있는가?
- [ ] 극단적 이벤트(상장폐지, 부도 등)의 경우:
  → evidence.snippet에도 기업명이 있어야 함 (Entity Confusion 방지)

### 3. 금지 표현 검증
- [ ] title에 금지 표현이 없는가?
- [ ] summary에 금지 표현이 없는가?
  → 있다 → 허용 표현으로 대체

### 4. retrieval_confidence 검증
- [ ] retrieval_confidence가 명시되어 있는가?
- [ ] INFERRED인 경우 confidence_reason이 있는가?
  → 없다 → 시그널 무효
"""

# =============================================================================
# PERSONAS
# =============================================================================

RISK_MANAGER_PERSONA = """
### Risk Manager 페르소나: 박준혁 팀장

**프로필**
- 직책: 기업여신심사역 팀장, 시중은행 기업금융본부
- 경력: 15년 (기업여신심사 12년, 부실채권관리 3년)
- 철학: "모르면 모른다고 하는 것이 프로다"

**핵심 질문**
"이 기업에 10억원을 대출해줬을 때, 원리금을 제때 상환할 수 있는가?"

**Red Flags (HIGH 신뢰도 필수)**
| Flag | 기준 | 필요 Evidence |
|------|------|--------------|
| 연체 | 30일 이상 | 내부 스냅샷 |
| 등급 하락 | 2단계+ | 내부 스냅샷 |
| 매출 급감 | 전년비 -20%+ | 재무제표/공시 |
| 부채비율 급증 | +50%p 이상 | 재무제표 |
| 대표 변경 + 주주 변경 | 동시 발생 | 등기부/공시 |

**의사결정 스타일**
- Evidence 없으면 판단 유보
- 숫자로 증명되지 않으면 "확인 필요" 표기
- False Positive보다 False Negative가 낫다
"""

IB_MANAGER_PERSONA = """
### IB Manager 페르소나: 김서연 이사

**프로필**
- 직책: 기업금융팀 이사, 대형 증권사 IB본부
- 경력: 12년 (M&A 자문 5년, 기업투자 7년)
- 철학: "확실한 기회만 선별한다"

**핵심 질문**
"이 기업에 50억원을 투자했을 때, 3-5년 내 2배 이상 회수할 수 있는가?"

**Green Flags (Evidence 기반만)**
| Flag | 기준 | 필요 Evidence |
|------|------|--------------|
| 대형 수주 | 매출 10%+ 규모 | 공시/계약서/뉴스 |
| 정부 지원 | 공식 선정 발표 | 정부 보도자료 |
| 전략적 투자 | 지분 5%+ 취득 | 공시/등기 |

**의사결정 스타일**
- MOU ≠ 계약 (구속력 명시 필수)
- 예상 효과는 공시된 것만 인용
- 낙관적 추정보다 보수적 판단
"""

# =============================================================================
# FEW-SHOT EXAMPLES: DIRECT (16개)
# =============================================================================

DIRECT_EXAMPLES = """
## DIRECT 시그널 예시 (16개)

### 1. OVERDUE_FLAG_ON - RISK
```json
{
  "signal_type": "DIRECT",
  "event_type": "OVERDUE_FLAG_ON",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "엠케이전자 30일 이상 연체 발생",
  "summary": "엠케이전자의 기업여신 계좌에서 2026년 1월 기준 30일 이상 연체가 확인됨. 내부 스냅샷에서 overdue_flag가 true로 확인. 상환능력 저하 신호로 담보 점검 권고.",
  "evidence": [
    {
      "evidence_type": "INTERNAL_FIELD",
      "ref_type": "SNAPSHOT_KEYPATH",
      "ref_value": "/credit/loan_summary/overdue_flag",
      "snippet": "overdue_flag: true"
    }
  ]
}
```

### 2. OVERDUE_FLAG_ON - OPPORTUNITY (연체 해소)
```json
{
  "signal_type": "DIRECT",
  "event_type": "OVERDUE_FLAG_ON",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "동부건설 연체 해소 확인",
  "summary": "동부건설의 30일 이상 연체 상태가 해소됨. 내부 스냅샷에서 overdue_flag가 false로 전환 확인. 상환능력 정상화 신호.",
  "evidence": [
    {
      "evidence_type": "INTERNAL_FIELD",
      "ref_type": "SNAPSHOT_KEYPATH",
      "ref_value": "/credit/loan_summary/overdue_flag",
      "snippet": "overdue_flag: false (이전: true)"
    }
  ]
}
```

### 3. INTERNAL_RISK_GRADE_CHANGE - RISK
```json
{
  "signal_type": "DIRECT",
  "event_type": "INTERNAL_RISK_GRADE_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "전북식품 내부신용등급 2단계 하락",
  "summary": "전북식품의 내부신용등급이 BBB에서 BB로 2단계 하락함. 내부 스냅샷에서 확인. 기존 여신 조건 재검토 대상.",
  "evidence": [
    {
      "evidence_type": "INTERNAL_FIELD",
      "ref_type": "SNAPSHOT_KEYPATH",
      "ref_value": "/corp/kyc_status/internal_risk_grade",
      "snippet": "internal_risk_grade: BB (이전: BBB)"
    }
  ]
}
```

### 4. INTERNAL_RISK_GRADE_CHANGE - OPPORTUNITY
```json
{
  "signal_type": "DIRECT",
  "event_type": "INTERNAL_RISK_GRADE_CHANGE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "광주정밀기계 내부신용등급 상향 조정",
  "summary": "광주정밀기계의 내부신용등급이 BB에서 BBB로 1단계 상향됨. 내부 스냅샷에서 확인. 여신 확대 검토 가능.",
  "evidence": [
    {
      "evidence_type": "INTERNAL_FIELD",
      "ref_type": "SNAPSHOT_KEYPATH",
      "ref_value": "/corp/kyc_status/internal_risk_grade",
      "snippet": "internal_risk_grade: BBB (이전: BB)"
    }
  ]
}
```

### 5. LOAN_EXPOSURE_CHANGE - RISK
```json
{
  "signal_type": "DIRECT",
  "event_type": "LOAN_EXPOSURE_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "MED",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "휴림로봇 여신 노출 15% 증가",
  "summary": "휴림로봇의 총 여신 노출이 100억원에서 115억원으로 15% 증가함. 내부 스냅샷에서 확인. 담보 커버리지 점검 권고.",
  "evidence": [
    {
      "evidence_type": "INTERNAL_FIELD",
      "ref_type": "SNAPSHOT_KEYPATH",
      "ref_value": "/credit/loan_summary/total_exposure_krw",
      "snippet": "total_exposure_krw: 11500000000 (이전: 10000000000)"
    }
  ]
}
```

### 6. LOAN_EXPOSURE_CHANGE - OPPORTUNITY
```json
{
  "signal_type": "DIRECT",
  "event_type": "LOAN_EXPOSURE_CHANGE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "LOW",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "삼성전자 여신 노출 10% 감소",
  "summary": "삼성전자의 총 여신 노출이 500억원에서 450억원으로 10% 감소함. 내부 스냅샷에서 확인. 상환 능력 개선 신호.",
  "evidence": [
    {
      "evidence_type": "INTERNAL_FIELD",
      "ref_type": "SNAPSHOT_KEYPATH",
      "ref_value": "/credit/loan_summary/total_exposure_krw",
      "snippet": "total_exposure_krw: 45000000000 (이전: 50000000000)"
    }
  ]
}
```

### 7. COLLATERAL_CHANGE - RISK
```json
{
  "signal_type": "DIRECT",
  "event_type": "COLLATERAL_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "동부건설 담보가치 20% 하락",
  "summary": "동부건설의 담보 부동산 가치가 80억원에서 64억원으로 20% 하락함. 내부 스냅샷에서 확인. LTV 재산정 및 추가 담보 검토 권고.",
  "evidence": [
    {
      "evidence_type": "INTERNAL_FIELD",
      "ref_type": "SNAPSHOT_KEYPATH",
      "ref_value": "/collateral/total_value_krw",
      "snippet": "total_value_krw: 6400000000 (이전: 8000000000)"
    }
  ]
}
```

### 8. COLLATERAL_CHANGE - OPPORTUNITY
```json
{
  "signal_type": "DIRECT",
  "event_type": "COLLATERAL_CHANGE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "엠케이전자 신규 담보 30억원 설정",
  "summary": "엠케이전자가 신규 담보(토지)를 추가 설정함. 담보가치 30억원. 내부 스냅샷에서 확인. 여신 커버리지 개선.",
  "evidence": [
    {
      "evidence_type": "INTERNAL_FIELD",
      "ref_type": "SNAPSHOT_KEYPATH",
      "ref_value": "/collateral/items",
      "snippet": "신규 담보: 토지, 가치: 3000000000원"
    }
  ]
}
```

### 9. OWNERSHIP_CHANGE - RISK
```json
{
  "signal_type": "DIRECT",
  "event_type": "OWNERSHIP_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "PARAPHRASED",
  "title": "전북식품 대주주 지분 35% 전량 매각",
  "summary": "전북식품의 대주주 홍길동(지분 35%)이 지분 전량을 매각함. DART 주요주주 변동 공시에 따름. 경영 연속성 리스크 점검 권고.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260115000001",
      "snippet": "홍길동, 보유지분 35% 전량 매도, 2026.01.15"
    }
  ]
}
```

### 10. OWNERSHIP_CHANGE - OPPORTUNITY
```json
{
  "signal_type": "DIRECT",
  "event_type": "OWNERSHIP_CHANGE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "광주정밀기계 LG전자 전략적 투자 100억원 유치",
  "summary": "광주정밀기계가 LG전자로부터 100억원 규모 전략적 투자를 유치함. 지분 10% 취득. DART 공시에 따름. 기술 협력 및 안정적 매출처 확보.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260120000002",
      "snippet": "LG전자, 광주정밀기계 지분 10%(100억원) 취득, 2026.01.20"
    }
  ]
}
```

### 11. GOVERNANCE_CHANGE - RISK
```json
{
  "signal_type": "DIRECT",
  "event_type": "GOVERNANCE_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "MED",
  "retrieval_confidence": "PARAPHRASED",
  "title": "휴림로봇 대표이사 횡령 의혹 사임",
  "summary": "휴림로봇 김봉관 대표이사가 돌연 사임함. 한국경제 보도에 따르면 회사 자금 횡령 의혹으로 검찰 수사 진행 중. 신임 대표 미선임 상태로 경영 공백 우려.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.hankyung.com/article/202601200001",
      "snippet": "휴림로봇 김봉관 대표, 횡령 의혹으로 사임...검찰 수사 착수"
    }
  ]
}
```

### 12. GOVERNANCE_CHANGE - OPPORTUNITY
```json
{
  "signal_type": "DIRECT",
  "event_type": "GOVERNANCE_CHANGE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "삼성전자 前 LG 부사장 CFO 영입",
  "summary": "삼성전자가 LG전자 前 부사장 이재용을 CFO로 영입함. DART 임원변경 공시에 따름. 재무 전문성 강화 및 투자자 신뢰 제고.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260201000003",
      "snippet": "CFO 선임: 이재용 (前 LG전자 부사장), 2026.02.01 취임"
    }
  ]
}
```

### 13. FINANCIAL_STATEMENT_UPDATE - RISK
```json
{
  "signal_type": "DIRECT",
  "event_type": "FINANCIAL_STATEMENT_UPDATE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "동부건설 2025년 영업손실 120억원 기록",
  "summary": "동부건설의 2025년 연결 기준 영업손실 120억원 기록. DART 사업보고서에 따름. 전년 영업이익 50억원 대비 적자전환. 현금흐름 점검 권고.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260315000004",
      "snippet": "2025년 영업이익: -12,000백만원 (전년: 5,000백만원)"
    }
  ]
}
```

### 14. FINANCIAL_STATEMENT_UPDATE - OPPORTUNITY
```json
{
  "signal_type": "DIRECT",
  "event_type": "FINANCIAL_STATEMENT_UPDATE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "엠케이전자 2025년 매출 30% 성장",
  "summary": "엠케이전자의 2025년 매출액이 1,500억원으로 전년(1,154억원) 대비 30% 성장함. DART 사업보고서에 따름. 반도체 수요 회복 영향.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260315000005",
      "snippet": "2025년 매출액: 150,000백만원 (전년: 115,400백만원, +30.0%)"
    }
  ]
}
```

### 15. KYC_REFRESH - NEUTRAL
```json
{
  "signal_type": "DIRECT",
  "event_type": "KYC_REFRESH",
  "impact_direction": "NEUTRAL",
  "impact_strength": "LOW",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "전북식품 KYC 정기 갱신 시점 도래",
  "summary": "전북식품의 KYC 갱신 시점이 도래함(마지막 갱신: 2025-01-15, 12개월 경과). 내부 스냅샷에서 확인. 정기 점검 프로세스 진행 필요.",
  "evidence": [
    {
      "evidence_type": "INTERNAL_FIELD",
      "ref_type": "SNAPSHOT_KEYPATH",
      "ref_value": "/corp/kyc_status/last_kyc_updated",
      "snippet": "last_kyc_updated: 2025-01-15"
    }
  ]
}
```

### 16. KYC_REFRESH - RISK (정보 불일치)
```json
{
  "signal_type": "DIRECT",
  "event_type": "KYC_REFRESH",
  "impact_direction": "RISK",
  "impact_strength": "MED",
  "confidence": "MED",
  "retrieval_confidence": "INFERRED",
  "confidence_reason": "외부 공시 정보와 내부 KYC 정보 간 대표이사 불일치 확인",
  "title": "광주정밀기계 KYC 정보 불일치 발견",
  "summary": "광주정밀기계의 내부 KYC 정보와 DART 공시 정보 간 불일치 발견. 내부: 대표이사 김철수, DART: 대표이사 강성우. 정보 갱신 필요.",
  "evidence": [
    {
      "evidence_type": "INTERNAL_FIELD",
      "ref_type": "SNAPSHOT_KEYPATH",
      "ref_value": "/corp/ceo_name",
      "snippet": "ceo_name: 김철수"
    },
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260115000006",
      "snippet": "대표이사: 강성우"
    }
  ]
}
```
"""

# =============================================================================
# FEW-SHOT EXAMPLES: INDUSTRY (10개)
# =============================================================================

INDUSTRY_EXAMPLES = """
## INDUSTRY 시그널 예시 (10개)

### 1. 시장 수요 변화 - RISK
```json
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "글로벌 반도체 수요 급감, 메모리 가격 20% 하락",
  "summary": "글로벌 반도체 수요 감소로 메모리 가격이 전분기 대비 20% 하락함. 트렌드포스 발표 기준. 삼성전자는 전자부품제조업(C26)으로 해당 업황 변화의 영향을 받을 수 있음.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.trendforce.com/news/202601200001",
      "snippet": "DRAM 가격 20% 하락...2026년 1분기 추가 하락 가능"
    }
  ]
}
```

### 2. 시장 수요 변화 - OPPORTUNITY
```json
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "AI 서버 수요 급증, HBM 가격 35% 상승",
  "summary": "AI 학습용 서버 수요 급증으로 HBM 공급 부족 현상 발생. 블룸버그 보도에 따르면 HBM 가격 전분기 대비 35% 상승. 삼성전자는 전자부품제조업(C26)으로 HBM 생산업체로서 수혜 가능.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.bloomberg.com/news/202601150001",
      "snippet": "HBM prices surge 35% as AI demand outpaces supply"
    }
  ]
}
```

### 3. 공급 충격 - RISK
```json
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "철근 가격 30% 급등, 건설업 원가 부담 가중",
  "summary": "철근 가격이 전년 대비 30% 상승함. 한국철강협회 발표 기준. 동부건설은 건설업(F41)으로 원자재 원가 상승 영향을 직접 받을 수 있음.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.kosa.or.kr/news/202601200001",
      "snippet": "철근 가격 톤당 90만원 돌파...전년비 30% 상승"
    }
  ]
}
```

### 4. 공급 충격 - OPPORTUNITY
```json
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "confidence": "MED",
  "retrieval_confidence": "PARAPHRASED",
  "title": "밀가루 가격 15% 하락, 식품업계 원가 부담 완화",
  "summary": "국제 밀 가격이 6개월 연속 하락하며 안정세. 농림축산식품부 발표 기준 밀가루 가격 전년비 15% 하락. 전북식품은 식품제조업(C10)으로 원가 개선 효과가 있을 수 있음.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.mafra.go.kr/news/202601200001",
      "snippet": "밀가루 수입가격 15% 하락, 6개월 연속 하락세 지속"
    }
  ]
}
```

### 5. 경쟁 구도 변화 - RISK
```json
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "중국 전기차 업체 한국 시장 본격 진출",
  "summary": "BYD, NIO 등 중국 전기차 업체가 한국 시장에 본격 진출함. 조선비즈 보도에 따르면 2026년 내 5개 브랜드 출시. 휴림로봇은 전기업(D35) 관련 사업으로 경쟁 심화 영향 모니터링 필요.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://biz.chosun.com/news/202601200001",
      "snippet": "BYD 한국 법인 설립...2026년 상반기 정식 출시 예정"
    }
  ]
}
```

### 6. 경쟁 구도 변화 - OPPORTUNITY
```json
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "confidence": "MED",
  "retrieval_confidence": "PARAPHRASED",
  "title": "국내 1위 경쟁사 사업 축소, 시장점유율 변화 가능",
  "summary": "국내 기계장비 1위 업체 A사가 사업 구조조정을 발표함. 매일경제 보도에 따르면 A사 3개 사업부 매각 추진 중. 광주정밀기계는 기계장비제조업(C29)으로 시장점유율 확대 기회 가능.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.mk.co.kr/news/202601200001",
      "snippet": "A사, 비핵심 사업부 3곳 매각...경쟁 구도 재편"
    }
  ]
}
```

### 7. 기술 변화 - RISK
```json
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "RISK",
  "impact_strength": "MED",
  "confidence": "MED",
  "retrieval_confidence": "PARAPHRASED",
  "title": "차세대 반도체 공정 전환 가속화, 기존 장비 수요 감소",
  "summary": "글로벌 반도체 업체들이 3nm 이하 공정 전환을 가속화함. 디지타임스 보도 기준 2nm 공정 투자 비중 2배 증가. 엠케이전자는 전자부품제조업(C26)으로 기존 공정 장비 수요 감소 영향 모니터링 필요.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.digitimes.com/news/202601200001",
      "snippet": "2nm 공정 투자 비중 2배 증가...기존 공정 투자는 축소"
    }
  ]
}
```

### 8. 기술 변화 - OPPORTUNITY
```json
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "스마트팩토리 도입 40% 증가, 산업로봇 수요 확대",
  "summary": "제조업 스마트팩토리 도입이 전년비 40% 증가함. 산업통상자원부 발표 기준. 광주정밀기계는 기계장비제조업(C29)으로 산업로봇 수요 확대 수혜 가능.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.motie.go.kr/news/202601200001",
      "snippet": "2025년 스마트팩토리 구축 기업 수 40% 증가...산업로봇 수요 동반 성장"
    }
  ]
}
```

### 9. 글로벌 시장 변화 - RISK
```json
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "건설업 PF 연체율 8.5%, 중견 건설사 연쇄 위기",
  "summary": "금융감독원 발표에 따르면 건설업 PF 연체율이 8.5%로 전년 대비 3%p 상승함. 중견 건설사 3곳이 워크아웃 신청. 동부건설은 건설업(F41)으로 PF 익스포저 점검 권고.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.fss.or.kr/news/202601200001",
      "snippet": "건설 PF 연체율 8.5%...중견 3사 워크아웃 신청"
    }
  ]
}
```

### 10. 글로벌 시장 변화 - OPPORTUNITY
```json
{
  "signal_type": "INDUSTRY",
  "event_type": "INDUSTRY_SHOCK",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "K-푸드 수출 100억불 돌파, 식품업계 수혜",
  "summary": "농림축산식품부 발표에 따르면 2025년 K-푸드 수출액이 100억 달러를 돌파함. 동남아/중동 시장에서 30% 이상 성장. 전북식품은 식품제조업(C10)으로 해당 수출 증가의 수혜 가능.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.mafra.go.kr/news/202601200002",
      "snippet": "K-푸드 수출 100억불 돌파...동남아/중동 30%+ 성장"
    }
  ]
}
```
"""

# =============================================================================
# FEW-SHOT EXAMPLES: ENVIRONMENT (11개)
# =============================================================================

ENVIRONMENT_EXAMPLES = """
## ENVIRONMENT 시그널 예시 (11개)

### 1. FX_RISK (환율 변동)
```json
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "MED",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "원/달러 환율 1,450원 돌파, 연중 최고치",
  "summary": "원/달러 환율이 1,450원을 돌파하며 연중 최고치 기록. 한국은행 발표 기준. 엠케이전자는 수출 비중 45%로 환율 변동의 양면적 영향(수출 경쟁력 vs 수입원가)을 받을 수 있음.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.bok.or.kr/news/202601200001",
      "snippet": "원/달러 환율 1,450.5원 마감...연중 최고치 경신"
    }
  ]
}
```

### 2. TRADE_BLOC (무역/관세)
```json
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "미국 반도체 관세 25% 부과 발표",
  "summary": "미국이 중국산 반도체에 25% 관세 부과를 발표함. USTR 공식 발표 기준, 2026년 4월 시행. 삼성전자는 전자부품제조업(C26)으로 미국 수출 시 간접 영향 모니터링 필요.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://ustr.gov/news/202601150001",
      "snippet": "25% tariff on semiconductor imports from China, effective April 2026"
    }
  ]
}
```

### 3. GEOPOLITICAL (지정학)
```json
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "MED",
  "retrieval_confidence": "PARAPHRASED",
  "title": "홍해 지역 긴장, 해운 물류비 30% 상승",
  "summary": "홍해 지역 긴장 고조로 주요 해운사들이 수에즈 운하 회피 항로 운항 중. 로이터 보도 기준 해상 운임 30% 상승. 엠케이전자는 해외 수출 비중이 높아 물류비 상승 영향을 받을 수 있음.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.reuters.com/news/202601200001",
      "snippet": "Major shipping lines avoiding Red Sea...freight rates up 30%"
    }
  ]
}
```

### 4. SUPPLY_CHAIN (공급망)
```json
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "반도체 공급망 안정화 지원금 1조원 편성",
  "summary": "산업통상자원부가 반도체 공급망 안정화 지원책을 발표함. 핵심 소재 국내 생산 지원금 1조원 편성. 엠케이전자는 전자부품제조업(C26)으로 정부 지원 대상이 될 수 있음.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.motie.go.kr/news/202601200002",
      "snippet": "반도체 소재 국산화 지원 1조원...2026년 하반기 시행"
    }
  ]
}
```

### 5. REGULATION (산업 규제)
```json
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "MED",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "식품 영양성분 표시 강화, 2026년 3월 시행",
  "summary": "식품의약품안전처가 식품 영양성분 표시 기준을 강화함. 당류/나트륨 전면 표기 의무화. 전북식품은 식품제조업(C10)으로 포장 변경 비용 발생 가능.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.mfds.go.kr/news/202601200001",
      "snippet": "당류/나트륨 전면 표시 의무화...2026년 3월 시행"
    }
  ]
}
```

### 6. COMMODITY (원자재)
```json
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "중국 희토류 수출 쿼터제 도입, 연간 30% 감축",
  "summary": "중국 상무부가 희토류 수출 쿼터제 도입을 발표함. 연간 수출량 30% 감축. 광주정밀기계는 기계장비제조업(C29)으로 모터/센서 등 희토류 사용 부품 원가 영향 모니터링 필요.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "http://www.mofcom.gov.cn/news/202601200001",
      "snippet": "稀土出口配额制实施...年出口量削减30%"
    }
  ]
}
```

### 7. PANDEMIC_HEALTH (보건/팬데믹)
```json
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "MED",
  "confidence": "MED",
  "retrieval_confidence": "PARAPHRASED",
  "title": "동남아 신종 감염병 확산, WHO 경보 발령",
  "summary": "WHO가 동남아 지역 신종 감염병 확산에 대해 경보 발령. 베트남/태국 출장 제한 권고. 삼성전자는 베트남 생산시설 운영으로 생산 차질 가능성 모니터링 필요.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.who.int/news/202601200001",
      "snippet": "WHO issues alert for new infectious disease in Southeast Asia"
    }
  ]
}
```

### 8. POLITICAL_INSTABILITY (정치 불안)
```json
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "MED",
  "retrieval_confidence": "PARAPHRASED",
  "title": "수출국 정치 불안정, 결제 리스크 증가",
  "summary": "A국 정치 불안정으로 금융시장 마비 상태. 로이터 보도 기준 달러 결제 지연 사례 발생. 해당 국가 수출 비중이 있는 기업은 결제 리스크 점검 권고.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.reuters.com/news/202601200002",
      "snippet": "Financial markets paralyzed amid political crisis...payment delays reported"
    }
  ]
}
```

### 9. CYBER_TECH (사이버/기술)
```json
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "MED",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "개인정보보호법 개정, 과징금 상한 매출액 4%",
  "summary": "개인정보보호법 개정으로 과징금 상한이 매출액 4%로 상향됨. 2026년 6월 시행. 삼성전자는 고객 데이터 처리 기업으로 컴플라이언스 점검 필요.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.law.go.kr/news/202601200001",
      "snippet": "개인정보보호법 개정...과징금 상한 매출액 4%로 상향"
    }
  ]
}
```

### 10. ENERGY_SECURITY (에너지 안보)
```json
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "MED",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "신재생에너지 발전 비중 목표 30%로 상향",
  "summary": "산업통상자원부가 2030년 신재생에너지 발전 비중 목표를 25%에서 30%로 상향함. 휴림로봇은 전기업(D35) 관련 사업으로 신재생에너지 설비 수요 증가 수혜 가능.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.motie.go.kr/news/202601200003",
      "snippet": "2030 신재생에너지 발전 비중 목표 30%로 상향 조정"
    }
  ]
}
```

### 11. FOOD_SECURITY (식량 안보)
```json
{
  "signal_type": "ENVIRONMENT",
  "event_type": "POLICY_REGULATION_CHANGE",
  "impact_direction": "OPPORTUNITY",
  "impact_strength": "LOW",
  "confidence": "HIGH",
  "retrieval_confidence": "VERBATIM",
  "title": "식량 자급률 제고 정책, 국산 원료 세제 혜택",
  "summary": "농림축산식품부가 식량 자급률 제고 5개년 계획을 발표함. 국산 농산물 사용 기업에 세제 혜택 부여. 전북식품은 식품제조업(C10)으로 국산 원료 사용 시 세제 혜택 가능.",
  "evidence": [
    {
      "evidence_type": "EXTERNAL",
      "ref_type": "URL",
      "ref_value": "https://www.mafra.go.kr/news/202601200003",
      "snippet": "식량 자급률 60% 목표...국산 원료 사용 기업 세제 혜택"
    }
  ]
}
```
"""

# =============================================================================
# REJECTION EXAMPLES
# =============================================================================

REJECTION_EXAMPLES = """
## 시그널 생성 금지 예시 (Rejection Cases)

### ❌ Case 1: 수치가 Evidence에 없음 (Hallucination)
**문제**: summary에 "88% 감소"가 있지만 검색 결과에서 확인 불가
**결과**: 거부

### ❌ Case 2: 다른 기업 정보 귀속 (Entity Confusion)
**문제**: "상장폐지"가 다른 기업에 대한 것인데 분석 대상 기업에 귀속
**결과**: 거부

### ❌ Case 3: Evidence URL이 검색 결과에 없음 (Fabricated URL)
**문제**: LLM이 존재하지 않는 URL을 생성
**결과**: 거부

### ❌ Case 4: 금지 표현 사용
**문제**: "급락할 것으로 예상됨", "즉시 점검 필요" 등 사용
**결과**: 거부

### ❌ Case 5: INFERRED인데 confidence_reason 없음
**문제**: 추론인데 근거 설명 누락
**결과**: 거부

### ❌ Case 6: 잘못된 분류
**문제**: 산업 전체 이슈를 DIRECT로 분류
**결과**: 거부 (INDUSTRY여야 함)

---
**✅ 올바른 대응**: 위 경우들은 시그널을 생성하지 않고 빈 배열 [] 반환
"""

# =============================================================================
# PROMPT BUILDERS
# =============================================================================

def build_enhanced_system_prompt(
    signal_type: str,
    corp_name: str,
    industry_code: str,
    industry_name: str,
) -> str:
    """
    Build enhanced system prompt for signal extraction.

    Args:
        signal_type: DIRECT, INDUSTRY, or ENVIRONMENT
        corp_name: Corporation name
        industry_code: Industry code
        industry_name: Industry name

    Returns:
        Complete system prompt
    """
    # Select appropriate examples
    if signal_type.upper() == "DIRECT":
        examples = DIRECT_EXAMPLES
    elif signal_type.upper() == "INDUSTRY":
        examples = INDUSTRY_EXAMPLES
    elif signal_type.upper() == "ENVIRONMENT":
        examples = ENVIRONMENT_EXAMPLES
    else:
        examples = DIRECT_EXAMPLES

    return f"""# Signal Extraction System Prompt (Enhanced)

당신은 한국 금융기관의 기업심사 AI 분석가입니다.
**{signal_type}** 유형의 시그널만 추출합니다.

## 분석 대상
- 기업명: {corp_name}
- 업종: {industry_code} ({industry_name})

{V2_CORE_PRINCIPLES}

## 전문가 페르소나
{RISK_MANAGER_PERSONA}

{IB_MANAGER_PERSONA}

{STRICT_JSON_SCHEMA}

{CHAIN_OF_VERIFICATION}

{examples}

{REJECTION_EXAMPLES}

## 최종 지침
1. **Hallucination Zero Tolerance**: 입력 데이터에 없는 정보 생성 절대 금지
2. **Evidence-First**: 모든 주장은 evidence로 검증 가능해야 함
3. **빈 결과 허용**: 확실한 시그널이 없으면 {{"signals": []}} 반환
4. **금지 표현 검열**: 사용 시 자동 거부됨
5. **기업명 필수**: title과 summary에 반드시 포함

## 출력 형식
```json
{{
  "signals": [...]
}}
```
"""


def build_enhanced_user_prompt(
    corp_name: str,
    corp_reg_no: str,
    industry_code: str,
    industry_name: str,
    snapshot_json: str,
    events_data: str,
    signal_type: str = "DIRECT",
) -> str:
    """
    Build enhanced user prompt for signal extraction.

    Args:
        corp_name: Corporation name
        corp_reg_no: Corporation registration number
        industry_code: Industry code
        industry_name: Industry name
        snapshot_json: Internal snapshot JSON
        events_data: External events JSON
        signal_type: Signal type to extract

    Returns:
        Complete user prompt
    """
    return f"""# 분석 대상 기업
- 기업명: {corp_name}
- 법인번호: {corp_reg_no or "N/A"}
- 업종: {industry_code} ({industry_name})
- 분석 유형: {signal_type}

# 내부 스냅샷 데이터 (INTERNAL_FIELD Evidence 소스)
```json
{snapshot_json}
```

# 외부 이벤트 데이터 (EXTERNAL Evidence 소스)
```json
{events_data}
```

# 분석 요청

위 데이터에서 **{signal_type}** 유형의 시그널을 추출하세요.

## 필수 체크리스트
1. [ ] summary의 모든 수치가 위 데이터에 있는가?
2. [ ] evidence URL이 위 외부 이벤트에 있는가?
3. [ ] evidence keypath가 스냅샷에 실제 존재하는가?
4. [ ] title과 summary에 기업명({corp_name})이 있는가?
5. [ ] 금지 표현(예상됨, 약, 즉시 등)이 없는가?
6. [ ] retrieval_confidence가 명시되어 있는가?

## 출력
- 시그널이 있으면: {{"signals": [...]}}
- 시그널이 없으면: {{"signals": []}}
- 불확실하면: 생성하지 말 것 (빈 배열이 낫다)
"""


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_signal_strict(signal: dict, context: dict) -> Tuple[bool, list[str]]:
    """
    Strict validation of signal against enhanced schema.

    Args:
        signal: Signal dict to validate
        context: Context dict with corp_name etc.

    Returns:
        tuple of (is_valid, list of error messages)
    """
    errors = []

    # Required fields
    required = [
        "signal_type", "event_type", "impact_direction",
        "impact_strength", "confidence", "retrieval_confidence",
        "title", "summary", "evidence"
    ]

    for field in required:
        if not signal.get(field):
            errors.append(f"Missing required field: {field}")

    # Evidence check
    evidence = signal.get("evidence", [])
    if not evidence:
        errors.append("No evidence provided")

    # retrieval_confidence check
    rc = signal.get("retrieval_confidence")
    if rc and rc not in {"VERBATIM", "PARAPHRASED", "INFERRED"}:
        errors.append(f"Invalid retrieval_confidence: {rc}")

    if rc == "INFERRED" and not signal.get("confidence_reason"):
        errors.append("INFERRED requires confidence_reason")

    # Forbidden patterns check
    title = signal.get("title", "")
    summary = signal.get("summary", "")

    forbidden_in_title = check_forbidden_patterns(title)
    forbidden_in_summary = check_forbidden_patterns(summary)

    if forbidden_in_title:
        patterns = [f["pattern"] for f in forbidden_in_title]
        errors.append(f"Forbidden patterns in title: {patterns}")
    if forbidden_in_summary:
        patterns = [f["pattern"] for f in forbidden_in_summary]
        errors.append(f"Forbidden patterns in summary: {patterns}")

    # Corp name check
    corp_name = context.get("corp_name", "")
    if corp_name:
        if corp_name not in title and corp_name not in summary:
            errors.append(f"Corp name '{corp_name}' not in title or summary")

    # Length check
    if len(title) > 50:
        errors.append(f"Title too long: {len(title)} > 50")
    if len(summary) > 300:
        errors.append(f"Summary too long: {len(summary)} > 300")

    return len(errors) == 0, errors


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Constants
    "V2_CORE_PRINCIPLES",
    "STRICT_JSON_SCHEMA",
    "CHAIN_OF_VERIFICATION",
    # Personas
    "RISK_MANAGER_PERSONA",
    "IB_MANAGER_PERSONA",
    # Examples
    "DIRECT_EXAMPLES",
    "INDUSTRY_EXAMPLES",
    "ENVIRONMENT_EXAMPLES",
    "REJECTION_EXAMPLES",
    # Patterns
    "ALL_FORBIDDEN_LITERALS",
    "COMPILED_FORBIDDEN_LITERALS",
    "COMPILED_REGEX_FORBIDDEN",
    "ForbiddenCategory",
    # Functions
    "build_enhanced_system_prompt",
    "build_enhanced_user_prompt",
    "check_forbidden_patterns",
    "validate_signal_strict",
]
