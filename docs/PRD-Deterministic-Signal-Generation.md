# PRD: Deterministic Signal Generation (Two-Pass Architecture)

**문서 버전**: v1.0
**작성일**: 2026-02-08
**작성자**: Silicon Valley Senior Engineer
**검토자**: Elon Musk (First Principles), JP Morgan CEO (금융 품질)
**상태**: Draft

---

## 1. Executive Summary

### 1.1 문제 정의

현재 rKYC 시그널 생성 시스템은 LLM에게 **추출, 판단, 생성**을 모두 위임합니다.
이로 인해 두 가지 상충하는 문제가 발생합니다:

| 문제 | 원인 | 영향 |
|------|------|------|
| **Hallucination** | LLM이 없는 정보 생성 | 허위 시그널로 잘못된 의사결정 유도 |
| **Under-Detection** | Hallucination 방지 위해 보수적 프롬프트 | 실제 리스크 누락 |

**근본 원인**: LLM에게 "판단"을 맡기는 것 자체가 문제입니다.

### 1.2 해결책 요약

**Two-Pass Architecture**:
- **Pass 1 (LLM)**: 데이터에서 "사실(Fact)"만 추출 - 판단 금지
- **Pass 2 (Rule Engine)**: 추출된 사실로 시그널 생성 여부를 결정론적으로 결정

```
현재:  Data → LLM(추출+판단+생성) → Signal (불확실)
제안:  Data → LLM(추출) → Facts → Rule Engine(판단+생성) → Signal (결정론적)
```

### 1.3 기대 효과

| 지표 | 현재 | 목표 | 개선율 |
|------|------|------|--------|
| Hallucination Rate | ~5% | <0.1% | 98% 감소 |
| Signal Consistency | ~70% | >99% | 41% 개선 |
| 테스트 가능성 | 없음 | 100% 규칙 테스트 | - |
| LLM 비용 | $0.15/기업 | $0.05/기업 | 67% 절감 |
| 설명 가능성 | 없음 | 규칙 ID로 추적 | - |

---

## 2. 제1원칙 분석

### 2.1 기존 가정 검증

| 가정 | 검증 결과 | 결론 |
|------|----------|------|
| "LLM이 관련성을 잘 판단한다" | ❌ 그럴듯하게 보이는 것 생성 | 코드가 판단해야 함 |
| "Few-Shot 예시가 필요하다" | ❌ 숫자 복사, 플레이스홀더 출력 | JSON Schema로 대체 |
| "Confidence를 LLM이 결정해야 한다" | ❌ 항상 자신만만 | 출처 기반 코드 계산 |
| "프롬프트 개선으로 해결 가능하다" | ❌ 본질적 한계 존재 | 아키텍처 변경 필요 |

### 2.2 LLM의 적합한 역할

| 작업 | LLM 적합성 | 이유 |
|------|-----------|------|
| 패턴 인식/추출 | ✅ 적합 | 다양한 형식의 텍스트에서 정보 추출 |
| 관련성 판단 | ❌ 부적합 | 일관성 없음, 검증 불가 |
| 영향도 평가 | ❌ 부적합 | 도메인 지식 불확실 |
| 텍스트 생성 | ⚠️ 조건부 | 템플릿 기반으로 제한 시 가능 |

---

## 3. 시스템 아키텍처

### 3.1 전체 흐름

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Two-Pass Architecture                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  Input   │    │   Pass 1     │    │   Fact       │              │
│  │  Data    │───▶│   LLM        │───▶│   Store      │              │
│  │          │    │  (Extract)   │    │              │              │
│  └──────────┘    └──────────────┘    └──────┬───────┘              │
│       │                                      │                      │
│       │          ┌──────────────┐           │                      │
│       │          │   Fact       │           │                      │
│       └─────────▶│  Validator   │◀──────────┘                      │
│                  │              │                                   │
│                  └──────┬───────┘                                   │
│                         │                                           │
│                         ▼                                           │
│                  ┌──────────────┐    ┌──────────────┐              │
│                  │   Pass 2     │    │   Signal     │              │
│                  │   Rule       │───▶│   Output     │              │
│                  │   Engine     │    │              │              │
│                  └──────────────┘    └──────────────┘              │
│                         │                                           │
│                         ▼                                           │
│                  ┌──────────────┐                                   │
│                  │   LLM        │  (규칙 미매칭 시에만)              │
│                  │   Fallback   │                                   │
│                  └──────────────┘                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 컴포넌트 설명

| 컴포넌트 | 역할 | 기술 |
|----------|------|------|
| **Pass 1: LLM Extractor** | 데이터에서 사실만 추출 | Claude/GPT + JSON Schema |
| **Fact Validator** | 추출된 사실이 원본에 있는지 검증 | Python 정규식/문자열 매칭 |
| **Pass 2: Rule Engine** | 사실 → 시그널 변환 규칙 | Python 규칙 엔진 |
| **Summary Generator** | 템플릿 기반 Summary 생성 | Python 문자열 포맷 |
| **LLM Fallback** | 규칙 미매칭 사실 처리 | Claude/GPT (LOW confidence) |

---

## 4. Pass 1: Fact Extraction

### 4.1 Fact 타입 정의

```python
class FactType(Enum):
    # Internal Snapshot Facts
    OVERDUE_STATUS = "overdue_status"           # 연체 상태
    GRADE_CHANGE = "grade_change"               # 등급 변동
    EXPOSURE_CHANGE = "exposure_change"         # 여신 변동
    COLLATERAL_CHANGE = "collateral_change"     # 담보 변동

    # Document Facts
    SHAREHOLDER_CHANGE = "shareholder_change"   # 주주 변경
    OFFICER_CHANGE = "officer_change"           # 임원 변경
    FINANCIAL_CHANGE = "financial_change"       # 재무 변동

    # External Event Facts
    COMPANY_NEWS = "company_news"               # 기업 직접 뉴스
    INDUSTRY_NEWS = "industry_news"             # 산업 뉴스
    POLICY_NEWS = "policy_news"                 # 정책/규제 뉴스

    # Unclassified (LLM Fallback 대상)
    UNCLASSIFIED = "unclassified"
```

### 4.2 Fact 스키마

