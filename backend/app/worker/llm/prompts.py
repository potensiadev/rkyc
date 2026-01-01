"""
LLM Prompt Templates
Prompt templates for signal extraction and insight generation
"""

# =============================================================================
# Signal Extraction Prompts
# =============================================================================

SIGNAL_EXTRACTION_SYSTEM = """당신은 금융기관의 기업 리스크 분석 전문가입니다.
주어진 기업 데이터와 외부 이벤트 정보를 분석하여 리스크 시그널을 추출합니다.

## 필수 규칙

### 1. 출처(Evidence) 필수
모든 시그널은 반드시 1개 이상의 출처(evidence)를 포함해야 합니다.
출처 없는 시그널은 생성하지 마세요.

### 2. 금지 표현 (절대 사용 금지)
다음 표현을 사용하면 안 됩니다:
- "~일 것이다", "~할 것이다" (단정적 예측)
- "반드시", "무조건" (절대적 표현)
- "즉시 조치 필요", "긴급" (과도한 긴급성)
- "확실히", "틀림없이" (확정적 표현)

### 3. 허용 표현 (대신 사용)
- "~로 추정됨", "~로 분석됨"
- "~가능성 있음", "~가능성이 높음"
- "검토 권고", "확인 필요"
- "~로 보도됨", "~로 알려짐" (외부 정보)

## Signal Type (3종 - 반드시 이 중 하나 선택)
- DIRECT: 기업에 직접 영향을 미치는 내부 리스크 (재무, 거래, 내부등급 변화 등)
- INDUSTRY: 해당 산업 전체에 영향을 미치는 리스크 (업종 트렌드, 시장 변화)
- ENVIRONMENT: 거시경제, 정책, 규제 등 외부 환경 리스크

## Event Type (10종 - 반드시 이 중 하나 선택)
1. KYC_REFRESH - KYC 갱신 필요
2. INTERNAL_RISK_GRADE_CHANGE - 내부 리스크 등급 변경
3. OVERDUE_FLAG_ON - 연체 발생
4. LOAN_EXPOSURE_CHANGE - 여신 노출 변화
5. COLLATERAL_CHANGE - 담보 변화
6. OWNERSHIP_CHANGE - 소유구조 변화
7. GOVERNANCE_CHANGE - 지배구조 변화
8. FINANCIAL_STATEMENT_UPDATE - 재무제표 변경
9. INDUSTRY_SHOCK - 산업 충격
10. POLICY_REGULATION_CHANGE - 정책/규제 변화

## Impact Direction
- RISK: 부정적 영향 (리스크 증가)
- OPPORTUNITY: 긍정적 영향 (기회 요인)
- NEUTRAL: 중립적 영향 (모니터링 필요)

## 출력 형식 (JSON)
```json
{
    "signals": [
        {
            "signal_type": "DIRECT|INDUSTRY|ENVIRONMENT",
            "event_type": "<위 10종 중 하나>",
            "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
            "impact_strength": "HIGH|MED|LOW",
            "confidence": "HIGH|MED|LOW",
            "title": "간결한 시그널 제목 (50자 이내)",
            "summary": "상세 설명 (200자 이내, 근거 포함, 금지표현 미사용)",
            "evidence": [
                {
                    "evidence_type": "INTERNAL_FIELD|DOC|EXTERNAL",
                    "ref_type": "SNAPSHOT_KEYPATH|DOC_PAGE|URL",
                    "ref_value": "/credit/loan_summary/overdue_flag 또는 URL",
                    "snippet": "관련 텍스트 스니펫 (100자 이내)"
                }
            ]
        }
    ]
}
```

## 분석 지침
1. 스냅샷 데이터의 변화를 먼저 확인하세요 (연체, 등급, 담보 등)
2. 외부 이벤트와 기업/산업의 연관성을 분석하세요
3. 불필요한 시그널을 남발하지 마세요. 실제 의미 있는 변화만 추출하세요.
4. 동일한 사안에 대해 중복 시그널을 생성하지 마세요.
5. 시그널이 없으면 빈 배열을 반환하세요: {"signals": []}
"""

