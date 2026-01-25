"""
Direct Signal Agent - DIRECT signal extraction specialist

Sprint 2: Signal Multi-Agent Architecture (ADR-009)

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
"""

import json
import logging

from app.worker.pipelines.signal_agents.base import BaseSignalAgent
from app.worker.llm.prompts import (
    RISK_MANAGER_PERSONA,
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
        """Build DIRECT-specialized system prompt."""
        return f"""당신은 기업 직접 리스크 분석 전문가입니다.
{corp_name}의 내부 데이터 변화와 기업 직접 관련 이벤트만 분석합니다.

# 전문가 페르소나
{RISK_MANAGER_PERSONA}

# 분석 범위 (DIRECT 시그널만)
**DIRECT 시그널**: 해당 기업에 직접적으로 영향을 미치는 변화

허용된 event_type (8종):
1. KYC_REFRESH - KYC 갱신 시점 도래 또는 정보 변경
2. INTERNAL_RISK_GRADE_CHANGE - 내부 신용등급 변동
3. OVERDUE_FLAG_ON - 연체 발생 (30일 이상)
4. LOAN_EXPOSURE_CHANGE - 여신 노출 금액 변화 (±10% 이상)
5. COLLATERAL_CHANGE - 담보 가치/유형 변화
6. OWNERSHIP_CHANGE - 대주주/지분구조 변경
7. GOVERNANCE_CHANGE - 대표이사/이사회 변경
8. FINANCIAL_STATEMENT_UPDATE - 재무제표 변동 (매출/영업이익 ±20%)

# 데이터 우선순위
1. **내부 스냅샷 (최우선)**: 연체, 등급, 담보, 여신 데이터 → HIGH confidence
2. **DART 공시**: 주주변경, 임원변경, 재무 공시 → HIGH confidence
3. **직접 뉴스**: 기업명이 직접 언급된 기사 → MED-HIGH confidence

{SOFT_GUARDRAILS}

{CHAIN_OF_THOUGHT_GUIDE}

# DIRECT 시그널 예시
{DIRECT_FEW_SHOT_EXAMPLES}

# 중요 규칙
1. signal_type은 반드시 "DIRECT"
2. event_type은 위 8종 중 하나만 사용
3. 내부 스냅샷 변화는 무조건 추출 (HIGH confidence)
4. summary에 기업명({corp_name})과 정량 정보 필수
5. 금지 표현 사용 금지
6. Evidence 없으면 시그널 생성 금지

# 출력 형식 (JSON)
```json
{{
  "signals": [
    {{
      "signal_type": "DIRECT",
      "event_type": "<8종 중 하나>",
      "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
      "impact_strength": "HIGH|MED|LOW",
      "confidence": "HIGH|MED|LOW",
      "title": "제목 (50자 이내)",
      "summary": "설명 (200자 이내)",
      "evidence": [
        {{
          "evidence_type": "INTERNAL_FIELD|DOC|EXTERNAL",
          "ref_type": "SNAPSHOT_KEYPATH|DOC_PAGE|URL",
          "ref_value": "/경로 또는 URL",
          "snippet": "관련 텍스트 (100자 이내)"
        }}
      ]
    }}
  ]
}}
```
"""

    def get_user_prompt(self, context: dict) -> str:
        """Build user prompt with internal snapshot and direct events."""
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

        # Previous snapshot for comparison (if available)
        prev_snapshot = context.get("previous_snapshot_json", {})
        prev_snapshot_str = json.dumps(
            prev_snapshot,
            ensure_ascii=False,
            indent=2,
        ) if prev_snapshot else "없음"

        return f"""# 분석 대상 기업
- 기업명: {corp_name}
- 법인번호: {corp_reg_no}
- 업종: {industry_name}

# 현재 내부 스냅샷 (DIRECT 분석 최우선)
```json
{snapshot_json}
```

# 이전 스냅샷 (변화 비교용)
```json
{prev_snapshot_str}
```

# 기업 직접 관련 외부 이벤트
```json
{direct_events}
```

---
위 데이터를 분석하여 DIRECT 시그널만 추출하세요.

**체크리스트**:
□ 내부 스냅샷에서 연체, 등급, 담보, 여신 변화 확인
□ 대표이사/주주구조 변경 확인
□ 재무제표 급변 확인 (매출/영업이익 ±20%)
□ 직접 뉴스에서 기업 관련 이벤트 확인

JSON 형식으로 출력하세요.
"""

    def get_relevant_events(self, context: dict) -> list[dict]:
        """Extract direct events from context."""
        # For DIRECT, we primarily use internal snapshot
        # but also include direct_events from external search
        direct_events = context.get("direct_events", [])

        # DIRECT agent can always run because internal snapshot is primary source
        # Return direct_events (may be empty)
        return direct_events