```python
@dataclass
class ExtractedFact:
    """LLM이 추출한 사실 단위"""

    fact_id: str                    # 고유 ID
    fact_type: FactType             # 사실 유형

    # 핵심 데이터
    subject: str                    # 주체 (기업명, 산업명 등)
    predicate: str                  # 서술 (변동, 발생, 발표 등)
    object_value: Any               # 값 (숫자, 문자열, bool 등)

    # 변화 정보 (해당 시)
    previous_value: Optional[Any]   # 이전 값
    change_direction: Optional[str] # INCREASE, DECREASE, NEW, REMOVED
    change_magnitude: Optional[float]  # 변화율 (%)

    # 출처
    source_type: str                # SNAPSHOT, DOCUMENT, EXTERNAL
    source_ref: str                 # keypath, doc_page, URL
    source_snippet: str             # 원문 발췌 (100자 이내)

    # 메타데이터
    extracted_at: datetime
    extraction_confidence: float    # LLM 추출 신뢰도 (내부용)
```

### 4.3 Extraction 프롬프트

```python
FACT_EXTRACTION_SYSTEM = """당신은 데이터 추출 전문가입니다.
주어진 데이터에서 "사실(Fact)"만 추출합니다.

## 핵심 규칙

### 1. 판단 금지
- "리스크", "기회", "영향" 등 판단 표현 사용 금지
- 오직 "무엇이 어떻게 되었다"만 추출

### 2. 숫자 정확성
- 원본에 있는 숫자만 추출
- 단위 변환 시 원본 값도 함께 기록
- 추정/계산 금지

### 3. 출처 필수
- 모든 Fact에 source_ref 필수
- source_snippet은 원본에서 복사

### 4. 분류
- fact_type은 제공된 유형 중 선택
- 해당 없으면 "unclassified"

## 출력 형식
```json
{
  "facts": [
    {
      "fact_type": "overdue_status",
      "subject": "엠케이전자",
      "predicate": "연체 발생",
      "object_value": true,
      "previous_value": false,
      "change_direction": "NEW",
      "source_type": "SNAPSHOT",
      "source_ref": "/credit/loan_summary/overdue_flag",
      "source_snippet": "overdue_flag: true, overdue_days: 32"
    }
  ]
}
```
"""

FACT_EXTRACTION_USER = """# 분석 대상
- 기업명: {corp_name}
- 업종: {industry_name}

# 데이터 소스

## 1. 내부 스냅샷
```json
{snapshot_json}
```

## 2. 이전 스냅샷 (비교용)
```json
{prev_snapshot_json}
```

## 3. 외부 이벤트
```json
{external_events}
```

# 요청
위 데이터에서 사실(Fact)만 추출하세요.
- 변화가 없는 항목은 추출 불필요
- 판단/평가 표현 금지
- 숫자는 원본 그대로
"""
```

### 4.4 JSON Schema 강제

```python
FACT_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fact_type": {
                        "type": "string",
                        "enum": [
                            "overdue_status", "grade_change", "exposure_change",
                            "collateral_change", "shareholder_change", "officer_change",
                            "financial_change", "company_news", "industry_news",
                            "policy_news", "unclassified"
                        ]
                    },
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"},
                    "object_value": {},  # any type
                    "previous_value": {},
                    "change_direction": {
                        "type": "string",
                        "enum": ["INCREASE", "DECREASE", "NEW", "REMOVED", "UNCHANGED"]
                    },
                    "change_magnitude": {"type": "number"},
                    "source_type": {
                        "type": "string",
                        "enum": ["SNAPSHOT", "DOCUMENT", "EXTERNAL"]
                    },
                    "source_ref": {"type": "string"},
                    "source_snippet": {"type": "string", "maxLength": 150}
                },
                "required": ["fact_type", "subject", "predicate", "source_type", "source_ref"]
            }
        }
    },
    "required": ["facts"]
}
```

---

## 5. Fact Validator

### 5.1 검증 규칙

```python
class FactValidator:
    """추출된 Fact가 원본 데이터에 실제로 존재하는지 검증"""

    def validate(self, fact: ExtractedFact, source_data: dict) -> ValidationResult:
        """
        Returns:
            ValidationResult with:
            - is_valid: bool
            - confidence_adjustment: float (-1.0 to 0.0)
            - rejection_reason: Optional[str]
        """
        checks = [
            self._check_source_exists(fact, source_data),
            self._check_number_exists(fact, source_data),
            self._check_snippet_exists(fact, source_data),
        ]

        failed = [c for c in checks if not c.passed]

        if any(c.severity == "CRITICAL" for c in failed):
            return ValidationResult(is_valid=False, reason=failed[0].message)

        confidence_penalty = sum(c.penalty for c in failed)
        return ValidationResult(
            is_valid=True,
            confidence_adjustment=confidence_penalty
        )

    def _check_number_exists(self, fact: ExtractedFact, source_data: dict) -> CheckResult:
        """Fact의 숫자가 원본에 있는지 확인"""
        if fact.object_value is None:
            return CheckResult(passed=True)

        # 숫자 추출
        numbers_in_fact = self._extract_numbers(str(fact.object_value))
        if not numbers_in_fact:
            return CheckResult(passed=True)

        # 원본 데이터 문자열화
        source_str = json.dumps(source_data, ensure_ascii=False)

        for num in numbers_in_fact:
            if str(num) not in source_str:
                # 비율로 변환해서 재확인 (100 → 100%, 0.5 → 50%)
                if f"{num}%" not in source_str and f"{num*100}%" not in source_str:
                    return CheckResult(
                        passed=False,
                        severity="CRITICAL",
                        message=f"Number {num} not found in source data",
                        penalty=-1.0
                    )

        return CheckResult(passed=True)

    def _check_snippet_exists(self, fact: ExtractedFact, source_data: dict) -> CheckResult:
        """source_snippet이 원본에서 발췌된 것인지 확인"""
        if not fact.source_snippet:
            return CheckResult(passed=True)

        source_str = json.dumps(source_data, ensure_ascii=False)

        # 공백 정규화 후 비교
        normalized_snippet = " ".join(fact.source_snippet.split())
        normalized_source = " ".join(source_str.split())

        # 80% 이상 매칭
        if self._fuzzy_match(normalized_snippet, normalized_source) < 0.8:
            return CheckResult(
                passed=False,
                severity="WARNING",
                message="Snippet not found in source (fuzzy match < 80%)",
                penalty=-0.3
            )

        return CheckResult(passed=True)
```

### 5.2 검증 결과 처리

| 검증 결과 | 처리 |
|----------|------|
| ✅ 모든 검증 통과 | Rule Engine으로 전달 |
| ⚠️ WARNING 있음 | 전달하되 confidence 하향 |
| ❌ CRITICAL 실패 | Fact 폐기, 로그 기록 |

---

## 6. Pass 2: Rule Engine

### 6.1 규칙 구조