SIGNAL_EXTRACTION_USER_TEMPLATE = """## 분석 대상 기업
- 기업명: {corp_name}
- 법인번호: {corp_reg_no}
- 업종코드: {industry_code} ({industry_name})

## 내부 스냅샷 데이터
{snapshot_json}

## 관련 외부 이벤트
{external_events}

위 정보를 분석하여 리스크 시그널을 JSON 형식으로 추출하세요.
시그널이 없으면 {{"signals": []}}를 반환하세요.
"""


# =============================================================================
# Insight Generation Prompts
# =============================================================================

INSIGHT_GENERATION_PROMPT = """## 경영진 브리핑 요약 생성

다음 기업의 리스크 시그널 분석 결과를 경영진 브리핑 형식으로 요약하세요.

### 기업 정보
- 기업명: {corp_name}
- 업종: {industry_code} ({industry_name})

### 발견된 시그널 ({signal_count}건)
{signals_summary}

### 요약 형식
1. **핵심 요약** (2-3문장)
   - 가장 중요한 리스크/기회 요인 요약
   - 전체적인 리스크 수준 평가

2. **주요 시그널** (우선순위순)
   - 각 시그널의 핵심 내용 1줄 요약

3. **권고 조치사항**
   - 담당자가 검토해야 할 사항
   - 추가 확인이 필요한 영역

### 주의사항
- 단정적 표현 금지 ("~일 것이다", "반드시", "즉시 조치 필요")
- 허용 표현 사용 ("~로 추정됨", "검토 권고", "~가능성 있음")
- 객관적이고 사실에 기반한 요약만 작성
"""


# =============================================================================
# Helper Functions
# =============================================================================

def format_signal_extraction_prompt(
    corp_name: str,
    corp_reg_no: str,
    industry_code: str,
    industry_name: str,
    snapshot_json: str,
    external_events: str,
) -> str:
    """Format the signal extraction user prompt with context data"""
    return SIGNAL_EXTRACTION_USER_TEMPLATE.format(
        corp_name=corp_name,
        corp_reg_no=corp_reg_no or "N/A",
        industry_code=industry_code,
        industry_name=industry_name,
        snapshot_json=snapshot_json,
        external_events=external_events,
    )


def format_insight_prompt(
    corp_name: str,
    industry_code: str,
    industry_name: str,
    signals: list[dict],
) -> str:
    """Format the insight generation prompt"""
    # Format signals summary
    if not signals:
        signals_summary = "발견된 시그널이 없습니다."
    else:
        lines = []
        for i, sig in enumerate(signals, 1):
            line = (
                f"{i}. [{sig.get('signal_type', 'N/A')}] {sig.get('event_type', 'N/A')}\n"
                f"   - 제목: {sig.get('title', 'N/A')}\n"
                f"   - 영향: {sig.get('impact_direction', 'N/A')} / 강도: {sig.get('impact_strength', 'N/A')}\n"
                f"   - 신뢰도: {sig.get('confidence', 'N/A')}"
            )
            lines.append(line)
        signals_summary = "\n".join(lines)

    return INSIGHT_GENERATION_PROMPT.format(
        corp_name=corp_name,
        industry_code=industry_code,
        industry_name=industry_name,
        signal_count=len(signals),
        signals_summary=signals_summary,
    )


# Industry code to name mapping
INDUSTRY_CODE_MAP = {
    "C10": "식품제조업",
    "C21": "의약품제조업",
    "C26": "전자부품제조업",
    "C29": "기계장비제조업",
    "D35": "전기업",
    "F41": "건설업",
    "G45": "자동차판매업",
    "G46": "도매업",
    "G47": "소매업",
    "H49": "육상운송업",
    "J58": "출판업",
    "J62": "소프트웨어개발업",
    "K64": "금융업",
    "L68": "부동산업",
    "M70": "경영컨설팅업",
    "N74": "전문서비스업",
}


def get_industry_name(industry_code: str) -> str:
    """Get industry name from code"""
    return INDUSTRY_CODE_MAP.get(industry_code, f"기타 ({industry_code})")
