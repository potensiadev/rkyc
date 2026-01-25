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

# Loan Insight 프롬프트 (v2.0 - Executive Summary + Key Opportunities 포함)
LOAN_INSIGHT_SYSTEM_PROMPT = """당신은 은행의 '기업 여신 심사역(Credit Officer)'이자 '리스크 분석 AI'입니다.
주어진 기업의 프로필과 감지된 시그널(위험/기회 요인)을 바탕으로, 대출 승인/유지 여부를 판단하는 데 필요한 '보조 의견서'를 작성해야 합니다.

# 역할
- 재무제표(정량) 외의 비재무/동향(정성) 정보를 종합하여 리스크의 방향성을 제시합니다.
- 심사역이 놓칠 수 있는 '부실 징후'나 '숨겨진 기회'를 포착하여 브리핑합니다.

# 분석 대상 기업
기업명: {corp_name}
업종: {industry_name}

# 기업 프로필 (외부 수집 정보)
{profile_context}

# 출력 요구사항 (JSON)
다음 JSON 형식으로 출력하십시오. 마크다운 코드블록 없이 순수 JSON만 출력하세요.

{{
  "executive_summary": "2-3문장으로 작성. 첫 문장은 기업명+주요사업/비즈니스모델 요약, 둘째 문장은 핵심 리스크 요약(있으면), 셋째 문장은 핵심 기회 요약(있으면). 100자 내외.",
  "stance_level": "CAUTION | MONITORING | STABLE | POSITIVE",
  "stance_label": "한글 라벨 (예: 주의 요망, 모니터링 필요, 중립/안정적, 긍정적)",
  "narrative": "종합 의견 서술 (3-4문장). 전체적인 톤앤매너는 전문가스럽고 객관적으로. 핵심 리스크와 상쇄 요인을 종합하여 결론 도출.",
  "key_risks": [
    "핵심 리스크 요인 1 (구체적 근거 포함)",
    "핵심 리스크 요인 2"
  ],
  "key_opportunities": [
    "핵심 기회 요인 1 (구체적 근거 포함, 시그널 기반)",
    "핵심 기회 요인 2"
  ],
  "mitigating_factors": [
    "리스크 상쇄 요인 1 (구체적 근거 포함)",
    "리스크 상쇄 요인 2"
  ],
  "action_items": [
    "심사역이 확인해야 할 구체적인 행동/서류 1",
    "심사역이 확인해야 할 구체적인 행동/서류 2"
  ]
}}

# 판단 가이드
1. **CAUTION (주의 요망)**: 치명적 리스크(경영권 분쟁, 횡령, 주요 거래처 이탈) 또는 다수의 High Risk 시그널. 여신 축소/회수 검토 필요.
2. **MONITORING (모니터링 필요)**: 당장 부실은 아니나 하방 압력(원자재가 상승, 산업 불황) 존재. 한도 유지하되 관찰 필요.
3. **STABLE (중립/안정적)**: 특이사항 없거나 리스크/기회가 상쇄됨. 통상적인 심사 진행.
4. **POSITIVE (긍정적)**: 대형 수주, M&A 성공 등 현금흐름 개선 확실시. 한도 증액 등 영업 기회.

# 작성 팁
- 'executive_summary'는 보고서 맨 위 요약란에 표시됩니다. 사업 개요와 핵심 시그널을 간결하게 담으세요.
- 'key_opportunities'는 'key_risks'와 균형있게 작성하세요. 기회 시그널이 있다면 여신 확대/영업 기회로 연결하세요.
- 'narrative'는 심사역이 보고서에 그대로 붙여넣을 수 있을 수준으로 정제된 문장을 사용하십시오.
- 'action_items'는 추상적인 "확인 필요"가 아니라, "계약서 O조항 검토", "법인 등기부등본 확인" 등 구체적으로 지시하십시오.
- 단정적 표현 금지: "~로 추정됨", "~가능성 있음", "검토 권고" 사용
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

        logger.info(f"INSIGHT stage starting for corp_id={corp_id}")

        # Handle no signals case
        if not signals:
            insight = self._generate_no_signals_insight(corp_name)
            # 시그널이 없어도 기본 Loan Insight 저장
            self._save_default_loan_insight(corp_id, corp_name, profile)
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

            # Loan Insight 생성 및 DB 저장 (별도 LLM 호출, profile 포함)
            self._generate_and_save_loan_insight(corp_id, corp_name, industry_name, signals, profile)

            return insight

        except AllProvidersFailedError as e:
            logger.error(f"LLM failed for insight generation: {e}")
            # Fallback loan insight도 저장
            self._save_fallback_loan_insight(corp_id, corp_name, signals, profile)
            return self._generate_fallback_insight(signals, corp_name)

        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            self._save_fallback_loan_insight(corp_id, corp_name, signals, profile)
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

            # LLM 호출
            system_prompt = LOAN_INSIGHT_SYSTEM_PROMPT.format(
                corp_name=corp_name,
                industry_name=industry_name,
                profile_context=profile_context,
            )

            user_prompt = f"""다음 시그널을 분석하여 여신 참고 의견을 작성해 주세요.

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
            # Fallback 저장
            self._save_fallback_loan_insight(corp_id, corp_name, signals, profile)

    def _save_fallback_loan_insight(
        self,
        corp_id: str,
        corp_name: str,
        signals: List[Dict[str, Any]],
        profile: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save rule-based fallback Loan Insight."""
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

        # Rule-based stance determination
        key_opportunities = []
        if high_risk_count > 0 or risk_count > (opp_count * 2):
            stance_level = "CAUTION"
            stance_label = "주의 요망"
            narrative = "다수의 리스크 시그널이 감지되어 시스템에 의한 주의 등급이 산정되었습니다. 상세 시그널을 검토하시기 바랍니다."
            key_risks = ["자동 산정: High Risk 시그널 감지됨" if high_risk_count > 0 else "자동 산정: Risk 시그널 다수"]
            executive_summary += f" 리스크 시그널 {risk_count}건이 감지되어 주의가 필요합니다."
        elif risk_count > opp_count:
            stance_level = "MONITORING"
            stance_label = "모니터링 필요"
            narrative = "일부 리스크 요인이 존재하여 모니터링이 권장됩니다."
            key_risks = ["자동 산정: 일부 Risk 시그널 존재"]
            executive_summary += f" 일부 리스크 요인({risk_count}건)이 감지되어 모니터링이 권장됩니다."
        elif opp_count > risk_count:
            stance_level = "POSITIVE"
            stance_label = "긍정적"
            narrative = "기회 시그널이 리스크 시그널보다 많이 감지되어 긍정적인 관점이 권장됩니다."
            key_risks = []
            key_opportunities = ["자동 산정: 기회 시그널 다수 감지"]
            executive_summary += f" 기회 시그널 {opp_count}건이 감지되어 긍정적 전망이 예상됩니다."
        else:
            stance_level = "STABLE"
            stance_label = "중립/안정적"
            narrative = "특이한 리스크 시그널이 감지되지 않았으며, 표준 심사 절차 진행이 가능합니다."
            key_risks = []
            executive_summary += " 현재 특이 시그널이 없어 안정적인 상태로 판단됩니다."

        self._save_loan_insight_to_db(
            corp_id=corp_id,
            stance_level=stance_level,
            stance_label=stance_label,
            executive_summary=executive_summary,
            narrative=narrative,
            key_risks=key_risks,
            key_opportunities=key_opportunities,
            mitigating_factors=[],
            action_items=["전체 시그널 목록 수동 검토 필요"] if risk_count > 0 else [],
            signal_count=len(signals),
            risk_count=risk_count,
            opportunity_count=opp_count,
            generation_model=None,
            is_fallback=True,
        )

        logger.info(f"Fallback Loan Insight saved for corp_id={corp_id}")

    def _save_default_loan_insight(self, corp_id: str, corp_name: str, profile: Optional[Dict[str, Any]] = None) -> None:
        """Save default Loan Insight when no signals detected."""
        # 기본 executive_summary 생성
        business_summary = ""
        if profile:
            business_summary = profile.get("business_summary") or profile.get("business_model") or ""

        if business_summary:
            executive_summary = f"{corp_name}은(는) {business_summary[:80]}. 현재 특이 시그널이 감지되지 않았습니다."
        else:
            executive_summary = f"{corp_name}에 대해 새로운 시그널이 발견되지 않았습니다. 현재 기준으로 안정적인 상태입니다."

        self._save_loan_insight_to_db(
            corp_id=corp_id,
            stance_level="STABLE",
            stance_label="중립/안정적",
            executive_summary=executive_summary,
            narrative=f"{corp_name}에 대해 새로운 시그널이 발견되지 않았습니다. 현재 기준으로 특별한 리스크/기회 요인은 관찰되지 않습니다.",
            key_risks=[],
            key_opportunities=[],
            mitigating_factors=[],
            action_items=[],
            signal_count=0,
            risk_count=0,
            opportunity_count=0,
            generation_model=None,
            is_fallback=False,
        )

        logger.info(f"Default Loan Insight saved for corp_id={corp_id}")

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