```python
@dataclass
class SignalRule:
    """시그널 생성 규칙"""

    rule_id: str                    # 규칙 고유 ID (예: "RULE_OVERDUE_001")
    rule_name: str                  # 사람이 읽을 수 있는 이름

    # 매칭 조건
    fact_type: FactType             # 대상 Fact 유형
    conditions: list[Condition]     # 추가 조건들 (AND)

    # 시그널 생성 정보
    signal_type: str                # DIRECT, INDUSTRY, ENVIRONMENT
    event_type: str                 # 10종 중 하나
    impact_direction: str | Callable  # RISK, OPPORTUNITY, NEUTRAL 또는 함수
    impact_strength: str | Callable   # HIGH, MED, LOW 또는 함수

    # 우선순위 (낮을수록 우선)
    priority: int = 100

    # 활성화 여부
    enabled: bool = True


@dataclass
class Condition:
    """규칙 조건"""
    field: str                      # Fact 필드명
    operator: str                   # eq, ne, gt, lt, gte, lte, in, contains
    value: Any                      # 비교 값
```

### 6.2 기본 규칙 정의

```python
# rules/direct_rules.py

DIRECT_RULES = [
    # =========================================================================
    # OVERDUE_FLAG_ON: 연체 발생
    # =========================================================================
    SignalRule(
        rule_id="DIRECT_OVERDUE_001",
        rule_name="30일 이상 연체 발생",
        fact_type=FactType.OVERDUE_STATUS,
        conditions=[
            Condition("object_value", "eq", True),
            Condition("change_direction", "eq", "NEW"),
        ],
        signal_type="DIRECT",
        event_type="OVERDUE_FLAG_ON",
        impact_direction="RISK",
        impact_strength=lambda fact: "HIGH" if fact.get("overdue_days", 0) >= 30 else "MED",
        priority=10,
    ),

    # =========================================================================
    # INTERNAL_RISK_GRADE_CHANGE: 등급 변동
    # =========================================================================
    SignalRule(
        rule_id="DIRECT_GRADE_DOWN_001",
        rule_name="내부등급 하락",
        fact_type=FactType.GRADE_CHANGE,
        conditions=[
            Condition("change_direction", "eq", "DECREASE"),
        ],
        signal_type="DIRECT",
        event_type="INTERNAL_RISK_GRADE_CHANGE",
        impact_direction="RISK",
        impact_strength=lambda fact: "HIGH" if abs(fact.get("change_magnitude", 0)) >= 2 else "MED",
        priority=10,
    ),

    SignalRule(
        rule_id="DIRECT_GRADE_UP_001",
        rule_name="내부등급 상승",
        fact_type=FactType.GRADE_CHANGE,
        conditions=[
            Condition("change_direction", "eq", "INCREASE"),
        ],
        signal_type="DIRECT",
        event_type="INTERNAL_RISK_GRADE_CHANGE",
        impact_direction="OPPORTUNITY",
        impact_strength=lambda fact: "HIGH" if abs(fact.get("change_magnitude", 0)) >= 2 else "MED",
        priority=10,
    ),

    # =========================================================================
    # LOAN_EXPOSURE_CHANGE: 여신 변동
    # =========================================================================
    SignalRule(
        rule_id="DIRECT_EXPOSURE_UP_001",
        rule_name="여신 증가 (10% 이상)",
        fact_type=FactType.EXPOSURE_CHANGE,
        conditions=[
            Condition("change_direction", "eq", "INCREASE"),
            Condition("change_magnitude", "gte", 10),
        ],
        signal_type="DIRECT",
        event_type="LOAN_EXPOSURE_CHANGE",
        impact_direction="NEUTRAL",  # 여신 증가는 기회일 수도, 리스크일 수도
        impact_strength=lambda fact: "HIGH" if fact.get("change_magnitude", 0) >= 30 else "MED",
        priority=20,
    ),

    SignalRule(
        rule_id="DIRECT_EXPOSURE_DOWN_001",
        rule_name="여신 감소 (10% 이상)",
        fact_type=FactType.EXPOSURE_CHANGE,
        conditions=[
            Condition("change_direction", "eq", "DECREASE"),
            Condition("change_magnitude", "gte", 10),
        ],
        signal_type="DIRECT",
        event_type="LOAN_EXPOSURE_CHANGE",
        impact_direction="NEUTRAL",
        impact_strength=lambda fact: "HIGH" if fact.get("change_magnitude", 0) >= 30 else "MED",
        priority=20,
    ),

    # =========================================================================
    # GOVERNANCE_CHANGE: 임원 변경
    # =========================================================================
    SignalRule(
        rule_id="DIRECT_CEO_CHANGE_001",
        rule_name="대표이사 변경",
        fact_type=FactType.OFFICER_CHANGE,
        conditions=[
            Condition("object_value.position", "contains", "대표"),
        ],
        signal_type="DIRECT",
        event_type="GOVERNANCE_CHANGE",
        impact_direction="NEUTRAL",  # 긍정/부정 불명확
        impact_strength="MED",
        priority=30,
    ),

    # =========================================================================
    # OWNERSHIP_CHANGE: 주주 변경
    # =========================================================================
    SignalRule(
        rule_id="DIRECT_MAJOR_SHAREHOLDER_001",
        rule_name="주요주주 변경",
        fact_type=FactType.SHAREHOLDER_CHANGE,
        conditions=[
            Condition("change_magnitude", "gte", 5),  # 지분 5% 이상 변동
        ],
        signal_type="DIRECT",
        event_type="OWNERSHIP_CHANGE",
        impact_direction="NEUTRAL",
        impact_strength=lambda fact: "HIGH" if fact.get("change_magnitude", 0) >= 10 else "MED",
        priority=30,
    ),

    # =========================================================================
    # FINANCIAL_STATEMENT_UPDATE: 재무 변동
    # =========================================================================
    SignalRule(
        rule_id="DIRECT_REVENUE_DROP_001",
        rule_name="매출 급감 (20% 이상)",
        fact_type=FactType.FINANCIAL_CHANGE,
        conditions=[
            Condition("object_value.field", "eq", "revenue"),
            Condition("change_direction", "eq", "DECREASE"),
            Condition("change_magnitude", "gte", 20),
        ],
        signal_type="DIRECT",
        event_type="FINANCIAL_STATEMENT_UPDATE",
        impact_direction="RISK",
        impact_strength="HIGH",
        priority=10,
    ),

    SignalRule(
        rule_id="DIRECT_REVENUE_SURGE_001",
        rule_name="매출 급증 (20% 이상)",
        fact_type=FactType.FINANCIAL_CHANGE,
        conditions=[
            Condition("object_value.field", "eq", "revenue"),
            Condition("change_direction", "eq", "INCREASE"),
            Condition("change_magnitude", "gte", 20),
        ],
        signal_type="DIRECT",
        event_type="FINANCIAL_STATEMENT_UPDATE",
        impact_direction="OPPORTUNITY",
        impact_strength="HIGH",
        priority=10,
    ),

    SignalRule(
        rule_id="DIRECT_OPERATING_LOSS_001",
        rule_name="영업이익 적자 전환",
        fact_type=FactType.FINANCIAL_CHANGE,
        conditions=[
            Condition("object_value.field", "eq", "operating_income"),
            Condition("previous_value", "gt", 0),
            Condition("object_value.value", "lt", 0),
        ],
        signal_type="DIRECT",
        event_type="FINANCIAL_STATEMENT_UPDATE",
        impact_direction="RISK",
        impact_strength="HIGH",
        priority=5,
    ),
]
```

