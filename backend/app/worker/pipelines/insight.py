"""
Insight Pipeline Stage
Stage 8: Generate final briefing using LLM with similar case search
+ Pre-generate Loan Insight and save to DB
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy import text

from app.worker.db import get_sync_db
from app.worker.llm.service import LLMService
from app.worker.llm.prompts import INSIGHT_GENERATION_PROMPT
from app.worker.llm.exceptions import AllProvidersFailedError
from app.worker.llm.embedding import get_embedding_service, EmbeddingError

logger = logging.getLogger(__name__)

# Loan Insight 프롬프트 (v3.0 - 은행 기업뱅킹 전문가 관점 + Banking Data 통합)
LOAN_INSIGHT_SYSTEM_PROMPT = """당신은 은행의 '기업 여신 심사역(Credit Officer)'이자 '기업뱅킹 전문가'입니다.
주어진 기업의 프로필, **당행 거래 현황(Banking Data)**, 그리고 감지된 시그널을 바탕으로 여신 의사결정을 위한 '보조 의견서'를 작성해야 합니다.

# 핵심 역할
- **당행 관점 분석**: 외부 시그널이 "당행 여신 포트폴리오"에 미치는 영향을 구체적으로 분석
- 여신 금액, 담보 현황, 환헤지 비율 등 실제 숫자를 인용하여 근거 기반 분석
- 심사역이 놓칠 수 있는 '부실 징후'나 '영업 기회'를 포착하여 브리핑

# 분석 대상 기업
기업명: {corp_name}
업종: {industry_name}

# 기업 프로필 (외부 수집 정보)
{profile_context}

# 당행 거래 현황 (Banking Data) ⭐ 핵심 참고 자료
{banking_context}

# 출력 요구사항 (JSON)
다음 JSON 형식으로 출력하십시오. 마크다운 코드블록 없이 순수 JSON만 출력하세요.

{{
  "executive_summary": "2-3문장. 첫 문장은 기업+주요사업 요약, 둘째 문장은 당행 여신 규모와 핵심 리스크/기회 요약. 100자 내외.",
  "stance_level": "CAUTION | MONITORING | STABLE | POSITIVE",
  "stance_label": "한글 라벨 (예: 주의 요망, 모니터링 필요, 중립/안정적, 긍정적)",
  "narrative": "종합 의견 서술 (3-4문장). '당행 여신 XXX억원' 등 구체적 숫자를 인용하여 은행 관점의 결론 도출.",
  "key_risks": [
    "은행 관점 핵심 리스크 1 (예: '당행 여신 1,200억원이 환율 변동에 노출됨. 환헤지율 35%로 권고치 50% 미달')",
    "은행 관점 핵심 리스크 2 (예: 'LTV 75%로 담보 여력 부족. 추가 담보 확보 검토 권고')"
  ],
  "key_opportunities": [
    "은행 관점 핵심 기회 1 (예: '수출 증가로 외환 수수료 수익 확대 기회. 현재 무역금융 이용액 대비 30% 증대 가능')",
    "은행 관점 핵심 기회 2 (예: '담보물 인근 인프라 개발로 감정가 상승 예상. 여신 한도 확대 검토 가능')"
  ],
  "mitigating_factors": [
    "리스크 상쇄 요인 (예: '담보 커버리지 120%로 여신 대비 충분한 안전마진 확보')"
  ],
  "action_items": [
    "심사역 확인사항 (예: '환헤지 계약 현황 확인 및 헤지 비율 50%까지 상향 권유')",
    "심사역 확인사항 (예: '분기별 담보 재평가 일정 확인')"
  ]
}}

# 판단 가이드 (은행 관점)
1. **CAUTION (주의 요망)**:
   - 연체 플래그 ON, 내부등급 HIGH RISK
   - LTV 80% 초과, 환헤지율 30% 미만
   - 주요 거래처 이탈, 경영권 분쟁 등 치명적 시그널

2. **MONITORING (모니터링 필요)**:
   - LTV 60-80%, 환헤지율 30-50%
   - 산업 불황, 원자재가 상승 등 하방 압력
   - 한도 유지하되 분기별 점검 필요

3. **STABLE (중립/안정적)**:
   - LTV 60% 이하, 환헤지율 50% 이상
   - 리스크/기회가 상쇄됨
   - 통상적인 심사 진행

4. **POSITIVE (긍정적)**:
   - 대형 수주, 실적 개선으로 현금흐름 증가
   - 담보가치 상승, 신용등급 개선
   - 여신 한도 확대, 신규 상품 제안 기회

