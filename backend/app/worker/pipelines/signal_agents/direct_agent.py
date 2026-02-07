"""
Direct Signal Agent - DIRECT signal extraction specialist

Sprint 2: Signal Multi-Agent Architecture (ADR-009)
[2026-02-08] Buffett-Style Anti-Hallucination Update

Specialization:
- Signal Type: DIRECT (기업 직접 영향)
- Event Types: 8종
  - KYC_REFRESH
  - INTERNAL_RISK_GRADE_CHANGE
  - OVERDUE_FLAG_ON
  - LOAN_EXPOSURE_CHANGE
  - COLLATERAL_CHANGE
  - OWNERSHIP_CHANGE
  - GOVERNANCE_CHANGE
  - FINANCIAL_STATEMENT_UPDATE

Focus:
- Internal snapshot data (연체, 등급, 담보, 여신 변화)
- Direct company events (뉴스, 공시)
- HIGH confidence from internal data

Buffett Principles Applied:
- "You are a librarian, not an analyst"
- retrieval_confidence: VERBATIM | PARAPHRASED | INFERRED
- "I don't know" is a valid answer
"""

import json
import logging

from app.worker.pipelines.signal_agents.base import (
    BaseSignalAgent,
    BUFFETT_LIBRARIAN_PERSONA,
    SOURCE_CREDIBILITY,
)
from app.worker.llm.prompts import (
    SOFT_GUARDRAILS,
    CHAIN_OF_THOUGHT_GUIDE,
    DIRECT_FEW_SHOT_EXAMPLES,
)

logger = logging.getLogger(__name__)