```python
# rules/industry_rules.py

INDUSTRY_RULES = [
    # =========================================================================
    # INDUSTRY_SHOCK: 산업 이벤트
    # =========================================================================
    SignalRule(
        rule_id="INDUSTRY_NEGATIVE_001",
        rule_name="산업 부정적 뉴스",
        fact_type=FactType.INDUSTRY_NEWS,
        conditions=[
            Condition("object_value.sentiment", "in", ["negative", "부정", "하락", "위기"]),
        ],
        signal_type="INDUSTRY",
        event_type="INDUSTRY_SHOCK",
        impact_direction="RISK",
        impact_strength="MED",
        priority=50,
        # 추가 조건: Corp Profile 기반 관련성 확인 (런타임)
    ),

    SignalRule(
        rule_id="INDUSTRY_POSITIVE_001",
        rule_name="산업 긍정적 뉴스",
        fact_type=FactType.INDUSTRY_NEWS,
        conditions=[
            Condition("object_value.sentiment", "in", ["positive", "긍정", "상승", "성장"]),
        ],
        signal_type="INDUSTRY",
        event_type="INDUSTRY_SHOCK",
        impact_direction="OPPORTUNITY",
        impact_strength="MED",
        priority=50,
    ),
]
```

```python
# rules/environment_rules.py

ENVIRONMENT_RULES = [
    # =========================================================================
    # POLICY_REGULATION_CHANGE: 정책/규제
    # =========================================================================
    SignalRule(
        rule_id="ENV_POLICY_REGULATION_001",
        rule_name="정책/규제 발표",
        fact_type=FactType.POLICY_NEWS,
        conditions=[],  # 기본 조건 없음, Corp Profile 기반 필터링
        signal_type="ENVIRONMENT",
        event_type="POLICY_REGULATION_CHANGE",
        impact_direction=lambda fact: _determine_policy_impact(fact),
        impact_strength="MED",
        priority=50,
    ),
]

def _determine_policy_impact(fact: dict) -> str:
    """정책 영향 방향 결정"""
    keywords_risk = ["규제 강화", "세금 인상", "수출 제한", "금지"]
    keywords_opp = ["규제 완화", "지원 확대", "세금 감면", "인센티브"]

    text = str(fact.get("object_value", ""))

    if any(kw in text for kw in keywords_risk):
        return "RISK"
    elif any(kw in text for kw in keywords_opp):
        return "OPPORTUNITY"
    else:
        return "NEUTRAL"
```

### 6.3 Rule Engine 구현

```python
# rule_engine.py

class RuleEngine:
    """결정론적 시그널 생성 엔진"""

    def __init__(self):
        self.rules: list[SignalRule] = []
        self._load_rules()

    def _load_rules(self):
        """모든 규칙 로드"""
        from rules.direct_rules import DIRECT_RULES
        from rules.industry_rules import INDUSTRY_RULES
        from rules.environment_rules import ENVIRONMENT_RULES

        self.rules = DIRECT_RULES + INDUSTRY_RULES + ENVIRONMENT_RULES
        self.rules.sort(key=lambda r: r.priority)

    def process(
        self,
        facts: list[ExtractedFact],
        corp_profile: dict
    ) -> tuple[list[dict], list[ExtractedFact]]:
        """
        Facts를 시그널로 변환

        Returns:
            (생성된 시그널 목록, 규칙 미매칭 Fact 목록)
        """
        signals = []
        unmatched_facts = []
        processed_fact_ids = set()

        for fact in facts:
            matched = False

            for rule in self.rules:
                if not rule.enabled:
                    continue

                if self._matches(rule, fact, corp_profile):
                    signal = self._create_signal(rule, fact, corp_profile)
                    signals.append(signal)
                    processed_fact_ids.add(fact.fact_id)
                    matched = True
                    break  # 첫 번째 매칭 규칙만 적용

            if not matched:
                unmatched_facts.append(fact)

        return signals, unmatched_facts

    def _matches(
        self,
        rule: SignalRule,
        fact: ExtractedFact,
        corp_profile: dict
    ) -> bool:
        """규칙이 Fact에 매칭되는지 확인"""

        # 1. Fact 타입 확인
        if rule.fact_type != fact.fact_type:
            return False

        # 2. 조건 확인
        for cond in rule.conditions:
            if not self._check_condition(cond, fact):
                return False

        # 3. INDUSTRY/ENVIRONMENT는 Corp Profile 관련성 확인
        if rule.signal_type in ["INDUSTRY", "ENVIRONMENT"]:
            if not self._check_corp_relevance(rule, fact, corp_profile):
                return False

        return True

    def _check_corp_relevance(
        self,
        rule: SignalRule,
        fact: ExtractedFact,
        corp_profile: dict
    ) -> bool:
        """Corp Profile 기반 관련성 확인"""

        if rule.signal_type == "INDUSTRY":
            # 산업 코드 매칭
            fact_industries = fact.object_value.get("affected_industries", [])
            corp_industry = corp_profile.get("industry_code", "")

            if fact_industries and corp_industry:
                return corp_industry in fact_industries or \
                       corp_industry[:2] in [i[:2] for i in fact_industries]

            # 산업명 텍스트 매칭
            fact_text = str(fact.object_value).lower()
            corp_industry_name = corp_profile.get("industry_name", "").lower()

            return corp_industry_name in fact_text

        elif rule.signal_type == "ENVIRONMENT":
            # 환경 이벤트는 Corp Profile 특성 기반 필터링
            return self._check_environment_relevance(fact, corp_profile)

        return True

    def _check_environment_relevance(
        self,
        fact: ExtractedFact,
        corp_profile: dict
    ) -> bool:
        """ENVIRONMENT 이벤트의 기업 관련성 확인"""

        fact_text = str(fact.object_value).lower()

        # 수출 관련 → 수출 비중 30% 이상 기업
        if any(kw in fact_text for kw in ["수출", "관세", "무역", "환율"]):
            export_ratio = corp_profile.get("export_ratio_pct", 0)
            if export_ratio < 30:
                return False

        # 국가 관련 → 해당 국가 노출 기업
        country_keywords = {
            "중국": ["중국", "china", "베이징", "상하이"],
            "미국": ["미국", "usa", "us", "워싱턴", "뉴욕"],
            "EU": ["유럽", "eu", "브뤼셀", "독일", "프랑스"],
        }

        for country, keywords in country_keywords.items():
            if any(kw in fact_text for kw in keywords):
                country_exposure = corp_profile.get("country_exposure", [])
                if not any(country.lower() in str(c).lower() for c in country_exposure):
                    return False

        return True

    def _create_signal(
        self,
        rule: SignalRule,
        fact: ExtractedFact,
        corp_profile: dict
    ) -> dict:
        """규칙과 Fact로 시그널 생성"""

        # impact_direction/strength 계산
        if callable(rule.impact_direction):
            impact_direction = rule.impact_direction(fact.__dict__)
        else:
            impact_direction = rule.impact_direction

        if callable(rule.impact_strength):
            impact_strength = rule.impact_strength(fact.__dict__)
        else:
            impact_strength = rule.impact_strength

        # Confidence 계산 (출처 기반)
        confidence = self._calculate_confidence(fact)

        # Summary 생성 (템플릿)
        summary = self._generate_summary(rule, fact, corp_profile)

        return {
            "signal_type": rule.signal_type,
            "event_type": rule.event_type,
            "impact_direction": impact_direction,
            "impact_strength": impact_strength,
            "confidence": confidence,
            "title": self._generate_title(rule, fact, corp_profile),
            "summary": summary,
            "evidence": [{
                "evidence_type": self._map_source_type(fact.source_type),
                "ref_type": self._map_ref_type(fact.source_type),
                "ref_value": fact.source_ref,
                "snippet": fact.source_snippet,
            }],
            "rule_id": rule.rule_id,
            "fact_id": fact.fact_id,
        }

    def _calculate_confidence(self, fact: ExtractedFact) -> str:
        """출처 기반 Confidence 계산"""

        TIER1_DOMAINS = [
            "dart.fss.or.kr", "fss.or.kr", "bok.or.kr",
            "kostat.go.kr", "kosis.kr"
        ]
        TIER2_DOMAINS = [
            "hankyung.com", "mk.co.kr", "chosun.com",
            "sedaily.com", "edaily.co.kr"
        ]

        if fact.source_type == "SNAPSHOT":
            return "HIGH"  # 내부 데이터는 항상 HIGH

        if fact.source_type == "DOCUMENT":
            return "HIGH"  # 제출 문서는 항상 HIGH

        # EXTERNAL
        source_url = fact.source_ref.lower()

        if any(domain in source_url for domain in TIER1_DOMAINS):
            return "HIGH"
        elif any(domain in source_url for domain in TIER2_DOMAINS):
            return "MED"
        else:
            return "LOW"
```

