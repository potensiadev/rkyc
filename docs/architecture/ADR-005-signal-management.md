# ADR-005: 시그널 상태 관리 및 Guardrails

## 상태
Accepted

## 날짜
2025-01-XX

## 컨텍스트
rKYC 시스템의 핵심 출력물인 "시그널"은 기업 리스크 징후를 나타내는 개별 항목이다.
시그널은 AI가 생성하지만, 최종 판단은 인간 심사역이 수행한다.
AI 생성 콘텐츠의 품질과 신뢰성을 보장하기 위한 명확한 규칙이 필요하다.

### 요구사항
1. 시그널 생애주기 명확한 정의
2. 근거(evidence) 필수 제공
3. 단정적 표현 금지
4. 중복 시그널 방지
5. 감사 추적(audit trail)

## 결정
**시그널 상태 머신과 Guardrails 검증 레이어를 구현한다.**

### 시그널 상태 흐름
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│    ┌──────┐     ┌──────────┐     ┌───────────┐         │
│    │ new  │────▶│ reviewed │────▶│ confirmed │         │
│    └──────┘     └──────────┘     └───────────┘         │
│        │              │                                 │
│        │              │          ┌───────────┐         │
│        └──────────────┴─────────▶│ dismissed │         │
│                                  └───────────┘         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

| 상태 | 설명 | 전이 가능 상태 |
|-----|------|---------------|
| new | 신규 생성됨 | reviewed, dismissed |
| reviewed | 검토 완료 | confirmed, dismissed |
| confirmed | 리스크 확정 | (최종) |
| dismissed | 기각됨 | (최종) |

### 시그널 카테고리
```python
class SignalCategory(Enum):
    FINANCIAL = "financial"       # 재무 리스크
    LEGAL = "legal"              # 법적 리스크
    REPUTATIONAL = "reputational" # 평판 리스크
    OPERATIONAL = "operational"   # 운영 리스크
    MARKET = "market"            # 시장 리스크
```

### 심각도 레벨
```python
class SignalSeverity(Enum):
    INFO = 1       # 정보성
    LOW = 2        # 낮음
    MEDIUM = 3     # 보통
    HIGH = 4       # 높음
    CRITICAL = 5   # 심각
```

## Guardrails 규칙

### 1. Evidence 필수 규칙
```python
class SignalValidator:
    def validate_evidence(self, signal: Signal) -> bool:
        """모든 시그널은 최소 1개의 evidence 필요"""
        if not signal.evidence or len(signal.evidence) == 0:
            raise ValidationError(
                "Signal must have at least one evidence source"
            )

        for ev in signal.evidence:
            if not ev.url and not ev.source:
                raise ValidationError(
                    "Evidence must have URL or source reference"
                )
        return True
```

### 2. 금지 표현 필터
```python
FORBIDDEN_EXPRESSIONS = [
    "~일 것이다",      # 단정적 예측
    "반드시",          # 강제적 표현
    "즉시 조치 필요",   # 과도한 긴급성
    "확실히",          # 단정적 확신
    "틀림없이",        # 단정적 확신
    "무조건",          # 절대적 표현
]

ALLOWED_ALTERNATIVES = {
    "~일 것이다": "~로 추정됨, ~가능성 있음",
    "반드시": "권고됨, 고려 필요",
    "즉시 조치 필요": "조속한 검토 권고",
    "확실히": "높은 가능성으로",
    "틀림없이": "상당한 개연성으로",
    "무조건": "강력히 권고",
}

def check_forbidden_expressions(text: str) -> list[str]:
    """금지 표현 검출"""
    violations = []
    for expr in FORBIDDEN_EXPRESSIONS:
        if expr in text:
            violations.append(expr)
    return violations
```