class DirectSignalAgent(BaseSignalAgent):
    """
    Specialized agent for DIRECT signal extraction.

    Focus areas:
    - Internal financial data changes
    - Company-specific news and events
    - Ownership and governance changes
    """

    AGENT_NAME = "direct_signal_agent"
    SIGNAL_TYPE = "DIRECT"
    ALLOWED_EVENT_TYPES = {
        "KYC_REFRESH",
        "INTERNAL_RISK_GRADE_CHANGE",
        "OVERDUE_FLAG_ON",
        "LOAN_EXPOSURE_CHANGE",
        "COLLATERAL_CHANGE",
        "OWNERSHIP_CHANGE",
        "GOVERNANCE_CHANGE",
        "FINANCIAL_STATEMENT_UPDATE",
    }

    def get_system_prompt(self, corp_name: str, industry_name: str) -> str:
        """Build DIRECT-specialized system prompt with Buffett anti-hallucination."""
        return f"""# 역할: DIRECT 시그널 추출 전문 사서 (Librarian)

{BUFFETT_LIBRARIAN_PERSONA}

## 분석 대상
- 기업명: {corp_name}
- 업종: {industry_name}

## 분석 범위 (DIRECT 시그널만)
**DIRECT 시그널**: 해당 기업에 직접적으로 영향을 미치는 **확인된 사실**만 추출

## 허용된 event_type (8종)
1. KYC_REFRESH - KYC 갱신 시점 도래 또는 정보 변경
2. INTERNAL_RISK_GRADE_CHANGE - 내부 신용등급 변동
3. OVERDUE_FLAG_ON - 연체 발생 (30일 이상)
4. LOAN_EXPOSURE_CHANGE - 여신 노출 금액 변화 (±10% 이상)
5. COLLATERAL_CHANGE - 담보 가치/유형 변화
6. OWNERSHIP_CHANGE - 대주주/지분구조 변경
7. GOVERNANCE_CHANGE - 대표이사/이사회 변경
8. FINANCIAL_STATEMENT_UPDATE - 재무제표 변동 (매출/영업이익 ±20%)

## 데이터 출처별 신뢰도 (SOURCE CREDIBILITY)
| 출처 | 신뢰도 | retrieval_confidence |
|------|--------|---------------------|
| 내부 스냅샷 | 100점 | VERBATIM 필수 |
| DART 공시 (dart.fss.or.kr) | 100점 | VERBATIM 권장 |
| 한국거래소 (kind.krx.co.kr) | 100점 | VERBATIM 권장 |
| 주요 언론 | 70-80점 | PARAPHRASED 허용 |
| 기타 | 50점 이하 | 단독 사용 금지 |

{SOFT_GUARDRAILS}

{CHAIN_OF_THOUGHT_GUIDE}

## DIRECT 시그널 예시
{DIRECT_FEW_SHOT_EXAMPLES}

## 🔴 절대 규칙 (Anti-Hallucination)
1. **signal_type은 반드시 "DIRECT"**
2. **event_type은 위 8종 중 하나만 사용**
3. **숫자는 원본에서 복사만** - 계산하거나 추정 금지
   - ❌ 금지: "약 30% 감소로 추정"
   - ✅ 허용: "30.4% 감소 (출처: 2025년 3분기 실적)"
4. **Evidence 없으면 시그널 생성 금지** - 빈 배열 []이 hallucination보다 낫다
5. **retrieval_confidence 필수 명시**
   - INFERRED 사용 시 confidence_reason 필수
6. **could_not_find 필드 사용** - 찾지 못한 정보 명시

## 금지 표현 (HALLUCINATION_INDICATORS)
다음 표현이 포함되면 시그널 거부:
- "추정됨", "전망", "예상", "것으로 보인다"
- "일반적으로", "통상적으로", "약", "대략"
- "~할 것이다", "~일 것이다"

## 출력 형식 (JSON)
```json
{{
  "signals": [
    {{
      "signal_type": "DIRECT",
      "event_type": "<8종 중 하나>",
      "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
      "impact_strength": "HIGH|MED|LOW",
      "confidence": "HIGH|MED|LOW",
      "title": "제목 (50자 이내, 사실만)",
      "summary": "설명 (200자 이내, 원본 인용)",
      "retrieval_confidence": "VERBATIM|PARAPHRASED|INFERRED",
      "confidence_reason": "INFERRED일 경우 추론 근거 (선택)",
      "evidence": [
        {{
          "evidence_type": "INTERNAL_FIELD|DOC|EXTERNAL",
          "ref_type": "SNAPSHOT_KEYPATH|DOC_PAGE|URL",
          "ref_value": "/경로 또는 URL",
          "snippet": "원문 인용 (100자 이내)",
          "source_credibility": 100
        }}
      ]
    }}
  ],
  "could_not_find": ["확인 불가한 정보 목록"]
}}
```
"""

    def get_user_prompt(self, context: dict) -> str:
        """Build user prompt with Buffett-style anti-hallucination instructions."""
        corp_name = context.get("corp_name", "")
        corp_reg_no = context.get("corp_reg_no", "")
        industry_name = context.get("industry_name", "")

        # Get snapshot data (primary source for DIRECT)
        snapshot_json = json.dumps(
            context.get("snapshot_json", {}),
            ensure_ascii=False,
            indent=2,
        )

        # Get direct events from external search
        direct_events = json.dumps(
            context.get("direct_events", []),
            ensure_ascii=False,
            indent=2,
        )

        # v2.1: Get document facts (from DOC_INGEST pipeline)
        document_facts = context.get("document_facts", [])
        document_facts_str = json.dumps(
            document_facts,
            ensure_ascii=False,
            indent=2,
        ) if document_facts else "없음"

        # Previous snapshot for comparison (if available)
        prev_snapshot = context.get("previous_snapshot_json", {})
        prev_snapshot_str = json.dumps(
            prev_snapshot,
            ensure_ascii=False,
            indent=2,
        ) if prev_snapshot else "없음"

        return f"""# 분석 대상 기업 (DIRECT 시그널)
- 기업명: {corp_name}
- 법인번호: {corp_reg_no}
- 업종: {industry_name}

---

## 📊 데이터 소스 (이 데이터에 있는 사실만 추출)

### 1. 현재 내부 스냅샷 (신뢰도: 100점, VERBATIM 필수)
```json
{snapshot_json}
```

### 2. 이전 스냅샷 (변화 비교용)
```json
{prev_snapshot_str}
```

### 3. 제출 문서 Facts (신뢰도: 100점)
```json
{document_facts_str}
```

### 4. 외부 검색 결과 (신뢰도: URL 도메인 참조)
```json
{direct_events}
```

---

## 🔍 Buffett 스타일 추출 지침

### 사서(Librarian) 원칙
1. **복사만 하세요** - 위 데이터에 있는 숫자/사실만 그대로 인용
2. **계산하지 마세요** - "약 30% 감소"처럼 추정 금지
3. **없으면 없다고 하세요** - could_not_find 필드 활용

### Falsification 체크리스트 (Invert, Always Invert)
시그널 생성 전 스스로 물어보세요:
□ 이 숫자가 위 데이터에 **정확히** 있는가?
□ 이 URL이 위 검색 결과에 **실제로** 있는가?
□ 내가 **추론**하고 있지는 않은가?
□ 이 표현이 **금지 표현**에 해당하지 않는가?

### 출력 규칙
- **연체, 등급, 담보, 여신 변화**: 스냅샷 비교로 확인 → VERBATIM
- **주주변경, 임원변경, 재무변동**: 문서/공시에서 확인 → VERBATIM
- **뉴스 기반 이벤트**: 원문 snippet 필수 → PARAPHRASED 허용

### ⚠️ 시그널 생성 금지 조건
- 데이터에 없는 숫자가 포함됨
- Evidence URL이 검색 결과에 없음
- "추정", "전망", "예상" 표현 사용
- 스냅샷 간 유의미한 변화 없음 (연체 없음, 등급 동일)

---

**위 데이터를 기반으로 DIRECT 시그널만 추출하세요.**
**확실하지 않으면 빈 배열 []을 반환하세요. 그것이 정답입니다.**

JSON 형식으로 출력:
"""

    def get_relevant_events(self, context: dict) -> list[dict]:
        """Extract direct events from context."""
        # For DIRECT, we primarily use internal snapshot
        # but also include direct_events from external search
        direct_events = context.get("direct_events", [])

        # DIRECT agent can always run because internal snapshot is primary source
        # Return direct_events (may be empty)
        return direct_events