### 6.4 Confidence 계산 규칙

| 출처 유형 | Confidence | 근거 |
|----------|------------|------|
| 내부 스냅샷 | HIGH | 1차 자료, 검증된 데이터 |
| 제출 문서 | HIGH | 고객 제출, 공증 가능 |
| DART 공시 | HIGH | 법적 의무 공시 |
| 정부 발표 | HIGH | 공식 정보 |
| 주요 경제지 | MED | 신뢰도 높은 언론 |
| 일반 뉴스 | LOW | 단일 출처 |
| 출처 불명 | LOW | 검증 불가 |

---

## 7. Summary Generator

### 7.1 템플릿 정의

```python
# templates/summary_templates.py

SUMMARY_TEMPLATES = {
    # =========================================================================
    # DIRECT 시그널
    # =========================================================================
    "OVERDUE_FLAG_ON": {
        "RISK": "{corp_name}의 기업여신에서 {overdue_days}일 연체가 확인됨. 담보 상태 점검 및 상환 계획 확인 권고.",
    },

    "INTERNAL_RISK_GRADE_CHANGE": {
        "RISK": "{corp_name}의 내부신용등급이 {prev_grade}에서 {curr_grade}로 하락함. 여신 조건 재검토 대상.",
        "OPPORTUNITY": "{corp_name}의 내부신용등급이 {prev_grade}에서 {curr_grade}로 상승함. 여신 확대 검토 가능.",
    },

    "LOAN_EXPOSURE_CHANGE": {
        "NEUTRAL": "{corp_name}의 여신 노출이 {change_direction} {change_pct}% 변동함. 포트폴리오 리밸런싱 검토 권고.",
    },

    "GOVERNANCE_CHANGE": {
        "NEUTRAL": "{corp_name}의 {officer_position} {officer_name}이(가) 변경됨. 경영 연속성 모니터링 권고.",
    },

    "OWNERSHIP_CHANGE": {
        "NEUTRAL": "{corp_name}의 주주구조 변동 확인. {shareholder_name} 지분 {change_pct}% 변동. 지배구조 변화 모니터링 권고.",
    },

    "FINANCIAL_STATEMENT_UPDATE": {
        "RISK": "{corp_name}의 {financial_field}이(가) 전기 대비 {change_pct}% 감소함. 재무 건전성 점검 권고.",
        "OPPORTUNITY": "{corp_name}의 {financial_field}이(가) 전기 대비 {change_pct}% 증가함. 성장 추세 확인.",
    },

    # =========================================================================
    # INDUSTRY 시그널
    # =========================================================================
    "INDUSTRY_SHOCK": {
        "RISK": "{industry_name} 업종에서 {event_summary}. {corp_name}은 해당 업종으로 영향 모니터링 권고.",
        "OPPORTUNITY": "{industry_name} 업종에서 {event_summary}. {corp_name}은 해당 업종으로 수혜 가능성 검토.",
        "NEUTRAL": "{industry_name} 업종에서 {event_summary}. {corp_name}에 대한 영향은 추가 확인 필요.",
    },

    # =========================================================================
    # ENVIRONMENT 시그널
    # =========================================================================
    "POLICY_REGULATION_CHANGE": {
        "RISK": "{policy_name} 시행으로 {affected_area} 관련 규제 강화. {corp_name}은 {relevance_reason}으로 영향 가능성 있음.",
        "OPPORTUNITY": "{policy_name} 발표로 {affected_area} 지원 확대. {corp_name}은 {relevance_reason}으로 수혜 가능성 있음.",
        "NEUTRAL": "{policy_name} 관련 동향 확인. {corp_name}에 대한 영향은 {relevance_reason} 기반 모니터링 권고.",
    },
}
```