# 작성 규칙 (필수)
- **숫자 인용 필수**: "당행 여신 XXX억원", "LTV XX%", "환헤지율 XX%" 등 Banking Data의 실제 숫자를 반드시 인용
- **당행 관점 필수**: 일반적인 기업 분석이 아닌, "당행 포트폴리오에 미치는 영향" 관점으로 작성
- **기회 요인 균형**: 리스크만 나열하지 말고, 여신 확대/수수료 수익/신규 상품 등 영업 기회도 균형있게 제시
- **단정적 표현 금지**: "~로 추정됨", "~가능성 있음", "검토 권고" 사용
"""


class InsightPipeline:
    """
    Stage 8: INSIGHT - Generate final briefing summary with similar case search

    Uses LLM to generate a concise executive briefing
    summarizing all detected signals and their implications.

    Enhanced with:
    - Similar case search using embedding vectors
    - Past case context for better insights
    """

    def __init__(self):
        self.llm = LLMService()
        self.embedding_service = get_embedding_service()

    def execute(self, signals: list[dict], context: dict) -> str:
        """
        Execute insight generation stage.

        Args:
            signals: List of validated signal dicts
            context: Unified context from ContextPipeline

        Returns:
            Generated insight/briefing string
        """
        corp_id = context.get("corp_id", "")
        corp_name = context.get("corp_name", "")
        industry_name = context.get("industry_name", context.get("industry_code", ""))
        # Profile 정보 (CorpProfilingPipeline에서 context에 추가됨)
        profile = context.get("profile", None)
        # Banking Data (v3.0 - 은행 기업뱅킹 전문가 관점)
        banking_data = context.get("banking_data", None)

        logger.info(f"INSIGHT stage starting for corp_id={corp_id}, banking_data={'있음' if banking_data else '없음'}")

        # Handle no signals case
        if not signals:
            insight = self._generate_no_signals_insight(corp_name)
            # 시그널이 없어도 기본 Loan Insight 저장 (banking_data 포함)
            self._save_default_loan_insight(corp_id, corp_name, profile, banking_data)
            logger.info("INSIGHT stage completed (no signals)")
            return insight

        # Find similar past cases for context
        similar_cases = []
        if self.embedding_service.is_available:
            try:
                similar_cases = self._find_similar_cases(signals)
                logger.info(f"Found {len(similar_cases)} similar past cases")
            except Exception as e:
                logger.warning(f"Similar case search failed (non-fatal): {e}")

        try:
            insight = self._generate_insight(signals, context, similar_cases)
            logger.info(f"INSIGHT stage completed: {len(insight)} chars")

            # Loan Insight 생성 및 DB 저장 (v3.0: banking_data 포함)
            self._generate_and_save_loan_insight(
                corp_id, corp_name, industry_name, signals, profile, banking_data
            )

            return insight

        except AllProvidersFailedError as e:
            logger.error(f"LLM failed for insight generation: {e}")
            # Fallback loan insight도 저장 (banking_data 포함)
            self._save_fallback_loan_insight(corp_id, corp_name, signals, profile, banking_data)
            return self._generate_fallback_insight(signals, corp_name)

        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            self._save_fallback_loan_insight(corp_id, corp_name, signals, profile, banking_data)
            return self._generate_fallback_insight(signals, corp_name)

    def _generate_insight(
        self,
        signals: list[dict],
        context: dict,
        similar_cases: list[dict] = None,
    ) -> str:
        """Generate insight using LLM with similar case context."""
        # Build signal summary for prompt
        signal_summary = self._build_signal_summary(signals)

        # Build similar cases summary
        similar_cases_summary = ""
        if similar_cases:
            similar_cases_summary = self._build_similar_cases_summary(similar_cases)

        user_prompt = INSIGHT_GENERATION_PROMPT.format(
            corp_name=context.get("corp_name", ""),
            industry_code=context.get("industry_code", ""),
            industry_name=context.get("industry_name", ""),
            signal_count=len(signals),
            signals_summary=signal_summary,
        )

        # Add similar cases to prompt if available
        if similar_cases_summary:
            user_prompt += f"\n\n### 유사 과거 케이스 참고\n{similar_cases_summary}"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior corporate analyst providing executive briefings. "
                    "Generate concise, actionable insights in Korean. "
                    "IMPORTANT: Cover both RISK and OPPORTUNITY factors with equal emphasis. "
                    "Opportunities like revenue growth, new products, factory expansion, technology investment "
                    "are valuable signals for banks to identify credit expansion opportunities. "
                    "Use probabilistic language: '~로 추정됨', '~가능성 있음', '검토 권고'. "
                    "Avoid definitive statements like '반드시', '즉시 조치 필요'. "
                    "If similar past cases are provided, reference them to provide historical context."
                ),
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]

        # Use call_with_fallback for text response
        insight = self.llm.call_with_fallback(
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
        )

        return insight.strip()

    def _find_similar_cases(
        self,
        signals: list[dict],
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[dict]:
        """
        Find similar past cases using embedding similarity.

        Args:
            signals: Current signals to find similar cases for
            limit: Maximum number of similar cases to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of similar case dicts with similarity scores
        """
        if not signals:
            return []

        # Use the most significant signal for case search
        # (typically HIGH impact or first signal)
        high_impact = [s for s in signals if s.get("impact_strength") == "HIGH"]
        target_signal = high_impact[0] if high_impact else signals[0]

        # Generate embedding for target signal
        combined_text = f"""