### 3. 중복 시그널 방지
```python
async def check_duplicate_signal(
    db: AsyncSession,
    corp_id: str,
    new_signal: SignalCreate
) -> Optional[Signal]:
    """유사 시그널 존재 여부 확인"""

    # 최근 30일 내 동일 카테고리 시그널 조회
    recent_signals = await db.execute(
        select(Signal)
        .where(Signal.corporation_id == corp_id)
        .where(Signal.category == new_signal.category)
        .where(Signal.created_at > datetime.now() - timedelta(days=30))
        .where(Signal.status != SignalStatus.DISMISSED)
    )

    for existing in recent_signals:
        similarity = compute_similarity(
            existing.description,
            new_signal.description
        )
        if similarity > 0.85:
            return existing  # 중복으로 간주

    return None
```

## 결과

### 긍정적 결과
1. **신뢰성**: Evidence 필수로 근거 기반 분석 보장
2. **책임 회피 방지**: 단정적 표현 금지로 AI 과신 방지
3. **효율성**: 중복 제거로 심사역 업무 부담 감소
4. **추적성**: 상태 변경 이력으로 감사 대응 가능

### 부정적 결과
1. **표현 제한**: 유효한 경고도 완화된 어조로 표현
2. **검증 비용**: 모든 시그널에 추가 처리 필요
3. **오탐 가능**: 유사도 기반 중복 검출의 한계

### 상태 변경 감사 로그
```python
async def change_signal_status(
    db: AsyncSession,
    signal_id: str,
    new_status: SignalStatus,
    user_id: str,
    reason: str = None
):
    signal = await db.get(Signal, signal_id)
    old_status = signal.status

    # 상태 전이 유효성 검사
    if not is_valid_transition(old_status, new_status):
        raise InvalidStateTransition(
            f"Cannot transition from {old_status} to {new_status}"
        )

    signal.status = new_status
    signal.updated_at = datetime.now()

    # 감사 로그 생성
    audit_log = SignalAuditLog(
        signal_id=signal_id,
        user_id=user_id,
        action=f"status_change:{old_status}->{new_status}",
        reason=reason,
        created_at=datetime.now()
    )
    db.add(audit_log)
    await db.commit()
```

## LLM 프롬프트 Guardrails

### 시그널 추출 프롬프트 템플릿
```python
SIGNAL_EXTRACTION_PROMPT = """
당신은 기업 리스크 분석 전문가입니다.
주어진 정보에서 리스크 시그널을 추출하세요.

## 규칙
1. 반드시 출처(evidence)를 명시하세요
2. 다음 표현을 사용하지 마세요: {forbidden_list}
3. 대신 다음과 같이 표현하세요: {allowed_alternatives}
4. 확인되지 않은 정보는 "~로 보도됨", "~주장" 등으로 표현하세요

## 출력 형식 (JSON)
{{
    "signals": [
        {{
            "category": "financial|legal|reputational|operational|market",
            "severity": 1-5,
            "title": "간결한 제목",
            "description": "상세 설명 (근거 포함)",
            "evidence": [
                {{"url": "출처 URL", "title": "기사 제목", "date": "YYYY-MM-DD"}}
            ]
        }}
    ]
}}
"""
```

## 대안 검토

### 대안 1: 자유 형식 시그널
- 장점: 유연성, 빠른 구현
- 단점: 품질 일관성 없음, 근거 누락 가능
- **기각 사유**: 금융 규제 환경에서 허용 불가

### 대안 2: 규칙 기반 시그널만 (LLM 미사용)
- 장점: 예측 가능, 일관성
- 단점: 새로운 유형 탐지 불가, 문맥 이해 부족
- **기각 사유**: 혁신적 리스크 패턴 탐지 불가

### 대안 3: Human-in-the-loop 필수
- 장점: 모든 시그널 인간 검증
- 단점: 확장성 제한, 병목 발생
- **기각 사유**: 대량 처리 시 비효율

## 참조
- PRD Full-Stack Spec v0.2 - Section 6.1 시그널 정의
- PRD 추가 지침서 - Section 2.3 Guardrails