### 7.2 Summary Generator 구현

```python
# summary_generator.py

class SummaryGenerator:
    """템플릿 기반 Summary 생성기"""

    def __init__(self):
        self.templates = SUMMARY_TEMPLATES

    def generate(
        self,
        signal: dict,
        fact: ExtractedFact,
        corp_profile: dict
    ) -> str:
        """시그널 Summary 생성"""

        event_type = signal["event_type"]
        impact_direction = signal["impact_direction"]

        # 템플릿 조회
        event_templates = self.templates.get(event_type, {})
        template = event_templates.get(impact_direction)

        if not template:
            # Fallback: 기본 템플릿
            return self._generate_fallback_summary(signal, fact, corp_profile)

        # 템플릿 변수 준비
        variables = self._prepare_variables(signal, fact, corp_profile)

        # 템플릿 렌더링
        try:
            return template.format(**variables)
        except KeyError as e:
            # 누락된 변수는 빈 문자열로 대체
            return self._safe_format(template, variables)

    def _prepare_variables(
        self,
        signal: dict,
        fact: ExtractedFact,
        corp_profile: dict
    ) -> dict:
        """템플릿 변수 준비"""

        variables = {
            "corp_name": corp_profile.get("corp_name", "해당 기업"),
            "industry_name": corp_profile.get("industry_name", "해당 업종"),
            "industry_code": corp_profile.get("industry_code", ""),
        }

        # Fact에서 변수 추출
        if fact.object_value:
            if isinstance(fact.object_value, dict):
                variables.update(fact.object_value)
            else:
                variables["object_value"] = fact.object_value

        if fact.previous_value:
            variables["previous_value"] = fact.previous_value
            variables["prev_value"] = fact.previous_value

        if fact.change_magnitude:
            variables["change_pct"] = round(abs(fact.change_magnitude), 1)
            variables["change_magnitude"] = round(abs(fact.change_magnitude), 1)

        if fact.change_direction:
            direction_map = {
                "INCREASE": "증가",
                "DECREASE": "감소",
                "NEW": "신규 발생",
                "REMOVED": "해소",
            }
            variables["change_direction"] = direction_map.get(
                fact.change_direction, fact.change_direction
            )

        # 이벤트 요약 (외부 뉴스용)
        if fact.source_snippet:
            variables["event_summary"] = fact.source_snippet[:100]

        return variables

    def _safe_format(self, template: str, variables: dict) -> str:
        """누락된 변수를 안전하게 처리하는 format"""
        import re

        # {variable} 패턴 찾기
        pattern = r'\{(\w+)\}'

        def replacer(match):
            key = match.group(1)
            return str(variables.get(key, f"[{key}]"))

        return re.sub(pattern, replacer, template)

    def _generate_fallback_summary(
        self,
        signal: dict,
        fact: ExtractedFact,
        corp_profile: dict
    ) -> str:
        """템플릿 없을 때 기본 Summary"""

        corp_name = corp_profile.get("corp_name", "해당 기업")
        event_type = signal["event_type"]

        return f"{corp_name} 관련 {event_type} 이벤트 확인. 상세 내용 검토 권고."
```

### 7.3 Title Generator

```python
TITLE_TEMPLATES = {
    "OVERDUE_FLAG_ON": "{corp_name} 연체 발생",
    "INTERNAL_RISK_GRADE_CHANGE": "{corp_name} 내부등급 {direction}",
    "LOAN_EXPOSURE_CHANGE": "{corp_name} 여신 {change_pct}% 변동",
    "COLLATERAL_CHANGE": "{corp_name} 담보 변동",
    "OWNERSHIP_CHANGE": "{corp_name} 주주구조 변경",
    "GOVERNANCE_CHANGE": "{corp_name} {officer_position} 변경",
    "FINANCIAL_STATEMENT_UPDATE": "{corp_name} 재무 {direction}",
    "KYC_REFRESH": "{corp_name} KYC 갱신 필요",
    "INDUSTRY_SHOCK": "{industry_name} {event_keyword}",
    "POLICY_REGULATION_CHANGE": "{policy_keyword} 정책 변화",
}
```

---

## 8. LLM Fallback

### 8.1 Fallback 조건

규칙 엔진에서 매칭되지 않은 Fact는 LLM Fallback으로 처리:

```python
class LLMFallback:
    """규칙 미매칭 Fact 처리"""

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    def process(
        self,
        unmatched_facts: list[ExtractedFact],
        corp_profile: dict
    ) -> list[dict]:
        """
        규칙 미매칭 Fact를 LLM으로 처리

        주의: 모든 Fallback 시그널은 confidence=LOW
        """

        if not unmatched_facts:
            return []

        signals = []

        for fact in unmatched_facts:
            signal = self._process_single_fact(fact, corp_profile)
            if signal:
                signal["confidence"] = "LOW"  # 강제 LOW
                signal["is_fallback"] = True
                signal["fallback_reason"] = "No matching rule"
                signals.append(signal)

        return signals

    def _process_single_fact(
        self,
        fact: ExtractedFact,
        corp_profile: dict
    ) -> Optional[dict]:
        """단일 Fact LLM 처리"""

        prompt = f"""다음 사실(Fact)에 대해 금융 리스크/기회 시그널을 생성하세요.

## 사실
- 유형: {fact.fact_type}
- 주체: {fact.subject}
- 내용: {fact.predicate}
- 값: {fact.object_value}
- 출처: {fact.source_ref}

## 기업 정보
- 기업명: {corp_profile.get('corp_name')}
- 업종: {corp_profile.get('industry_name')}

## 규칙
1. 해당 기업과 관련성이 불명확하면 시그널 생성 금지
2. impact_direction은 RISK, OPPORTUNITY, NEUTRAL 중 선택
3. 판단 근거 없으면 NEUTRAL

## 출력 (JSON)
{{
  "should_create_signal": true/false,
  "signal_type": "DIRECT|INDUSTRY|ENVIRONMENT",
  "event_type": "...",
  "impact_direction": "...",
  "impact_strength": "MED",
  "reason": "생성/미생성 이유"
}}
"""

        response = self.llm.call(prompt)
        # ... JSON 파싱 및 시그널 생성
```

### 8.2 Fallback 비율 모니터링

