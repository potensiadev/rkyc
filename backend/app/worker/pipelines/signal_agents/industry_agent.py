"""
Industry Signal Agent - INDUSTRY signal extraction specialist

Sprint 2: Signal Multi-Agent Architecture (ADR-009)
[2026-02-08] Buffett-Style Anti-Hallucination Update

Specialization:
- Signal Type: INDUSTRY (산업 영향)
- Event Types: 1종
  - INDUSTRY_SHOCK

Focus:
- Industry-wide events affecting all companies in the sector
- Market trends and competitive dynamics
- Supply chain disruptions affecting the industry

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
        """Build INDUSTRY-specialized system prompt with Buffett anti-hallucination."""
        return f"""# 역할: INDUSTRY 시그널 추출 전문 사서 (Librarian)

{BUFFETT_LIBRARIAN_PERSONA}

## 분석 대상
- 기업명: {corp_name}
- 업종: {industry_name}

## 분석 범위 (INDUSTRY 시그널만)
**INDUSTRY 시그널**: 해당 산업 전체에 영향을 미치는 **확인된 사실**만 추출

## 허용된 event_type (1종)
- INDUSTRY_SHOCK - 산업 전체 영향 이벤트

## INDUSTRY_SHOCK 판단 기준 (사실 기반)
1. **범위**: 특정 기업이 아닌 산업 전체에 적용되는가? (출처에서 확인)
2. **영향**: 산업 내 다수 기업 언급이 있는가? (원문에서 확인)
3. **지속성**: 정책/규제/구조적 변화인가? (발표 주체 확인)

## INDUSTRY_SHOCK 카테고리
- **시장 수요 변화**: 소비 트렌드 변화, 대체재 등장
- **공급 충격**: 원자재 가격 급등, 공급망 병목
- **경쟁 구도 변화**: 대형 M&A, 신규 진입자
- **기술 변화**: 파괴적 기술, 표준 변경
- **글로벌 시장 변화**: 수출 시장 변동, 환율 급변

## 데이터 출처별 신뢰도 (SOURCE CREDIBILITY)
| 출처 | 신뢰도 | retrieval_confidence |
|------|--------|---------------------|
| 정부 통계 (kostat.go.kr) | 100점 | VERBATIM 필수 |
| 업종 협회/연구기관 | 90점 | VERBATIM 권장 |
| Reuters/Bloomberg | 80점 | PARAPHRASED 허용 |
| 국내 주요 언론 | 70점 | PARAPHRASED 허용 |
| 기타 | 50점 이하 | 단독 사용 금지 |

{SOFT_GUARDRAILS}

{CHAIN_OF_THOUGHT_GUIDE}

## INDUSTRY 시그널 예시
{INDUSTRY_FEW_SHOT_EXAMPLES}

## 🔴 절대 규칙 (Anti-Hallucination)
1. **signal_type은 반드시 "INDUSTRY"**
2. **event_type은 반드시 "INDUSTRY_SHOCK"**
3. **산업 전체 영향 증거 필수** - 특정 기업만 언급되면 DIRECT로 분류 (이 Agent에서 제외)
4. **숫자는 원본에서 복사만** - 추정/계산 금지
   - ❌ 금지: "업계 전반에 약 20% 영향 예상"
   - ✅ 허용: "반도체 업계 재고 18.5% 증가 (한국반도체산업협회, 2025.02)"
5. **영향 불명확 시** → "모니터링 권고"로 대체, 구체적 영향도 생성 금지
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
      "signal_type": "INDUSTRY",
      "event_type": "INDUSTRY_SHOCK",
      "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
      "impact_strength": "HIGH|MED|LOW",
      "confidence": "HIGH|MED|LOW",
      "title": "제목 (50자 이내, {industry_name} 포함)",
      "summary": "설명 (200자 이내, 원본 인용, 마지막에 '{corp_name}에 미칠 수 있는 영향' 또는 '모니터링 권고')",
      "retrieval_confidence": "VERBATIM|PARAPHRASED|INFERRED",
      "confidence_reason": "INFERRED일 경우 추론 근거 (선택)",
      "evidence": [
        {{
          "evidence_type": "EXTERNAL",
          "ref_type": "URL",
          "ref_value": "https://...",
          "snippet": "원문 인용 (100자 이내)",
          "source_credibility": 80
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

        return f"""# 분석 대상 기업 (INDUSTRY 시그널)
- 기업명: {corp_name}
- 업종 코드: {industry_code}
- 업종명: {industry_name}

---

## 📊 데이터 소스 (이 데이터에 있는 사실만 추출)

### 1. 업종 개요 (참조용)
{industry_overview if industry_overview else "업종 개요 정보 없음"}

### 2. 주요 경쟁사 (참조용)
{competitors_str}

### 3. 외부 검색 결과 (신뢰도: URL 도메인 참조)
```json
{industry_events}
```

---

## 🔍 Buffett 스타일 추출 지침

### 사서(Librarian) 원칙
1. **복사만 하세요** - 위 데이터에 있는 숫자/사실만 그대로 인용
2. **산업 전체 영향 확인** - 특정 기업만 언급되면 제외
3. **없으면 없다고 하세요** - could_not_find 필드 활용

### Falsification 체크리스트 (Invert, Always Invert)
시그널 생성 전 스스로 물어보세요:
□ 이 이벤트가 {corp_name}**만** 해당되는가? → DIRECT로 분류 (제외)
□ 이 이벤트가 {industry_name} **전체**에 해당되는가? → INDUSTRY (추출)
□ 원문에 **"업계", "산업", "전반"** 등 표현이 있는가?
□ 이 숫자가 위 데이터에 **정확히** 있는가?
□ 내가 **영향도를 추론**하고 있지는 않은가?

### 출력 규칙
- **산업 전체 영향**: 원문에 "업계", "산업 전반" 등 표현 있을 때만
- **영향 불명확 시**: "해당 업황 변화 모니터링 권고"로 대체
- **구체적 영향도**: Evidence에서 확인된 경우에만 포함 (추정 금지)

### ⚠️ 시그널 생성 금지 조건
- 특정 기업명만 언급되고 산업 전체 언급 없음
- 데이터에 없는 영향도 수치 포함
- Evidence URL이 검색 결과에 없음
- "추정", "전망", "예상" 표현 사용

---

**위 데이터를 기반으로 INDUSTRY 시그널만 추출하세요.**
**산업 전체 영향이 불명확하면 빈 배열 []을 반환하세요. 그것이 정답입니다.**

JSON 형식으로 출력:
"""

    def get_relevant_events(self, context: dict) -> list[dict]:
        """Extract industry events from context."""
        return context.get("industry_events", [])
