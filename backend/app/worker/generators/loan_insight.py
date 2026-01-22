"""
Loan Insight Generator
Generates AI Risk Opinion for Credit Report based on signals.
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime

from app.models.signal import Signal
from app.schemas.report import LoanInsightResponse, LoanInsightStance
from app.worker.llm.service import LLMService

logger = logging.getLogger(__name__)

# System Prompt for Loan Insight Generation
LOAN_INSIGHT_SYSTEM_PROMPT = """당신은 은행의 '기업 여신 심사역(Credit Officer)'이자 '리스크 분석 AI'입니다.
주어진 기업의 프로필과 감지된 시그널(위험/기회 요인)을 바탕으로, 대출 승인/유지 여부를 판단하는 데 필요한 '보조 의견서'를 작성해야 합니다.

# 역할
- 재무제표(정량) 외의 비재무/동향(정성) 정보를 종합하여 리스크의 방향성을 제시합니다.
- 심사역이 놓칠 수 있는 '부실 징후'나 '숨겨진 기회'를 포착하여 브리핑합니다.

# 분석 대상 기업
기업명: {corp_name}
업종: {industry_name}

# 입력 데이터
감지된 시그널 목록 (Risk/Opportunity/Neutral)

# 출력 요구사항 (JSON)
다음 JSON 형식으로 출력하십시오. 마크다운 코드블록 없이 순수 JSON만 출력하세요.

{{
  "stance_level": "CAUTION | MONITORING | STABLE | POSITIVE",
  "stance_label": "한글 라벨 (예: 주의 요망, 모니터링 필요, 중립/안정적, 긍정적)",
  "narrative": "종합 의견 서술 (3-4문장). 전체적인 톤앤매너는 전문가스럽고 객관적으로. 핵심 리스크와 상쇄 요인을 종합하여 결론 도출.",
  "key_risks": [
    "핵심 리스크 요인 1 (구체적 근거 포함)",
    "핵심 리스크 요인 2"
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
- 'narrative'는 심사역이 보고서에 그대로 붙여넣을 수 있을 수준으로 정제된 문장을 사용하십시오.
- 'action_items'는 추상적인 "확인 필요"가 아니라, "계약서 O조항 검토", "법인 등기부등본 확인" 등 구체적으로 지시하십시오.
"""

class LoanInsightGenerator:
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()

    async def generate(self, corp_name: str, industry_name: str, signals: List[Signal]) -> LoanInsightResponse:
        """
        Generate Loan Insight based on signals.
        If no signals, returns a default STABLE insight.
        """
        if not signals:
            return self._get_default_insight()

        # Prepare context for LLM
        signals_context = self._format_signals_for_context(signals)
        
        # Determine strictness simply based on risk count for fallback, 
        # but utilize LLM for the real logic.
        
        try:
            # Construct Prompts
            system_prompt = LOAN_INSIGHT_SYSTEM_PROMPT.format(
                corp_name=corp_name,
                industry_name=industry_name
            )
            
            user_prompt = f"""
다음 시그널을 분석하여 여신 참고 의견을 작성해 주세요.

[감지된 시그널 목록]
{signals_context}
"""
            
            # Call LLM
            response_json = self.llm.call_with_json_response(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2 # Low temperature for consistent analysis
            )
            
            return self._parse_llm_response(response_json)

        except Exception as e:
            logger.error(f"Failed to generate loan insight via LLM: {e}")
            return self._generate_rule_based_fallback(signals)

    def _format_signals_for_context(self, signals: List[Signal]) -> str:
        formatted = []
        for idx, s in enumerate(signals, 1):
            line = f"{idx}. [{s.signal_type}][{s.impact_direction}] {s.title} (강도: {s.impact_strength})"
            if s.summary_short:
                line += f" - {s.summary_short}"
            formatted.append(line)
        return "\n".join(formatted)

    def _parse_llm_response(self, data: Dict[str, Any]) -> LoanInsightResponse:
        stance_level = data.get("stance_level", "STABLE")
        
        # Color mapping
        color_map = {
            "CAUTION": "red",
            "MONITORING": "orange",
            "STABLE": "green", # or blue/grey depending on UI
            "POSITIVE": "blue"
        }
        
        return LoanInsightResponse(
            stance=LoanInsightStance(
                label=data.get("stance_label", "중립/안정적"),
                level=stance_level,
                color=color_map.get(stance_level, "grey")
            ),
            narrative=data.get("narrative", "특이한 리스크 시그널이 감지되지 않았습니다."),
            key_risks=data.get("key_risks", []),
            mitigating_factors=data.get("mitigating_factors", []),
            action_items=data.get("action_items", [])
        )

    def _generate_rule_based_fallback(self, signals: List[Signal]) -> LoanInsightResponse:
        """
        Fallback logic if LLM fails.
        Simple heuristic based on Risk vs Opportunity counts.
        """
        risk_count = sum(1 for s in signals if s.impact_direction == "RISK")
        opp_count = sum(1 for s in signals if s.impact_direction == "OPPORTUNITY")
        high_risk_count = sum(1 for s in signals if s.impact_direction == "RISK" and s.impact_strength == "HIGH")

        if high_risk_count > 0 or risk_count > (opp_count * 2):
            return LoanInsightResponse(
                stance=LoanInsightStance(label="주의 요망", level="CAUTION", color="red"),
                narrative="다수의 리스크 시그널이 감지되어 시스템에 의한 주의 등급이 산정되었습니다. 상세 시그널을 검토하시기 바랍니다.",
                key_risks=["자동 산정: High Risk 시그널 감지됨" if high_risk_count > 0 else "자동 산정: Risk 시그널 다수"],
                mitigating_factors=[],
                action_items=["전체 시그널 목록 수동 검토 필요"]
            )
        elif risk_count > opp_count:
            return LoanInsightResponse(
                stance=LoanInsightStance(label="모니터링 필요", level="MONITORING", color="orange"),
                narrative="일부 리스크 요인이 존재하여 모니터링이 권장됩니다.",
                key_risks=["자동 산정: 일부 Risk 시그널 존재"],
                mitigating_factors=[],
                action_items=["관련 리스크 시그널 확인"]
            )
        else:
            return self._get_default_insight()

    def _get_default_insight(self) -> LoanInsightResponse:
        return LoanInsightResponse(
            stance=LoanInsightStance(label="중립/안정적", level="STABLE", color="green"),
            narrative="특이한 리스크 시그널이 감지되지 않았으며, 표준 심사 절차 진행이 가능합니다.",
            key_risks=[],
            mitigating_factors=[],
            action_items=[]
        )