```python
class FallbackMonitor:
    """Fallback 비율 모니터링"""

    def __init__(self, alert_threshold: float = 0.2):
        self.alert_threshold = alert_threshold
        self.stats = defaultdict(lambda: {"total": 0, "fallback": 0})

    def record(self, corp_id: str, total_facts: int, fallback_facts: int):
        self.stats[corp_id]["total"] += total_facts
        self.stats[corp_id]["fallback"] += fallback_facts

        # 전체 비율 확인
        total = sum(s["total"] for s in self.stats.values())
        fallback = sum(s["fallback"] for s in self.stats.values())

        if total > 0:
            ratio = fallback / total
            if ratio > self.alert_threshold:
                self._alert(ratio)

    def _alert(self, ratio: float):
        logger.warning(
            f"[FallbackMonitor] High fallback ratio: {ratio:.1%}. "
            f"Consider adding new rules."
        )
```

---

## 9. 데이터베이스 스키마

### 9.1 신규 테이블

```sql
-- Fact 저장 테이블
CREATE TABLE rkyc_extracted_fact (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id),
    job_id UUID REFERENCES rkyc_job(job_id),

    -- Fact 정보
    fact_type VARCHAR(50) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    predicate VARCHAR(200) NOT NULL,
    object_value JSONB,
    previous_value JSONB,
    change_direction VARCHAR(20),
    change_magnitude DECIMAL(10, 2),

    -- 출처
    source_type VARCHAR(20) NOT NULL,  -- SNAPSHOT, DOCUMENT, EXTERNAL
    source_ref VARCHAR(500) NOT NULL,
    source_snippet TEXT,

    -- 검증
    validation_status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, VALID, INVALID
    validation_details JSONB,

    -- 메타데이터
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    extraction_model VARCHAR(50),

    CONSTRAINT valid_fact_type CHECK (fact_type IN (
        'overdue_status', 'grade_change', 'exposure_change', 'collateral_change',
        'shareholder_change', 'officer_change', 'financial_change',
        'company_news', 'industry_news', 'policy_news', 'unclassified'
    ))
);

CREATE INDEX idx_fact_corp_id ON rkyc_extracted_fact(corp_id);
CREATE INDEX idx_fact_type ON rkyc_extracted_fact(fact_type);
CREATE INDEX idx_fact_job_id ON rkyc_extracted_fact(job_id);


-- 규칙 실행 로그 테이블
CREATE TABLE rkyc_rule_execution_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES rkyc_job(job_id),
    fact_id UUID REFERENCES rkyc_extracted_fact(fact_id),
    signal_id UUID REFERENCES rkyc_signal(signal_id),

    -- 규칙 정보
    rule_id VARCHAR(100),
    rule_matched BOOLEAN NOT NULL,
    match_reason TEXT,

    -- Fallback 정보
    is_fallback BOOLEAN DEFAULT FALSE,
    fallback_reason TEXT,

    -- 타이밍
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    execution_time_ms INTEGER
);

CREATE INDEX idx_rule_log_job_id ON rkyc_rule_execution_log(job_id);
CREATE INDEX idx_rule_log_rule_id ON rkyc_rule_execution_log(rule_id);


-- 규칙 정의 테이블 (선택적 - 동적 규칙 관리용)
CREATE TABLE rkyc_signal_rule (
    rule_id VARCHAR(100) PRIMARY KEY,
    rule_name VARCHAR(200) NOT NULL,
    rule_version INTEGER DEFAULT 1,

    -- 매칭 조건
    fact_type VARCHAR(50) NOT NULL,
    conditions JSONB NOT NULL,  -- [{field, operator, value}, ...]

    -- 시그널 생성 정보
    signal_type VARCHAR(20) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    impact_direction VARCHAR(20),  -- NULL이면 동적 계산
    impact_strength VARCHAR(20),   -- NULL이면 동적 계산

    -- 메타데이터
    priority INTEGER DEFAULT 100,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100)
);
```

### 9.2 기존 테이블 수정

```sql
-- rkyc_signal에 규칙 추적 필드 추가
ALTER TABLE rkyc_signal ADD COLUMN rule_id VARCHAR(100);
ALTER TABLE rkyc_signal ADD COLUMN fact_id UUID REFERENCES rkyc_extracted_fact(fact_id);
ALTER TABLE rkyc_signal ADD COLUMN is_fallback BOOLEAN DEFAULT FALSE;
ALTER TABLE rkyc_signal ADD COLUMN generation_method VARCHAR(20) DEFAULT 'RULE';
-- generation_method: 'RULE', 'FALLBACK', 'LEGACY'

COMMENT ON COLUMN rkyc_signal.rule_id IS '시그널 생성에 사용된 규칙 ID';
COMMENT ON COLUMN rkyc_signal.generation_method IS 'RULE: 규칙 엔진, FALLBACK: LLM, LEGACY: 이전 방식';
```

---

## 10. API 엔드포인트

### 10.1 신규 엔드포인트

```python
# GET /api/v1/facts/{corp_id}
# 기업별 추출된 Fact 목록 조회
@router.get("/facts/{corp_id}")
async def get_facts(
    corp_id: str,
    job_id: Optional[str] = None,
    fact_type: Optional[str] = None,
    validation_status: Optional[str] = None,
):
    """기업별 추출된 Fact 조회"""
    pass


# GET /api/v1/rules
# 활성화된 규칙 목록 조회
@router.get("/rules")
async def get_rules(
    signal_type: Optional[str] = None,
    event_type: Optional[str] = None,
    enabled_only: bool = True,
):
    """시그널 생성 규칙 목록 조회"""
    pass


# GET /api/v1/rules/{rule_id}/stats
# 규칙별 매칭 통계
@router.get("/rules/{rule_id}/stats")
async def get_rule_stats(
    rule_id: str,
    days: int = 30,
):
    """규칙별 매칭 통계 조회"""
    pass


# GET /api/v1/admin/fallback-stats
# Fallback 통계
@router.get("/admin/fallback-stats")
async def get_fallback_stats(
    days: int = 7,
):
    """LLM Fallback 사용 통계"""
    pass


# POST /api/v1/admin/rules/test
# 규칙 테스트 (Dry Run)
@router.post("/admin/rules/test")
async def test_rule(
    rule: SignalRuleCreate,
    sample_facts: list[dict],
):
    """규칙 테스트 (실제 저장 없이)"""
    pass
```

### 10.2 기존 엔드포인트 수정

```python
# GET /api/v1/signals/{signal_id}/detail
# 시그널 상세에 규칙 정보 추가

class SignalDetailResponseV2(SignalDetailResponse):
    rule_id: Optional[str]           # 사용된 규칙 ID
    rule_name: Optional[str]         # 규칙 이름
    fact_id: Optional[str]           # 원본 Fact ID
    generation_method: str           # RULE, FALLBACK, LEGACY
    is_fallback: bool               # Fallback 여부
```

