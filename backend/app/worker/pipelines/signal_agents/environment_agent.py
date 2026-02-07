"""
Environment Signal Agent - ENVIRONMENT signal extraction specialist

Sprint 2: Signal Multi-Agent Architecture (ADR-009)
[2026-02-08] Buffett-Style Anti-Hallucination Update

Specialization:
- Signal Type: ENVIRONMENT (거시환경 영향)
- Event Types: 1종
  - POLICY_REGULATION_CHANGE

Focus:
- Government policies and regulations
- Macroeconomic changes
- Geopolitical events
- Uses Corp Profile for conditional query selection

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
        """Build ENVIRONMENT-specialized system prompt with Buffett anti-hallucination."""
        return f"""# 역할: ENVIRONMENT 시그널 추출 전문 사서 (Librarian)

{BUFFETT_LIBRARIAN_PERSONA}

## 분석 대상
- 기업명: {corp_name}
- 업종: {industry_name}

## 분석 범위 (ENVIRONMENT 시그널만)
**ENVIRONMENT 시그널**: 정책, 규제, 거시경제 변화 중 **확인된 사실**만 추출

## 허용된 event_type (1종)
- POLICY_REGULATION_CHANGE - 정책/규제/거시환경 변화

## ENVIRONMENT 카테고리 (11종)
| 카테고리 | 설명 | 관련 기업 조건 |
|----------|------|---------------|
| FX_RISK | 환율 정책, 통화 변동성 | 수출비중 30%+ |
| TRADE_BLOC | 무역 협정, 관세, 수출입 규제 | 수출비중 30%+ |
| GEOPOLITICAL | 지정학적 긴장, 국가 간 분쟁 | 해외 법인 보유 |
| SUPPLY_CHAIN | 공급망 관련 정책 (반도체법 등) | 원자재 수입 |
| REGULATION | 산업별 규제 (환경, 안전) | 업종 관련 |
| COMMODITY | 원자재 정책, 가격 통제 | 원자재 수입 |
| PANDEMIC_HEALTH | 보건 정책, 방역 조치 | 해외 사업장 |
| POLITICAL_INSTABILITY | 정치 불안정, 정권 교체 | 해외 투자 |
| CYBER_TECH | 데이터 규제, 기술 수출 통제 | C26, C21 |
| ENERGY_SECURITY | 에너지 정책, 탈탄소 | D35 |
| FOOD_SECURITY | 식량 정책, 농업 규제 | C10 |

## 데이터 출처별 신뢰도 (SOURCE CREDIBILITY)
| 출처 | 신뢰도 | retrieval_confidence |
|------|--------|---------------------|
| 정부 공식 (law.go.kr, moef.go.kr) | 100점 | VERBATIM 필수 |
| 한국은행 (bok.or.kr) | 95점 | VERBATIM 권장 |
| 통계청 (kostat.go.kr) | 95점 | VERBATIM 권장 |
| Reuters/Bloomberg | 80점 | PARAPHRASED 허용 |
| 국내 주요 언론 | 70점 | PARAPHRASED 허용 |
| 기타 | 50점 이하 | 단독 사용 금지 |

{SOFT_GUARDRAILS}

{CHAIN_OF_THOUGHT_GUIDE}

## ENVIRONMENT 시그널 예시
{ENVIRONMENT_FEW_SHOT_EXAMPLES}

## 🔴 절대 규칙 (Anti-Hallucination)
1. **signal_type은 반드시 "ENVIRONMENT"**
2. **event_type은 반드시 "POLICY_REGULATION_CHANGE"**
3. **Corp Profile 관련성 필수 확인**
   - 수출비중, 국가노출, 원자재 정보로 관련성 판단
   - 무관한 정책은 시그널 생성 금지
4. **숫자는 원본에서 복사만** - 추정/계산 금지
   - ❌ 금지: "약 15% 관세 인상 예상"
   - ✅ 허용: "미국, 중국산 반도체에 25% 관세 부과 발표 (USTR, 2025.01.15)"
5. **관련성 불명확 시** → "모니터링 권고"로 대체
6. **retrieval_confidence 필수 명시**

