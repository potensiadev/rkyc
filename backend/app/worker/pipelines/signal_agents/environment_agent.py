"""
Environment Signal Agent - ENVIRONMENT signal extraction specialist

Sprint 2: Signal Multi-Agent Architecture (ADR-009)
[2026-02-08] Buffett-Style Anti-Hallucination Update
[2026-02-08] Sprint 1 Integration: Enhanced prompts with 37 Few-Shot examples

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

Sprint 1 Enhancements:
- 11 ENVIRONMENT Few-Shot examples (from prompts_enhanced.py)
- V2_CORE_PRINCIPLES with Closed-World Assumption
- CHAIN_OF_VERIFICATION for self-check
- 50+ forbidden pattern detection
"""

import json
import logging

from app.worker.pipelines.signal_agents.base import (
    BaseSignalAgent,
    BUFFETT_LIBRARIAN_PERSONA,
    SOURCE_CREDIBILITY,
)
# Sprint 1: Enhanced prompts
from app.worker.llm.prompts_enhanced import (
    V2_CORE_PRINCIPLES,
    STRICT_JSON_SCHEMA,
    CHAIN_OF_VERIFICATION,
    RISK_MANAGER_PERSONA,
    ENVIRONMENT_EXAMPLES,
    REJECTION_EXAMPLES,
)
# Legacy imports for backward compatibility
from app.worker.llm.prompts import (
    SOFT_GUARDRAILS,
    CHAIN_OF_THOUGHT_GUIDE,
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
        """Build ENVIRONMENT-specialized system prompt with Sprint 1 enhancements."""
        return f"""# 역할: ENVIRONMENT 시그널 추출 전문 사서 (Librarian)

{BUFFETT_LIBRARIAN_PERSONA}

## 분석 대상
- 기업명: {corp_name}
- 업종: {industry_name}

{V2_CORE_PRINCIPLES}

## 전문가 페르소나
{RISK_MANAGER_PERSONA}

## 분석 범위 (ENVIRONMENT 시그널만)
**ENVIRONMENT 시그널**: 정책, 규제, 거시경제 변화 중 **확인된 사실**만 추출

## 허용된 event_type (1종)
- POLICY_REGULATION_CHANGE - 정책/규제/거시환경 변화

## ENVIRONMENT 카테고리 (11종)
| 카테고리 | 설명 | 관련 조건 | retrieval_confidence |
|----------|------|----------|---------------------|
| FX_RISK | 환율 정책 | 수출 30%+ | VERBATIM 권장 |
| TRADE_BLOC | 무역/관세 | 수출 30%+ | VERBATIM 필수 |
| GEOPOLITICAL | 지정학 | 해외 법인 | PARAPHRASED 허용 |
| SUPPLY_CHAIN | 공급망 정책 | 원자재 수입 | VERBATIM 권장 |
| REGULATION | 산업 규제 | 업종 관련 | VERBATIM 필수 |
| COMMODITY | 원자재 정책 | 원자재 수입 | VERBATIM 권장 |
| PANDEMIC_HEALTH | 보건/방역 | 해외 사업장 | PARAPHRASED 허용 |
| POLITICAL_INSTABILITY | 정치 불안 | 해외 투자 | PARAPHRASED 허용 |
| CYBER_TECH | 기술 규제 | C26, C21 | VERBATIM 필수 |
| ENERGY_SECURITY | 에너지 정책 | D35 | VERBATIM 권장 |
| FOOD_SECURITY | 식량 정책 | C10 | VERBATIM 권장 |

## 데이터 출처별 신뢰도 (SOURCE CREDIBILITY)
| 출처 | 신뢰도 | 허용 confidence |
|------|--------|----------------|
| 정부 공식 (law.go.kr, moef.go.kr) | 100점 | HIGH |
| 한국은행 (bok.or.kr) | 95점 | HIGH |
| 통계청 (kostat.go.kr) | 95점 | HIGH |
| Reuters/Bloomberg | 80점 | MED |
| 국내 주요 언론 | 70점 | MED |
| 기타 | 50점 이하 | LOW (단독 불가) |

{STRICT_JSON_SCHEMA}

{CHAIN_OF_VERIFICATION}

## ENVIRONMENT 시그널 예시 (Sprint 1: 11개)
{ENVIRONMENT_EXAMPLES}

{REJECTION_EXAMPLES}

## 🔴 절대 규칙 (Anti-Hallucination)
1. **signal_type은 반드시 "ENVIRONMENT"**
2. **event_type은 반드시 "POLICY_REGULATION_CHANGE"**
3. **Corp Profile 관련성 필수 확인**
   - 수출비중, 국가노출, 원자재 정보로 판단
   - 무관한 정책 → 시그널 생성 금지
4. **숫자는 원본에서 복사만** - 추정/계산 금지
   - ❌ 금지: "약 15% 관세 인상 예상"
   - ✅ 허용: "미국, 중국산 반도체에 25% 관세 부과 발표 (USTR, 2025.01.15)"
5. **관련성 불명확 시** → "{corp_name}에 대한 영향 모니터링 권고"
6. **retrieval_confidence 필수 명시**
7. **기업명 필수 포함** - summary에 "{corp_name}" 포함

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
      "retrieval_confidence": "VERBATIM|PARAPHRASED|INFERRED",
      "confidence_reason": "INFERRED일 경우 추론 근거",
      "title": "제목 (50자 이내, 정책/규제명 포함)",
      "summary": "설명 (80-200자, 마지막에 '{corp_name}에 미칠 수 있는 영향' 포함)",
      "environment_category": "<11종 중 하나>",
      "evidence": [...]
    }}
  ]
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