---

## 11. 마이그레이션 계획

### 11.1 Phase 1: 병렬 실행 (1주일)

```
현재 시스템 (LLM 기반) ──┬──▶ Signal (Production)
                         │
새 시스템 (Rule 기반) ───┴──▶ Signal (Shadow, 저장만)
```

- 새 시스템을 Shadow 모드로 실행
- 동일 입력에 대해 두 시스템 출력 비교
- 불일치 분석 및 규칙 보완

### 11.2 Phase 2: A/B 테스트 (1주일)

- 50% 트래픽을 새 시스템으로 라우팅
- Precision, Recall, 사용자 피드백 측정
- 목표: 새 시스템 품질 >= 기존 시스템

### 11.3 Phase 3: 전환 (3일)

- 새 시스템을 Primary로 전환
- 기존 시스템을 Fallback으로 유지 (1주일)
- 안정화 확인 후 기존 시스템 제거

---

## 12. 성공 지표

### 12.1 품질 지표

| 지표 | 정의 | 목표 |
|------|------|------|
| Hallucination Rate | (허위 시그널 / 전체 시그널) | < 0.1% |
| Precision | (정확한 시그널 / 생성 시그널) | > 95% |
| Recall | (탐지 시그널 / 실제 이벤트) | > 85% |
| Consistency | (동일 입력 동일 출력 비율) | > 99% |

### 12.2 운영 지표

| 지표 | 정의 | 목표 |
|------|------|------|
| Rule Coverage | (규칙 매칭 / 전체 Fact) | > 80% |
| Fallback Rate | (Fallback / 전체 시그널) | < 20% |
| Latency p95 | 시그널 생성 시간 | < 5초 |
| LLM Cost | 기업당 LLM 비용 | < $0.05 |

### 12.3 비즈니스 지표

| 지표 | 정의 | 목표 |
|------|------|------|
| User Trust | 시그널 기각률 | < 10% |
| Explainability | 규칙 ID 추적 가능 비율 | 100% |
| Audit Readiness | 근거 추적 가능 비율 | 100% |

---

## 13. 리스크 및 완화

### 13.1 기술 리스크

| 리스크 | 확률 | 영향 | 완화 |
|--------|------|------|------|
| 규칙 커버리지 부족 | 중 | 중 | LLM Fallback + 주간 규칙 리뷰 |
| Fact 추출 Hallucination | 낮음 | 높음 | Fact Validator 강화 |
| 성능 저하 | 낮음 | 중 | 규칙 엔진 최적화, 캐싱 |

### 13.2 비즈니스 리스크

| 리스크 | 확률 | 영향 | 완화 |
|--------|------|------|------|
| 시그널 수 급감 | 중 | 높음 | Phase 1 병렬 비교로 사전 확인 |
| 사용자 혼란 | 낮음 | 중 | 점진적 전환, 변경 사항 안내 |

---

## 14. 타임라인

| Phase | 기간 | 주요 작업 |
|-------|------|----------|
| **Phase 1**: 설계 | 3일 | 상세 설계, DB 스키마 확정 |
| **Phase 2**: 구현 | 7일 | Rule Engine, Fact Extractor, Summary Generator |
| **Phase 3**: 테스트 | 5일 | 단위 테스트, 통합 테스트, 규칙 검증 |
| **Phase 4**: 병렬 실행 | 7일 | Shadow 모드 실행, 비교 분석 |
| **Phase 5**: A/B 테스트 | 7일 | 50% 트래픽 라우팅, 품질 측정 |
| **Phase 6**: 전환 | 3일 | Primary 전환, 모니터링 |

**총 소요: 약 5주**

---

## 15. 승인

| 역할 | 이름 | 승인 | 날짜 |
|------|------|------|------|
| Product Owner | - | ⬜ | - |
| Tech Lead | - | ⬜ | - |
| Security | - | ⬜ | - |
| QA Lead | - | ⬜ | - |

---

## Appendix A: 규칙 예시 전체 목록

```python
# 전체 규칙 ID 목록

DIRECT_RULES = [
    "DIRECT_OVERDUE_001",           # 연체 발생
    "DIRECT_GRADE_DOWN_001",        # 등급 하락
    "DIRECT_GRADE_UP_001",          # 등급 상승
    "DIRECT_EXPOSURE_UP_001",       # 여신 증가
    "DIRECT_EXPOSURE_DOWN_001",     # 여신 감소
    "DIRECT_CEO_CHANGE_001",        # 대표이사 변경
    "DIRECT_MAJOR_SHAREHOLDER_001", # 주요주주 변경
    "DIRECT_REVENUE_DROP_001",      # 매출 급감
    "DIRECT_REVENUE_SURGE_001",     # 매출 급증
    "DIRECT_OPERATING_LOSS_001",    # 영업이익 적자 전환
    "DIRECT_OPERATING_PROFIT_001",  # 영업이익 흑자 전환
    "DIRECT_COLLATERAL_DROP_001",   # 담보가치 하락
    "DIRECT_KYC_EXPIRY_001",        # KYC 갱신 필요
]

INDUSTRY_RULES = [
    "INDUSTRY_NEGATIVE_001",        # 산업 부정적 뉴스
    "INDUSTRY_POSITIVE_001",        # 산업 긍정적 뉴스
    "INDUSTRY_DEMAND_CHANGE_001",   # 수요 변화
    "INDUSTRY_SUPPLY_SHOCK_001",    # 공급 충격
    "INDUSTRY_COMPETITION_001",     # 경쟁 구도 변화
]

ENVIRONMENT_RULES = [
    "ENV_POLICY_REGULATION_001",    # 정책/규제 발표
    "ENV_FX_CHANGE_001",            # 환율 변동
    "ENV_RATE_CHANGE_001",          # 금리 변동
    "ENV_TRADE_POLICY_001",         # 무역 정책
    "ENV_GEOPOLITICAL_001",         # 지정학 리스크
]
```

---

## Appendix B: 용어 정의

| 용어 | 정의 |
|------|------|
| **Fact** | LLM이 추출한 객관적 사실 단위 |
| **Rule** | Fact를 Signal로 변환하는 결정론적 규칙 |
| **Rule Engine** | 규칙을 적용하여 시그널을 생성하는 엔진 |
| **Fallback** | 규칙 미매칭 시 LLM으로 처리하는 방식 |
| **Shadow Mode** | 실제 저장 없이 결과만 비교하는 테스트 모드 |

---

*End of Document*