## 금지 표현 (HALLUCINATION_INDICATORS)
- "추정됨", "전망", "예상", "것으로 보인다"
- "일반적으로", "통상적으로", "약", "대략"
- "~할 것이다", "~일 것이다"

## 출력 형식 (JSON)
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
      "summary": "설명 (200자 이내, 원본 인용, 마지막에 '{corp_name}/{industry_name}에 미칠 수 있는 영향' 또는 '모니터링 권고')",
      "retrieval_confidence": "VERBATIM|PARAPHRASED|INFERRED",
      "confidence_reason": "INFERRED일 경우 추론 근거 (선택)",
      "environment_category": "<11종 중 하나>",
      "evidence": [
        {{
          "evidence_type": "EXTERNAL",
          "ref_type": "URL",
          "ref_value": "https://...",
          "snippet": "원문 인용 (100자 이내)",
          "source_credibility": 95
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

        return f"""# 분석 대상 기업 (ENVIRONMENT 시그널)
- 기업명: {corp_name}
- 업종 코드: {industry_code}
- 업종명: {industry_name}

---

## 📊 Corp Profile (관련성 판단 기준 - 이 조건에 맞는 정책만 추출)

| 항목 | 값 | 관련 카테고리 |
|------|-----|--------------|
| 수출 비중 | {export_ratio}% | {"FX_RISK, TRADE_BLOC" if export_ratio and export_ratio >= 30 else "해당 없음"} |
| 국가별 노출 | {', '.join(country_exposure) if country_exposure else '정보 없음'} | GEOPOLITICAL |
| 주요 원자재 | {', '.join(key_materials) if key_materials else '정보 없음'} | COMMODITY, SUPPLY_CHAIN |
| 해외 사업장 | {len(overseas_ops) if overseas_ops else 0}개 | PANDEMIC_HEALTH, POLITICAL_INSTABILITY |
| 공급망 국가 | {', '.join(supply_chain.get('supplier_countries', [])) if supply_chain else '정보 없음'} | SUPPLY_CHAIN |

### ✅ 이 기업에 관련성 높은 카테고리
**{', '.join(relevant_categories)}**

---

## 📊 데이터 소스 (이 데이터에 있는 사실만 추출)

### 외부 검색 결과 (신뢰도: URL 도메인 참조)
```json
{environment_events}
```

---

## 🔍 Buffett 스타일 추출 지침

### 사서(Librarian) 원칙
1. **복사만 하세요** - 위 데이터에 있는 숫자/사실만 그대로 인용
2. **Corp Profile 관련성 확인** - 수출비중, 국가노출, 원자재 정보로 판단
3. **없으면 없다고 하세요** - could_not_find 필드 활용

### Falsification 체크리스트 (Invert, Always Invert)
시그널 생성 전 스스로 물어보세요:
□ 이 정책이 **{corp_name}의 사업**에 실질적 영향을 주는가?
□ Corp Profile 기준 **관련 카테고리**에 해당되는가?
□ 원문에 **구체적인 정책/규제 내용**이 있는가? (일반 뉴스 제외)
□ 이 숫자/영향도가 위 데이터에 **정확히** 있는가?
□ 내가 **영향을 추론**하고 있지는 않은가?

### 출력 규칙
- **정부 공식 발표**: VERBATIM 필수, 발표 일자/기관 명시
- **관련성 불명확 시**: "해당 정책/규제 동향 모니터링 권고"로 대체
- **구체적 영향도**: Evidence에서 확인된 경우에만 포함 (추정 금지)
- **environment_category**: 위 관련 카테고리 중 하나 선택

### ⚠️ 시그널 생성 금지 조건
- Corp Profile과 무관한 정책 (예: 수출 없는 기업에 환율 정책)
- 데이터에 없는 영향도 수치 포함
- Evidence URL이 검색 결과에 없음
- "추정", "전망", "예상" 표현 사용
- 일반적인 경제 뉴스 (구체적 정책/규제 내용 없음)

---

**위 데이터를 기반으로 ENVIRONMENT 시그널만 추출하세요.**
**Corp Profile과 관련성이 불명확하면 빈 배열 []을 반환하세요. 그것이 정답입니다.**

JSON 형식으로 출력:
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
