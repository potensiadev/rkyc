# ADR-009: 4-Layer Analysis Architecture with Null-Free Policy

## Status
**Accepted** - 2026-01-21

## Context

### 문제 정의
기존 LLM 기반 분석 시스템에서 다음과 같은 품질 이슈가 발생:

1. **NULL/정보 없음 문제**
   - 분석 필드가 비거나 "정보 없음"으로 남아 실무 활용도 저하
   - 금융기관 심사역이 추가 조사 필요

2. **전문성 체감 부족**
   - 기업 분석/시그널 분석이 월가(Wall Street) 수준에 미달
   - IB/신용분석 실무에서 신뢰성 부족으로 판단될 가능성

3. **근거-주장 연결 부족**
   - 증거 자료와 분석 결론이 분리
   - 감사/검증 가능성 저하

### 요구사항
- NULL/빈값/'정보 없음' 완전 제거
- 정보 부족 시에도 추정값 + 근거 + 범위 출력
- 기업 분석 7대 필수 요소 강제
- 시그널 분석에 영향 경로/조기경보/실행 체크리스트 포함
- 근거-주장 연결 및 반대 근거 포함

## Decision

### 4-Layer Analysis Architecture 도입

```
┌─────────────────────────────────────────────────────────────┐
│                    Layer 1: INTAKE                          │
│  - Entity matching verification (corp_name, biz_no)         │
│  - Signal date validation                                   │
│  - Source credibility labeling (A/B/C grade)               │
├─────────────────────────────────────────────────────────────┤
│                    Layer 2: EVIDENCE                        │
│  - Evidence collection with claim linking                   │
│  - Cross-verification across sources                        │
│  - Counter-evidence inclusion (minimum 1)                   │
│  - Duplicate source removal                                 │
├─────────────────────────────────────────────────────────────┤
│                 Layer 3: EXPERT ANALYSIS                    │
│  - Corporation Analysis (7 required sections)               │
│  - Signal Analysis (impact paths, early indicators)         │
│  - Actionable checklists generation                         │
│  - Null-free policy enforcement with estimation             │
├─────────────────────────────────────────────────────────────┤
│                  Layer 4: QUALITY GATE                      │
│  - Null-free compliance validation                          │
│  - Evidence coverage check (≥50%)                          │
│  - Counter-evidence requirement                             │
│  - Peer comparison (≥2 metrics)                            │
│  - Regulatory risk assessment check                         │
│  - Quality score calculation (0-100)                        │
└─────────────────────────────────────────────────────────────┘
```

### Null-Free Policy

```python
# 금지 값
FORBIDDEN_VALUES = [
    None, "", "null", "NULL", "N/A", "n/a",
    "정보 없음", "확인 필요", "미확인", "불명", "-"
]

# 필수 대체 형식
정보 부족 시:
- 숫자: "100억~200억 (업종 평균 기반 추정, 신뢰도: LOW)"
- 카테고리: "중 (범위 추정, 근거: 업종 평균)"
- 텍스트: "추정: [내용] (근거: [이유], 신뢰도: LOW)"
```

### Corporation Analysis 7대 필수 요소

| 섹션 | 필수 필드 | NULL 대체 방법 |
|------|----------|---------------|
| 1. 사업 구조 | core_business, revenue_segments, business_model | 업종 기반 추정 |
| 2. 시장 지위 | market_share_range, competitive_position | 범위로 표현 |
| 3. 재무 프로필 | profitability, stability, growth (각 추세+범위+리스크) | 업종 평균 |
| 4. 리스크 맵 | credit/operational/market/regulatory/concentration | "관찰된 리스크 없음" |
| 5. 촉매 | positive_catalysts, negative_catalysts | "식별된 촉매 없음 (추가 조사 권고)" |
| 6. 비교군 | **최소 2개 지표** 필수 | 매출액, 영업이익률 기본 |
| 7. ESG/거버넌스 | **recent_regulatory_risks** 필수 | "확인된 리스크 없음" |

### Signal Analysis 필수 요소

```python
@dataclass
class SignalAnalysis:
    # 1. 영향 경로 (세부 분류)
    impact_paths: list[dict]  # REVENUE, COST, REGULATION, DEMAND, SUPPLY_CHAIN, FINANCING, REPUTATION, OPERATIONAL

    # 2. 조기 경보 지표
    early_indicators: dict  # quantitative_indicators + qualitative_triggers

    # 3. 실행 가능 체크리스트
    actionable_checks: list[dict]  # action, responsible_role, deadline_type, verification_method

    # 4. 시나리오 분석
    scenario_analysis: dict  # base_case, upside_case, downside_case

    # 5. 영향 요약
    impact_summary: dict  # overall_direction, strength, confidence, recommended_stance
```

