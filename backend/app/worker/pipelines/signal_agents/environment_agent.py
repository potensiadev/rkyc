"""
Environment Signal Agent - ENVIRONMENT signal extraction specialist

Sprint 2: Signal Multi-Agent Architecture (ADR-009)

Specialization:
- Signal Type: ENVIRONMENT (거시환경 영향)
- Event Types: 1종
  - POLICY_REGULATION_CHANGE

Focus:
- Government policies and regulations
- Macroeconomic changes
- Geopolitical events
- Uses Corp Profile for conditional query selection
"""

import json
import logging

from app.worker.pipelines.signal_agents.base import BaseSignalAgent
from app.worker.llm.prompts import (
    RISK_MANAGER_PERSONA,
    IB_MANAGER_PERSONA,
    SOFT_GUARDRAILS,
    CHAIN_OF_THOUGHT_GUIDE,
    ENVIRONMENT_FEW_SHOT_EXAMPLES,
)

logger = logging.getLogger(__name__)


class EnvironmentSignalAgent(BaseSignalAgent):
    """
    Specialized agent for ENVIRONMENT signal extraction.

    Focus areas:
    - Government policies and regulations
    - Central bank monetary policy
    - Trade policies and tariffs
    - Environmental regulations
    - Geopolitical risks

    Uses Corp Profile to:
    - Identify relevant country exposures
    - Check export dependency
    - Select relevant environment queries
    """

    AGENT_NAME = "environment_signal_agent"
    SIGNAL_TYPE = "ENVIRONMENT"
    ALLOWED_EVENT_TYPES = {"POLICY_REGULATION_CHANGE"}

    # Environment query categories
    QUERY_CATEGORIES = {
        "FX_RISK": "환율 변동 리스크",
        "TRADE_BLOC": "무역/관세 정책",
        "GEOPOLITICAL": "지정학적 리스크",
        "SUPPLY_CHAIN": "공급망 정책",
        "REGULATION": "산업 규제",
        "COMMODITY": "원자재 정책",
        "PANDEMIC_HEALTH": "보건/팬데믹",
        "POLITICAL_INSTABILITY": "정치 불안정",
        "CYBER_TECH": "사이버/기술 규제",
        "ENERGY_SECURITY": "에너지 안보",
        "FOOD_SECURITY": "식량 안보",
    }

    def get_system_prompt(self, corp_name: str, industry_name: str) -> str:
        """Build ENVIRONMENT-specialized system prompt."""
        return f"""당신은 거시환경 및 정책 분석 전문가입니다.
{corp_name}({industry_name} 업종)에 영향을 미칠 수 있는 정책/규제/거시환경 변화를 분석합니다.

# 전문가 페르소나
{RISK_MANAGER_PERSONA}

{IB_MANAGER_PERSONA}

# 분석 범위 (ENVIRONMENT 시그널만)
**ENVIRONMENT 시그널**: 정책, 규제, 거시경제 변화

허용된 event_type (1종):
- POLICY_REGULATION_CHANGE - 정책/규제/거시환경 변화

# ENVIRONMENT 카테고리
1. **FX_RISK**: 환율 정책, 통화 변동성
2. **TRADE_BLOC**: 무역 협정, 관세, 수출입 규제
3. **GEOPOLITICAL**: 지정학적 긴장, 국가 간 분쟁
4. **SUPPLY_CHAIN**: 공급망 관련 정책 (반도체법, 배터리법 등)
5. **REGULATION**: 산업별 규제 (환경, 안전, 인허가)
6. **COMMODITY**: 원자재 정책, 가격 통제
7. **PANDEMIC_HEALTH**: 보건 정책, 방역 조치
8. **POLITICAL_INSTABILITY**: 정치 불안정, 정권 교체 리스크
9. **CYBER_TECH**: 데이터 규제, 기술 수출 통제
10. **ENERGY_SECURITY**: 에너지 정책, 탈탄소
11. **FOOD_SECURITY**: 식량 정책, 농업 규제

# 기업별 관련성 판단 (Corp Profile 기반)
- 수출비중 30%+ → FX_RISK, TRADE_BLOC 관련성 높음
- 해외 법인 보유 → GEOPOLITICAL, PANDEMIC 관련성 높음
- 원자재 수입 → COMMODITY, SUPPLY_CHAIN 관련성 높음
- 업종별 특성:
  - 반도체(C26), 제약(C21) → CYBER_TECH, REGULATION 높음
  - 에너지(D35) → ENERGY_SECURITY 높음
  - 식품(C10) → FOOD_SECURITY 높음

{SOFT_GUARDRAILS}

{CHAIN_OF_THOUGHT_GUIDE}

# ENVIRONMENT 시그널 예시
{ENVIRONMENT_FEW_SHOT_EXAMPLES}

# 중요 규칙
1. signal_type은 반드시 "ENVIRONMENT"
2. event_type은 반드시 "POLICY_REGULATION_CHANGE"
3. **summary에 "{corp_name}/{industry_name}에 미치는 영향 가능성" 1문장 필수**
4. 기업/산업 특성과 무관한 일반 정책은 제외
5. 불확실성 높으면 confidence LOW로 설정
6. 금지 표현 사용 금지

# 출력 형식 (JSON)
```json
{{
  "signals": [
    {{
      "signal_type": "ENVIRONMENT",
      "event_type": "POLICY_REGULATION_CHANGE",
      "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
      "impact_strength": "HIGH|MED|LOW",
      "confidence": "HIGH|MED|LOW",
      "title": "제목 (50자 이내, 정책/규제명 포함)",
      "summary": "설명 (200자 이내, '{corp_name}/{industry_name}에 미치는 영향 가능성' 필수)",
      "evidence": [
        {{
          "evidence_type": "EXTERNAL",
          "ref_type": "URL",
          "ref_value": "https://...",
          "snippet": "관련 텍스트 (100자 이내)"
        }}
      ],
      "environment_category": "<카테고리>"
    }}
  ]
}}
```
"""

    def get_user_prompt(self, context: dict) -> str:
        """Build user prompt with environment events and corp profile."""
        corp_name = context.get("corp_name", "")
        industry_code = context.get("industry_code", "")
        industry_name = context.get("industry_name", "")

        # Get environment events from external search
        environment_events = json.dumps(
            context.get("environment_events", []),
            ensure_ascii=False,
            indent=2,
        )

        # Get corp profile for relevance filtering
        corp_profile = context.get("corp_profile", {})

        # Extract relevant profile data for environment analysis
        export_ratio = corp_profile.get("export_ratio_pct", 0)
        country_exposure = corp_profile.get("country_exposure", [])
        key_materials = corp_profile.get("key_materials", [])
        overseas_ops = corp_profile.get("overseas_operations", [])
        supply_chain = corp_profile.get("supply_chain", {})

        # Determine relevant categories based on profile
        relevant_categories = self._get_relevant_categories(
            export_ratio=export_ratio,
            country_exposure=country_exposure,
            key_materials=key_materials,
            overseas_ops=overseas_ops,
            industry_code=industry_code,
        )

        return f"""# 분석 대상
- 기업명: {corp_name}
- 업종 코드: {industry_code}
- 업종명: {industry_name}

# 기업 프로필 (관련성 판단용)
- 수출 비중: {export_ratio}%
- 국가별 노출: {', '.join(country_exposure) if country_exposure else '정보 없음'}
- 주요 원자재: {', '.join(key_materials) if key_materials else '정보 없음'}
- 해외 사업장: {len(overseas_ops) if overseas_ops else 0}개
- 공급망 국가: {', '.join(supply_chain.get('supplier_countries', [])) if supply_chain else '정보 없음'}

# 관련성 높은 ENVIRONMENT 카테고리
{', '.join(relevant_categories)}

# 거시환경/정책 관련 외부 이벤트
```json
{environment_events}
```

---
위 이벤트들을 분석하여 ENVIRONMENT 시그널만 추출하세요.

**판단 기준**:
□ 이 정책/규제가 {corp_name}의 사업에 실질적 영향을 주는가?
□ 기업 프로필 기반으로 관련성이 있는가? (수출비중, 국가노출, 원자재 등)
□ 일반적인 뉴스인가, 구체적인 정책/규제 변화인가?

**필수 확인**:
□ summary에 "{corp_name}/{industry_name}에 미치는 영향 가능성" 문장 포함
□ 관련 카테고리 명시

JSON 형식으로 출력하세요.
"""

    def get_relevant_events(self, context: dict) -> list[dict]:
        """Extract environment events from context."""
        return context.get("environment_events", [])

    def _get_relevant_categories(
        self,
        export_ratio: float,
        country_exposure: list,
        key_materials: list,
        overseas_ops: list,
        industry_code: str,
    ) -> list[str]:
        """
        Determine relevant environment categories based on corp profile.

        This implements conditional query selection from PRD-Corp-Profiling.
        """
        categories = []

        # Export ratio based
        if export_ratio and export_ratio >= 30:
            categories.extend(["FX_RISK", "TRADE_BLOC"])

        # Country exposure based
        if country_exposure:
            countries_lower = [c.lower() for c in country_exposure]
            if any("중국" in c or "china" in c for c in countries_lower):
                categories.extend(["GEOPOLITICAL", "SUPPLY_CHAIN", "REGULATION"])
            if any("미국" in c or "usa" in c or "us" in c for c in countries_lower):
                categories.extend(["GEOPOLITICAL", "REGULATION", "TRADE_BLOC"])

        # Key materials based
        if key_materials:
            categories.extend(["COMMODITY", "SUPPLY_CHAIN"])

        # Overseas operations based
        if overseas_ops:
            categories.extend(["GEOPOLITICAL", "PANDEMIC_HEALTH", "POLITICAL_INSTABILITY"])

        # Industry code based
        if industry_code:
            if industry_code in ["C26", "C21"]:  # 반도체, 제약
                categories.append("CYBER_TECH")
            if industry_code == "D35":  # 에너지
                categories.append("ENERGY_SECURITY")
            if industry_code == "C10":  # 식품
                categories.append("FOOD_SECURITY")

        # Remove duplicates while preserving order
        seen = set()
        unique_categories = []
        for cat in categories:
            if cat not in seen:
                seen.add(cat)
                unique_categories.append(cat)

        # If no specific categories, return general ones
        if not unique_categories:
            return ["REGULATION", "GEOPOLITICAL", "TRADE_BLOC"]

        return unique_categories