Signal Type: {target_signal.get('signal_type', '')}
Event Type: {target_signal.get('event_type', '')}
Title: {target_signal.get('title', '')}
Summary: {target_signal.get('summary', '')}
""".strip()

        try:
            embedding = self.embedding_service.embed_text(combined_text)
            if not embedding:
                return []

            # Query similar cases from database
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            with get_sync_db() as db:
                # Use the helper function from migration
                # Note: Use CAST() instead of :: to avoid SQLAlchemy parameter binding conflicts
                result = db.execute(
                    text("""
                        SELECT
                            case_id,
                            corp_id,
                            industry_code,
                            signal_type,
                            event_type,
                            summary,
                            1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                        FROM rkyc_case_index
                        WHERE embedding IS NOT NULL
                          AND 1 - (embedding <=> CAST(:embedding AS vector)) >= :threshold
                        ORDER BY embedding <=> CAST(:embedding AS vector)
                        LIMIT :limit
                    """),
                    {
                        "embedding": embedding_str,
                        "threshold": similarity_threshold,
                        "limit": limit,
                    }
                )

                cases = []
                for row in result:
                    cases.append({
                        "case_id": str(row.case_id),
                        "corp_id": row.corp_id,
                        "industry_code": row.industry_code,
                        "signal_type": row.signal_type,
                        "event_type": row.event_type,
                        "summary": row.summary,
                        "similarity": round(row.similarity, 3),
                    })

                return cases

        except EmbeddingError as e:
            logger.warning(f"Embedding generation failed for case search: {e}")
            return []
        except Exception as e:
            logger.warning(f"Similar case search query failed: {e}")
            return []

    def _build_similar_cases_summary(self, cases: list[dict]) -> str:
        """Build summary text for similar cases."""
        if not cases:
            return ""

        lines = []
        for i, case in enumerate(cases, 1):
            similarity_pct = int(case.get("similarity", 0) * 100)
            lines.append(
                f"{i}. [{case.get('signal_type', 'N/A')}] {case.get('event_type', 'N/A')} "
                f"(유사도 {similarity_pct}%)\n"
                f"   - 업종: {case.get('industry_code', 'N/A')}\n"
                f"   - 요약: {case.get('summary', 'N/A')[:100]}..."
            )

        return "\n".join(lines)

    def _build_signal_summary(self, signals: list[dict]) -> str:
        """Build signal summary for LLM prompt."""
        lines = []

        # Group by impact direction
        risk_signals = [s for s in signals if s.get("impact_direction") == "RISK"]
        opp_signals = [s for s in signals if s.get("impact_direction") == "OPPORTUNITY"]
        neutral_signals = [s for s in signals if s.get("impact_direction") == "NEUTRAL"]

        # OPPORTUNITY 시그널을 먼저 표시 (기회 요인 강조)
        if opp_signals:
            lines.append(f"## 🚀 기회 시그널 ({len(opp_signals)}건) - 성장/투자/수익 개선 기회")
            for s in opp_signals:
                strength = s.get("impact_strength", "MED")
                event_type = s.get("event_type", "")
                opp_category = self._categorize_opportunity(event_type, s.get("title", ""), s.get("summary", ""))
                lines.append(f"- [{strength}] [{opp_category}] {s.get('title', '')}: {s.get('summary', '')[:100]}")

        if risk_signals:
            lines.append(f"\n## ⚠️ 리스크 시그널 ({len(risk_signals)}건)")
            for s in risk_signals:
                strength = s.get("impact_strength", "MED")
                lines.append(f"- [{strength}] {s.get('title', '')}: {s.get('summary', '')[:100]}")

        if neutral_signals:
            lines.append(f"\n## 📋 참고 시그널 ({len(neutral_signals)}건)")
            for s in neutral_signals:
                lines.append(f"- {s.get('title', '')}: {s.get('summary', '')[:100]}")

        return "\n".join(lines)

    def _categorize_opportunity(self, event_type: str, title: str, summary: str) -> str:
        """Categorize opportunity signal for better context."""
        text = f"{title} {summary}".lower()

        # 카테고리 매핑
        if any(kw in text for kw in ["매출", "실적", "영업이익", "순이익", "흑자", "수익"]):
            return "실적개선"
        elif any(kw in text for kw in ["공장", "증설", "설비", "투자", "확장", "신규 사업장"]):
            return "성장투자"
        elif any(kw in text for kw in ["신제품", "신기술", "특허", "개발", "혁신", "r&d"]):
            return "기술혁신"
        elif any(kw in text for kw in ["수주", "계약", "고객", "시장", "해외", "진출"]):
            return "시장확대"
        elif any(kw in text for kw in ["부채", "유동성", "재무", "신용등급", "건전성"]):
            return "재무개선"
        elif any(kw in text for kw in ["정책", "지원", "보조금", "세제", "규제 완화"]):
            return "정책수혜"
        elif any(kw in text for kw in ["담보", "자산", "부동산", "특허 가치"]):
            return "담보강화"
        elif any(kw in text for kw in ["인수", "합병", "제휴", "파트너", "합작"]):
            return "전략제휴"
        elif any(kw in text for kw in ["esg", "환경", "지배구조", "지속가능"]):
            return "ESG개선"
        else:
            return "기회요인"

    def _generate_no_signals_insight(self, corp_name: str) -> str:
        """Generate insight when no signals detected."""
        return (
            f"{corp_name}에 대한 분석 결과, 새로운 시그널이 발견되지 않았습니다. "
            "현재 기준으로 특별한 리스크 요인 및 기회 요인은 관찰되지 않으나, "
            "지속적인 모니터링이 권고됩니다."
        )

    def _generate_fallback_insight(self, signals: list[dict], corp_name: str) -> str:
        """Generate basic insight without LLM (fallback)."""
        risk_count = sum(1 for s in signals if s.get("impact_direction") == "RISK")
        opp_count = sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY")
        high_count = sum(1 for s in signals if s.get("impact_strength") == "HIGH")

        insight_parts = [f"{corp_name}에 대해 {len(signals)}개의 시그널이 감지되었습니다."]

        # 기회 시그널을 먼저 언급 (긍정적 요인 강조)
        if opp_count > 0:
            insight_parts.append(f"기회 시그널 {opp_count}건 (성장/투자/실적개선 기회)")
        if risk_count > 0:
            insight_parts.append(f"리스크 시그널 {risk_count}건")
        if high_count > 0:
            insight_parts.append(f"(HIGH 강도 {high_count}건 포함)")

        # 기회 시그널이 있으면 여신 확대 기회 언급
        if opp_count > 0:
            insight_parts.append("기회 시그널에 대해서는 여신 확대 및 신규 상품 제안 검토가 권고됩니다.")

        insight_parts.append("상세 내용은 시그널 목록을 참조하시기 바랍니다.")

        return " ".join(insight_parts)

    # ============================================================
    # Loan Insight Generation & Storage
    # ============================================================

    def _generate_and_save_loan_insight(
        self,
        corp_id: str,
        corp_name: str,
        industry_name: str,
        signals: List[Dict[str, Any]],
        profile: Optional[Dict[str, Any]] = None,
        banking_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Generate Loan Insight via LLM and save to DB."""
        try:
            # 시그널 통계
            risk_count = sum(1 for s in signals if s.get("impact_direction") == "RISK")
            opp_count = sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY")

            # 시그널 컨텍스트 포맷
            signals_context = self._format_signals_for_loan_insight(signals)

            # 프로필 컨텍스트 포맷
            profile_context = self._format_profile_for_loan_insight(profile, corp_name)

            # Banking Data 컨텍스트 포맷 (v3.0 신규)
            banking_context = self._format_banking_data_for_loan_insight(banking_data, corp_name)

            # LLM 호출
            system_prompt = LOAN_INSIGHT_SYSTEM_PROMPT.format(
                corp_name=corp_name,
                industry_name=industry_name,
                profile_context=profile_context,
                banking_context=banking_context,
            )

            user_prompt = f"""다음 시그널을 분석하여 **은행 관점**의 여신 참고 의견을 작성해 주세요.
Banking Data의 실제 숫자(여신 금액, LTV, 환헤지율 등)를 반드시 인용하여 구체적으로 분석하세요.

[감지된 시그널 목록]
{signals_context}
"""

            response_json = self.llm.call_with_json_response(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )

            # DB 저장
            self._save_loan_insight_to_db(
                corp_id=corp_id,
                stance_level=response_json.get("stance_level", "STABLE"),
                stance_label=response_json.get("stance_label", "중립/안정적"),
                executive_summary=response_json.get("executive_summary", ""),
                narrative=response_json.get("narrative", ""),
                key_risks=response_json.get("key_risks", []),
                key_opportunities=response_json.get("key_opportunities", []),
                mitigating_factors=response_json.get("mitigating_factors", []),
                action_items=response_json.get("action_items", []),
                signal_count=len(signals),
                risk_count=risk_count,
                opportunity_count=opp_count,
                generation_model=self.llm.last_successful_model,
                is_fallback=False,
            )

            logger.info(f"Loan Insight saved for corp_id={corp_id}, stance={response_json.get('stance_level')}")

        except Exception as e:
            logger.error(f"Failed to generate Loan Insight via LLM: {e}")
            # Fallback 저장 (banking_data 포함)
            self._save_fallback_loan_insight(corp_id, corp_name, signals, profile, banking_data)

    def _save_fallback_loan_insight(
        self,
        corp_id: str,
        corp_name: str,
        signals: List[Dict[str, Any]],
        profile: Optional[Dict[str, Any]] = None,
        banking_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save rule-based fallback Loan Insight with Banking Data."""
        risk_count = sum(1 for s in signals if s.get("impact_direction") == "RISK")
        opp_count = sum(1 for s in signals if s.get("impact_direction") == "OPPORTUNITY")
        high_risk_count = sum(
            1 for s in signals
            if s.get("impact_direction") == "RISK" and s.get("impact_strength") == "HIGH"
        )

        # 기본 executive_summary 생성
        business_summary = ""
        if profile:
            business_summary = profile.get("business_summary") or profile.get("business_model") or ""
        executive_summary = f"{corp_name}은(는) {business_summary[:50]}..." if business_summary else f"{corp_name}에 대한 분석 결과입니다."

        # Banking Data에서 핵심 지표 추출
        loan_exposure_str = ""
        ltv_str = ""
        hedge_ratio_str = ""
        if banking_data:
            loan = banking_data.get("loan_exposure", {})
            if loan.get("total_exposure_krw"):
                loan_exposure_str = f"당행 여신 {loan['total_exposure_krw'] / 1_0000_0000:.0f}억원"

            collateral = banking_data.get("collateral_detail", {})
            if collateral.get("avg_ltv"):
                ltv_str = f"LTV {collateral['avg_ltv']}%"

            trade = banking_data.get("trade_finance", {})
            fx = trade.get("fx_exposure", {})
            if fx.get("hedge_ratio") is not None:
                hedge_ratio_str = f"환헤지율 {fx['hedge_ratio']}%"

        # Rule-based stance determination (Banking Data 기반 강화)
        key_risks = []
        key_opportunities = []

        # Banking Data 기반 리스크 추가
        if banking_data:
            risk_alerts = banking_data.get("risk_alerts", [])
            for alert in risk_alerts[:2]:
                key_risks.append(f"당행 시스템 감지: {alert.get('title', '알림')}")

            opp_signals = banking_data.get("opportunity_signals", [])
            for opp in opp_signals[:2]:
                if isinstance(opp, str):
                    key_opportunities.append(f"당행 시스템 감지: {opp}")
                elif isinstance(opp, dict):
                    key_opportunities.append(f"당행 시스템 감지: {opp.get('title', opp)}")

        if high_risk_count > 0 or risk_count > (opp_count * 2):
            stance_level = "CAUTION"
            stance_label = "주의 요망"
            narrative = f"다수의 리스크 시그널이 감지되었습니다. {loan_exposure_str} 관련 모니터링이 필요합니다."
            key_risks.append("자동 산정: High Risk 시그널 감지됨" if high_risk_count > 0 else "자동 산정: Risk 시그널 다수")
            executive_summary += f" {loan_exposure_str} 관련 리스크 {risk_count}건 감지."
        elif risk_count > opp_count:
            stance_level = "MONITORING"
            stance_label = "모니터링 필요"
            narrative = f"일부 리스크 요인이 존재합니다. {loan_exposure_str}, {ltv_str} 관련 모니터링이 권장됩니다."
            key_risks.append("자동 산정: 일부 Risk 시그널 존재")
            executive_summary += f" {loan_exposure_str} 모니터링 권장."
        elif opp_count > risk_count:
            stance_level = "POSITIVE"
            stance_label = "긍정적"
            narrative = f"기회 시그널이 다수 감지되었습니다. {loan_exposure_str} 한도 확대 검토 가능성이 있습니다."
            key_opportunities.append("자동 산정: 기회 시그널 다수 감지 - 여신 확대 검토 권고")
            executive_summary += f" {loan_exposure_str} 확대 검토 가능."
        else:
            stance_level = "STABLE"
            stance_label = "중립/안정적"
            narrative = f"특이한 시그널이 감지되지 않았습니다. {loan_exposure_str}은(는) 현재 안정적입니다."
            executive_summary += f" {loan_exposure_str} 안정적."

        self._save_loan_insight_to_db(
            corp_id=corp_id,
            stance_level=stance_level,
            stance_label=stance_label,
            executive_summary=executive_summary,
            narrative=narrative,
            key_risks=key_risks,
            key_opportunities=key_opportunities,
            mitigating_factors=[f"담보 커버리지 양호 ({ltv_str})" if ltv_str else ""],
            action_items=["전체 시그널 목록 수동 검토 필요"] if risk_count > 0 else [],
            signal_count=len(signals),
            risk_count=risk_count,
            opportunity_count=opp_count,
            generation_model=None,
            is_fallback=True,
        )

        logger.info(f"Fallback Loan Insight saved for corp_id={corp_id}")

    def _save_default_loan_insight(
        self,
        corp_id: str,
        corp_name: str,
        profile: Optional[Dict[str, Any]] = None,
        banking_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save default Loan Insight when no signals detected (with Banking Data)."""
        # 기본 executive_summary 생성
        business_summary = ""
        if profile:
            business_summary = profile.get("business_summary") or profile.get("business_model") or ""

        # Banking Data에서 핵심 지표 추출
        loan_exposure_str = ""
        key_risks = []
        key_opportunities = []
        mitigating_factors = []

        if banking_data:
            loan = banking_data.get("loan_exposure", {})
            if loan.get("total_exposure_krw"):
                loan_exposure_str = f"당행 여신 {loan['total_exposure_krw'] / 1_0000_0000:.0f}억원"

            collateral = banking_data.get("collateral_detail", {})
            if collateral.get("avg_ltv"):
                ltv = collateral["avg_ltv"]
                if ltv < 60:
                    mitigating_factors.append(f"담보 커버리지 양호 (LTV {ltv}%)")
                elif ltv >= 80:
                    key_risks.append(f"LTV {ltv}%로 담보 여력 부족. 추가 담보 확보 검토 권고")

            trade = banking_data.get("trade_finance", {})
            fx = trade.get("fx_exposure", {})
            if fx.get("hedge_ratio") is not None:
                hedge = fx["hedge_ratio"]
                if hedge < 30:
                    key_risks.append(f"환헤지율 {hedge}%로 권고치 50% 대비 크게 미달. 환리스크 관리 필요")
                elif hedge < 50:
                    key_risks.append(f"환헤지율 {hedge}%로 권고치 50% 미달. 헤지 비율 상향 권유")

            # 당행 시스템 Risk Alerts / Opportunities
            risk_alerts = banking_data.get("risk_alerts", [])
            for alert in risk_alerts[:2]:
                key_risks.append(f"당행 시스템 감지: {alert.get('title', '알림')}")

            opp_signals = banking_data.get("opportunity_signals", [])
            for opp in opp_signals[:2]:
                if isinstance(opp, str):
                    key_opportunities.append(f"당행 영업기회: {opp}")
                elif isinstance(opp, dict):
                    key_opportunities.append(f"당행 영업기회: {opp.get('title', opp)}")

        if business_summary:
            executive_summary = f"{corp_name}은(는) {business_summary[:60]}. {loan_exposure_str}. 현재 특이 시그널 없음."
        else:
            executive_summary = f"{corp_name}의 {loan_exposure_str}. 현재 특이 시그널이 감지되지 않았습니다."

        narrative = f"{corp_name}에 대해 새로운 외부 시그널이 발견되지 않았습니다. {loan_exposure_str}은(는) 현재 기준으로 안정적입니다."
        if key_risks:
            narrative += f" 다만, {len(key_risks)}건의 당행 시스템 알림이 있어 확인이 필요합니다."

        self._save_loan_insight_to_db(
            corp_id=corp_id,
            stance_level="STABLE" if not key_risks else "MONITORING",
            stance_label="중립/안정적" if not key_risks else "모니터링 필요",
            executive_summary=executive_summary,
            narrative=narrative,
            key_risks=key_risks,
            key_opportunities=key_opportunities,
            mitigating_factors=mitigating_factors,
            action_items=["당행 시스템 Risk Alert 확인"] if key_risks else [],
            signal_count=0,
            risk_count=len(key_risks),
            opportunity_count=len(key_opportunities),
            generation_model=None,
            is_fallback=False,
        )

        logger.info(f"Default Loan Insight saved for corp_id={corp_id} (banking_data={'있음' if banking_data else '없음'})")

    def _save_loan_insight_to_db(
        self,
        corp_id: str,
        stance_level: str,
        stance_label: str,
        executive_summary: str,
        narrative: str,
        key_risks: List[str],
        key_opportunities: List[str],
        mitigating_factors: List[str],
        action_items: List[str],
        signal_count: int,
        risk_count: int,
        opportunity_count: int,
        generation_model: Optional[str],
        is_fallback: bool,
    ) -> None:
        """Save or update Loan Insight in DB (UPSERT)."""
        import json

        # Color mapping
        color_map = {
            "CAUTION": "red",
            "MONITORING": "orange",
            "STABLE": "green",
            "POSITIVE": "blue",
        }
        stance_color = color_map.get(stance_level, "grey")

        # TTL: 7 days
        expires_at = datetime.utcnow() + timedelta(days=7)

        try:
            with get_sync_db() as db:
                # UPSERT using ON CONFLICT
                db.execute(
                    text("""
                        INSERT INTO rkyc_loan_insight (
                            insight_id, corp_id, stance_level, stance_label, stance_color,
                            executive_summary, narrative, key_risks, key_opportunities, mitigating_factors, action_items,
                            signal_count, risk_count, opportunity_count,
                            generation_model, generation_prompt_version, is_fallback,
                            generated_at, expires_at
                        ) VALUES (
                            :insight_id, :corp_id, :stance_level, :stance_label, :stance_color,
                            :executive_summary, :narrative, CAST(:key_risks AS jsonb), CAST(:key_opportunities AS jsonb), CAST(:mitigating_factors AS jsonb), CAST(:action_items AS jsonb),
                            :signal_count, :risk_count, :opportunity_count,
                            :generation_model, :generation_prompt_version, :is_fallback,
                            NOW(), :expires_at
                        )
                        ON CONFLICT (corp_id) DO UPDATE SET
                            stance_level = EXCLUDED.stance_level,
                            stance_label = EXCLUDED.stance_label,
                            stance_color = EXCLUDED.stance_color,
                            executive_summary = EXCLUDED.executive_summary,
                            narrative = EXCLUDED.narrative,
                            key_risks = EXCLUDED.key_risks,
                            key_opportunities = EXCLUDED.key_opportunities,
                            mitigating_factors = EXCLUDED.mitigating_factors,
                            action_items = EXCLUDED.action_items,
                            signal_count = EXCLUDED.signal_count,
                            risk_count = EXCLUDED.risk_count,
                            opportunity_count = EXCLUDED.opportunity_count,
                            generation_model = EXCLUDED.generation_model,
                            generation_prompt_version = EXCLUDED.generation_prompt_version,
                            is_fallback = EXCLUDED.is_fallback,
                            generated_at = NOW(),
                            expires_at = EXCLUDED.expires_at,
                            updated_at = NOW()
                    """),
                    {
                        "insight_id": str(uuid.uuid4()),
                        "corp_id": corp_id,
                        "stance_level": stance_level,
                        "stance_label": stance_label,
                        "stance_color": stance_color,
                        "executive_summary": executive_summary,
                        "narrative": narrative,
                        "key_risks": json.dumps(key_risks, ensure_ascii=False),
                        "key_opportunities": json.dumps(key_opportunities, ensure_ascii=False),
                        "mitigating_factors": json.dumps(mitigating_factors, ensure_ascii=False),
                        "action_items": json.dumps(action_items, ensure_ascii=False),
                        "signal_count": signal_count,
                        "risk_count": risk_count,
                        "opportunity_count": opportunity_count,
                        "generation_model": generation_model,
                        "generation_prompt_version": "v2.0",
                        "is_fallback": is_fallback,
                        "expires_at": expires_at,
                    },
                )
                db.commit()

        except Exception as e:
            logger.error(f"Failed to save Loan Insight to DB: {e}")
            raise

    def _format_signals_for_loan_insight(self, signals: List[Dict[str, Any]]) -> str:
        """Format signals for Loan Insight LLM prompt."""
        formatted = []
        for idx, s in enumerate(signals, 1):
            line = f"{idx}. [{s.get('signal_type', '')}][{s.get('impact_direction', '')}] {s.get('title', '')} (강도: {s.get('impact_strength', '')})"
            if s.get("summary"):
                line += f" - {s.get('summary', '')[:150]}"
            formatted.append(line)
        return "\n".join(formatted)

    def _format_profile_for_loan_insight(self, profile: Optional[Dict[str, Any]], corp_name: str) -> str:
        """Format profile for Loan Insight LLM prompt."""
        if not profile:
            return f"(프로필 정보 없음 - {corp_name})"

        lines = []

        # 사업 개요
        if profile.get("business_summary"):
            lines.append(f"사업 개요: {profile['business_summary']}")

        # 비즈니스 모델
        if profile.get("business_model"):
            lines.append(f"비즈니스 모델: {profile['business_model']}")

        # 업종 현황
        if profile.get("industry_overview"):
            lines.append(f"업종 현황: {profile['industry_overview']}")

        # 매출 및 수출
        if profile.get("revenue_krw"):
            revenue_str = f"{profile['revenue_krw'] / 100000000:.0f}억원" if profile['revenue_krw'] >= 100000000 else f"{profile['revenue_krw']:,}원"
            lines.append(f"연간 매출: {revenue_str}")

        if profile.get("export_ratio_pct") is not None:
            lines.append(f"수출 비중: {profile['export_ratio_pct']}%")

        # 국가별 노출
        if profile.get("country_exposure"):
            countries = ", ".join([f"{k} {v}%" for k, v in profile["country_exposure"].items()])
            lines.append(f"국가별 노출: {countries}")

        # 주요 고객사
        if profile.get("key_customers"):
            lines.append(f"주요 고객사: {', '.join(profile['key_customers'][:5])}")

        # 주요 원자재
        if profile.get("key_materials"):
            lines.append(f"주요 원자재: {', '.join(profile['key_materials'][:5])}")

        # 공급망 정보
        if profile.get("supply_chain"):
            sc = profile["supply_chain"]
            if sc.get("single_source_risk"):
                lines.append(f"단일 조달처 위험: {', '.join(sc['single_source_risk'])}")

        # 해외 사업
        if profile.get("overseas_operations"):
            lines.append(f"해외 사업장: {', '.join(profile['overseas_operations'][:3])}")

        # 경쟁사
        if profile.get("competitors"):
            comp_names = [c.get("name", c) if isinstance(c, dict) else c for c in profile["competitors"][:3]]
            lines.append(f"주요 경쟁사: {', '.join(comp_names)}")

        if not lines:
            return f"(상세 프로필 정보 없음 - {corp_name})"

        return "\n".join(lines)

    def _format_banking_data_for_loan_insight(
        self, banking_data: Optional[Dict[str, Any]], corp_name: str
    ) -> str:
        """
        Format Banking Data for Loan Insight LLM prompt.
        은행 기업뱅킹 전문가 관점의 핵심 지표를 포맷팅.
        """
        if not banking_data:
            return f"(당행 거래 데이터 없음 - {corp_name})"

        lines = []

        # 금액 포맷팅 헬퍼
        def fmt_krw(value):
            if not value:
                return "-"
            if value >= 1_0000_0000_0000:
                return f"{value / 1_0000_0000_0000:.1f}조원"
            if value >= 1_0000_0000:
                return f"{value / 1_0000_0000:.0f}억원"
            return f"{value / 1_0000:.0f}만원"

        def fmt_usd(value):
            if not value:
                return "-"
            if value >= 1_000_000:
                return f"${value / 1_000_000:.1f}M"
            return f"${value / 1_000:.0f}K"

        # ============================================================
        # 1. 여신 현황 (Loan Exposure) - 핵심 지표
        # ============================================================
        loan = banking_data.get("loan_exposure", {})
        if loan:
            lines.append("## 여신 현황 (Loan Exposure)")
            if loan.get("total_exposure_krw"):
                lines.append(f"- 총 여신 잔액: {fmt_krw(loan['total_exposure_krw'])}")

            # 여신 구성
            if loan.get("by_type"):
                by_type = loan["by_type"]
                type_parts = []
                if by_type.get("working_capital"):
                    type_parts.append(f"운전자금 {fmt_krw(by_type['working_capital'])}")
                if by_type.get("facility"):
                    type_parts.append(f"시설자금 {fmt_krw(by_type['facility'])}")
                if by_type.get("trade_finance"):
                    type_parts.append(f"무역금융 {fmt_krw(by_type['trade_finance'])}")
                if type_parts:
                    lines.append(f"- 여신 구성: {', '.join(type_parts)}")

            # 리스크 지표
            risk_ind = loan.get("risk_indicators", {})
            if risk_ind:
                risk_parts = []
                if risk_ind.get("internal_grade"):
                    lines.append(f"- 내부 신용등급: {risk_ind['internal_grade']}")
                if risk_ind.get("overdue_flag") is not None:
                    status = "연체 발생" if risk_ind["overdue_flag"] else "정상"
                    lines.append(f"- 연체 상태: {status}")
                if risk_ind.get("overdue_days"):
                    lines.append(f"- 연체 일수: {risk_ind['overdue_days']}일")

        # ============================================================
        # 2. 담보 현황 (Collateral) - 핵심 지표
        # ============================================================
        collateral = banking_data.get("collateral_detail", {})
        if collateral:
            lines.append("\n## 담보 현황 (Collateral)")
            if collateral.get("total_collateral_value"):
                lines.append(f"- 총 담보가치: {fmt_krw(collateral['total_collateral_value'])}")
            if collateral.get("avg_ltv") is not None:
                ltv = collateral["avg_ltv"]
                ltv_status = "양호" if ltv < 60 else ("주의" if ltv < 80 else "위험")
                lines.append(f"- 평균 LTV: {ltv}% ({ltv_status})")

            # 담보 목록
            if collateral.get("collaterals"):
                for col in collateral["collaterals"][:3]:
                    col_type = col.get("type", "기타")
                    col_value = fmt_krw(col.get("value", 0))
                    col_ltv = col.get("ltv_ratio", 0)
                    desc = col.get("description", "")[:30]
                    lines.append(f"  - {col_type}: {col_value} (LTV {col_ltv}%) - {desc}")

        # ============================================================
        # 3. 예수금 현황 (Deposit)
        # ============================================================
        deposit = banking_data.get("deposit_trend", {})
        if deposit:
            lines.append("\n## 예수금 현황 (Deposit)")
            if deposit.get("current_balance"):
                lines.append(f"- 현재 잔액: {fmt_krw(deposit['current_balance'])}")
            if deposit.get("trend"):
                lines.append(f"- 추이: {deposit['trend']}")
            if deposit.get("avg_balance_3m"):
                lines.append(f"- 최근 3개월 평균: {fmt_krw(deposit['avg_balance_3m'])}")

        # ============================================================
        # 4. 무역금융 / 환 노출 (Trade Finance / FX) - 핵심 지표
        # ============================================================
        trade = banking_data.get("trade_finance", {})
        if trade:
            lines.append("\n## 무역금융 / 환 노출 (Trade Finance)")

            # 수출
            export = trade.get("export", {})
            if export:
                if export.get("current_receivables_usd"):
                    lines.append(f"- 수출 채권: {fmt_usd(export['current_receivables_usd'])}")

            # 수입
            imp = trade.get("import", {})
            if imp:
                if imp.get("current_payables_usd"):
                    lines.append(f"- 수입 채무: {fmt_usd(imp['current_payables_usd'])}")

            # FX 노출 (⭐ 핵심)
            fx = trade.get("fx_exposure", {})
            if fx:
                if fx.get("net_position_usd"):
                    lines.append(f"- 순 외화 포지션: {fmt_usd(fx['net_position_usd'])}")
                if fx.get("hedge_ratio") is not None:
                    hedge = fx["hedge_ratio"]
                    hedge_status = "양호" if hedge >= 50 else ("주의" if hedge >= 30 else "위험")
                    lines.append(f"- 환헤지 비율: {hedge}% ({hedge_status}, 권고치 50%)")

        # ============================================================
        # 5. 기존 Risk Alerts (당행 시스템 감지)
        # ============================================================
        risk_alerts = banking_data.get("risk_alerts", [])
        if risk_alerts:
            lines.append("\n## 당행 시스템 감지 Risk Alerts ⚠️")
            for alert in risk_alerts[:5]:
                severity = alert.get("severity", "MED")
                title = alert.get("title", "알림")
                desc = alert.get("description", "")[:80]
                category = alert.get("category", "")
                lines.append(f"- [{severity}] {title}: {desc}")

        # ============================================================
        # 6. 기존 Opportunity Signals (당행 시스템 감지)
        # ============================================================
        opp_signals = banking_data.get("opportunity_signals", [])
        if opp_signals:
            lines.append("\n## 당행 시스템 감지 영업 기회 🎯")
            for opp in opp_signals[:5]:
                if isinstance(opp, str):
                    lines.append(f"- {opp}")
                elif isinstance(opp, dict):
                    lines.append(f"- {opp.get('title', opp)}")

        if not lines:
            return f"(상세 Banking Data 없음 - {corp_name})"

        return "\n".join(lines)