### Evidence Map 검증 규칙

| 규칙 | 기준 | 검증 |
|------|------|------|
| Claim-Evidence 연결 | 모든 claim에 evidence_id 연결 | 필수 |
| 신뢰도 등급 | A(공시)/B(주요언론)/C(일반) | 명시적 기준 |
| 반대 근거 | 최소 1건 | Quality Gate에서 검증 |
| 중복 제거 | 동일 URL/출처 1건만 | 자동 처리 |
| 교차 검증 | 2개 이상 출처 시 표시 | cross_verified 플래그 |

### Quality Gate 점수 계산

```python
def calculate_quality_score():
    score = 100.0

    # NULL 위반 (치명적)
    score -= len(null_violations) * 10

    # 근거 커버리지 부족
    if evidence_coverage < 0.8:
        score -= (0.8 - evidence_coverage) * 25

    # 반대 근거 누락
    if not has_counter_evidence:
        score -= 15

    # 비교군 지표 부족
    if peer_metrics < 2:
        score -= 10

    # 규제 리스크 점검 누락
    if not has_regulatory_check:
        score -= 10

    # 실행 체크리스트 보너스
    score += min(actionable_checks, 5) * 2

    return max(0, min(100, score))
```

## Consequences

### Positive
1. **정보 누락 제거**: 모든 필드가 값으로 채워짐
2. **월가 수준 체감**: 재무/경쟁/리스크/촉매 구조화
3. **감사 가능성 향상**: claim ↔ evidence 연결 구조
4. **조치 가능성 강화**: 담당자별 체크리스트 제공
5. **품질 정량화**: Quality Score로 분석 품질 측정 가능

### Negative
1. **LLM 비용 증가**: 더 긴 프롬프트와 상세 출력 요구
2. **처리 시간 증가**: 4-Layer 순차 실행
3. **복잡성 증가**: 유지보수 포인트 증가

### Risks
1. **추정값 오류**: NULL 대신 잘못된 추정값 출력 가능
   - 완화: 모든 추정에 신뢰도(LOW) 명시
2. **과도한 추정**: 실제 데이터 부족 시 추정값 비중 증가
   - 완화: 추정 비율 모니터링 및 경고

## Implementation

### 파일 구조
```
backend/app/worker/llm/
├── layer_architecture.py     # 4-Layer 구현
├── prompts_v2.py            # 강화된 프롬프트
└── __init__.py              # 모듈 export

backend/app/worker/pipelines/
├── expert_insight.py        # 통합 파이프라인
└── __init__.py              # 모듈 export
```

### 사용 예시
```python
from app.worker.llm import FourLayerAnalysisPipeline
from app.worker.pipelines import ExpertInsightPipeline

# 방법 1: 4-Layer Pipeline 직접 사용
pipeline = FourLayerAnalysisPipeline()
output = pipeline.execute(context)
print(f"Quality Score: {output.quality_metrics['overall_quality_score']}")

# 방법 2: ExpertInsightPipeline 사용 (권장)
expert = ExpertInsightPipeline()
result = expert.execute(signals, context)
print(f"Insight: {result['insight']}")
print(f"Quality: {result['quality_score']}")
```

### 기존 파이프라인과의 관계
- `InsightPipeline`: 기존 방식 유지 (하위 호환)
- `ExpertInsightPipeline`: 새로운 4-Layer 방식 (권장)
- `SignalExtractionPipeline`: 변경 없음 (Intake에서 추가 검증)

## Alternatives Considered

### Alternative 1: 단순 Validation 강화
- 기존 구조에 Validation 규칙만 추가
- **기각 이유**: 근본적인 품질 향상 어려움

### Alternative 2: LLM 프롬프트만 개선
- 시스템 프롬프트에 모든 규칙 추가
- **기각 이유**: LLM의 일관성 보장 어려움, 검증 불가

### Alternative 3: 후처리 보정
- LLM 출력 후 NULL을 자동 보정
- **기각 이유**: 맥락 없는 보정은 품질 저하 우려

## Related ADRs
- ADR-005: 시그널 상태 관리 및 Guardrails
- ADR-007: Vector Search - pgvector 기반 유사 케이스 검색
- ADR-008: Security Architecture LLM Separation

## References
- Wall Street Research Report Standards
- S&P/Moody's Credit Analysis Framework
- OWASP Guidelines for LLM Applications
