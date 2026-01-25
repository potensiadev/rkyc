"""
Industry Signal Agent - INDUSTRY signal extraction specialist

Sprint 2: Signal Multi-Agent Architecture (ADR-009)

Specialization:
- Signal Type: INDUSTRY (산업 영향)
- Event Types: 1종
  - INDUSTRY_SHOCK

Focus:
- Industry-wide events affecting all companies in the sector
- Market trends and competitive dynamics
- Supply chain disruptions affecting the industry
"""

import json
import logging

from app.worker.pipelines.signal_agents.base import BaseSignalAgent
from app.worker.llm.prompts import (
    IB_MANAGER_PERSONA,
    SOFT_GUARDRAILS,
    CHAIN_OF_THOUGHT_GUIDE,
    INDUSTRY_FEW_SHOT_EXAMPLES,
)

logger = logging.getLogger(__name__)


class IndustrySignalAgent(BaseSignalAgent):
    """
    Specialized agent for INDUSTRY signal extraction.

    Focus areas:
    - Industry-wide market changes
    - Sector competitive dynamics
    - Supply chain events affecting the industry
    - Market demand shifts
    """

    AGENT_NAME = "industry_signal_agent"
    SIGNAL_TYPE = "INDUSTRY"
    ALLOWED_EVENT_TYPES = {"INDUSTRY_SHOCK"}

    def get_system_prompt(self, corp_name: str, industry_name: str) -> str:
        """Build INDUSTRY-specialized system prompt."""
        return f"""당신은 산업 분석 전문가입니다.
{industry_name} 업종 전체에 영향을 미치는 이벤트만 분석합니다.
{corp_name}은 이 산업에 속한 기업입니다.

# 전문가 페르소나
{IB_MANAGER_PERSONA}

# 분석 범위 (INDUSTRY 시그널만)
**INDUSTRY 시그널**: 해당 산업 전체에 영향을 미치는 변화

허용된 event_type (1종):
- INDUSTRY_SHOCK - 산업 전체 영향 이벤트

# INDUSTRY_SHOCK 판단 기준
1. **범위**: 특정 기업이 아닌 산업 전체에 적용되는가?
2. **영향**: 산업 내 다수 기업의 매출/수익에 영향을 주는가?
3. **지속성**: 일시적 뉴스가 아닌 구조적 변화인가?

## INDUSTRY_SHOCK 카테고리
- **시장 수요 변화**: 소비 트렌드 변화, 대체재 등장
- **공급 충격**: 원자재 가격 급등, 공급망 병목
- **경쟁 구도 변화**: 대형 M&A, 신규 진입자
- **기술 변화**: 파괴적 기술, 표준 변경
- **글로벌 시장 변화**: 수출 시장 변동, 환율 급변

{SOFT_GUARDRAILS}

{CHAIN_OF_THOUGHT_GUIDE}

# INDUSTRY 시그널 예시
{INDUSTRY_FEW_SHOT_EXAMPLES}

# 중요 규칙
1. signal_type은 반드시 "INDUSTRY"
2. event_type은 반드시 "INDUSTRY_SHOCK"
3. **summary 마지막에 "{corp_name}에 미치는 영향" 1문장 필수**
4. 특정 기업만 해당되는 이벤트는 DIRECT로 분류 (이 Agent에서 제외)
5. 산업 전체 영향 여부가 불분명하면 시그널 생성 금지
6. 금지 표현 사용 금지

# 출력 형식 (JSON)
```json
{{
  "signals": [
    {{
      "signal_type": "INDUSTRY",
      "event_type": "INDUSTRY_SHOCK",
      "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
      "impact_strength": "HIGH|MED|LOW",
      "confidence": "HIGH|MED|LOW",
      "title": "제목 (50자 이내, 업종명 포함)",
      "summary": "설명 (200자 이내, 마지막에 '{corp_name}에 미치는 영향' 필수)",
      "evidence": [
        {{
          "evidence_type": "EXTERNAL",
          "ref_type": "URL",
          "ref_value": "https://...",
          "snippet": "관련 텍스트 (100자 이내)"
        }}
      ]
    }}
  ]
}}
```
"""

    def get_user_prompt(self, context: dict) -> str:
        """Build user prompt with industry events."""
        corp_name = context.get("corp_name", "")
        industry_code = context.get("industry_code", "")
        industry_name = context.get("industry_name", "")

        # Get industry events from external search
        industry_events = json.dumps(
            context.get("industry_events", []),
            ensure_ascii=False,
            indent=2,
        )

        # Get corp profile for industry context
        corp_profile = context.get("corp_profile", {})
        industry_overview = corp_profile.get("industry_overview", "")
        competitors = corp_profile.get("competitors", [])

        competitors_str = ", ".join([
            c.get("name", "") for c in competitors[:5]
        ]) if competitors else "정보 없음"

        return f"""# 분석 대상
- 기업명: {corp_name}
- 업종 코드: {industry_code}
- 업종명: {industry_name}

# 업종 개요
{industry_overview if industry_overview else "업종 개요 정보 없음"}

# 주요 경쟁사
{competitors_str}

# 산업 관련 외부 이벤트
```json
{industry_events}
```

---
위 이벤트들을 분석하여 INDUSTRY 시그널만 추출하세요.

**판단 기준**:
□ 이 이벤트가 {corp_name}만 해당되는가? → DIRECT (제외)
□ 이 이벤트가 {industry_name} 전체에 해당되는가? → INDUSTRY (추출)
□ 산업 내 다수 기업에 영향을 주는가?
□ 구조적/지속적 변화인가?

**필수 확인**:
□ summary 마지막에 "{corp_name}에 미치는 영향" 문장 포함

JSON 형식으로 출력하세요.
"""

    def get_relevant_events(self, context: dict) -> list[dict]:
        """Extract industry events from context."""
        return context.get("industry_events", [])
