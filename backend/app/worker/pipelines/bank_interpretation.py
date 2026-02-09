"""
Bank Interpretation Pipeline
은행 관점 시그널 재해석 레이어 (MVP)

핵심 원칙:
1. 숫자는 템플릿 변수로 주입 (LLM 생성 금지)
2. 권고 조치는 "검토 권고" 수준만
3. 기존 시그널 구조 유지, 해석만 추가

2026-02-09 MVP 구현
"""

import logging
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from app.worker.llm.service import LLMService

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class BankContext:
    """은행 내부 데이터 컨텍스트 (Internal Snapshot에서 추출)"""

    corp_id: str
    corp_name: str

    # 여신 정보
    total_exposure_krw: Optional[int] = None  # 총 여신 노출액
    loan_count: Optional[int] = None  # 여신 건수
    largest_loan_krw: Optional[int] = None  # 최대 단일 여신

    # 담보 정보
    collateral_value_krw: Optional[int] = None  # 담보 총액
    collateral_ratio_pct: Optional[float] = None  # 담보 비율

    # 신용 정보
    internal_risk_grade: Optional[str] = None  # 내부 등급 (HIGH/MED/LOW)
    overdue_flag: bool = False  # 연체 여부
    overdue_days: Optional[int] = None  # 연체 일수

    # 업종 포트폴리오
    industry_code: Optional[str] = None
    industry_exposure_krw: Optional[int] = None  # 해당 업종 총 여신
    industry_exposure_ratio_pct: Optional[float] = None  # 업종 비중

    def to_prompt_context(self) -> str:
        """LLM 프롬프트에 주입할 컨텍스트 문자열 생성"""
        lines = [
            f"# 당행 내부 정보 ({self.corp_name})",
            "",
        ]

        # 여신 정보
        if self.total_exposure_krw is not None:
            lines.append(f"- 총 여신 노출액: {self._format_krw(self.total_exposure_krw)}")
        if self.loan_count is not None:
            lines.append(f"- 여신 건수: {self.loan_count}건")
        if self.largest_loan_krw is not None:
            lines.append(f"- 최대 단일 여신: {self._format_krw(self.largest_loan_krw)}")

        # 담보 정보
        if self.collateral_value_krw is not None:
            lines.append(f"- 담보 총액: {self._format_krw(self.collateral_value_krw)}")
        if self.collateral_ratio_pct is not None:
            lines.append(f"- 담보 비율: {self.collateral_ratio_pct:.1f}%")

        # 신용 정보
        if self.internal_risk_grade:
            lines.append(f"- 내부 신용등급: {self.internal_risk_grade}")
        if self.overdue_flag:
            days_str = f" ({self.overdue_days}일)" if self.overdue_days else ""
            lines.append(f"- 연체 상태: 연체 중{days_str}")

        # 업종 정보
        if self.industry_exposure_krw is not None:
            lines.append(f"- 해당 업종({self.industry_code}) 총 여신: {self._format_krw(self.industry_exposure_krw)}")
        if self.industry_exposure_ratio_pct is not None:
            lines.append(f"- 업종 비중: {self.industry_exposure_ratio_pct:.1f}%")

        return "\n".join(lines)

    def _format_krw(self, amount: int) -> str:
        """금액 포맷팅 (억원 단위)"""
        if amount >= 100_000_000:
            return f"{amount / 100_000_000:.1f}억원"
        elif amount >= 10_000:
            return f"{amount / 10_000:.0f}만원"
        else:
            return f"{amount:,}원"


@dataclass
class BankInterpretation:
    """은행 관점 재해석 결과"""

    interpretation: str  # 은행 관점 해석 텍스트
    portfolio_impact: str  # HIGH/MED/LOW
    recommended_action: str  # 권고 조치
    action_priority: str  # URGENT/NORMAL/LOW
    generated_at: datetime

    # 메타데이터
    exposure_mentioned: bool = False  # 노출액 언급 여부
    action_type: Optional[str] = None  # 조치 유형 (MONITOR/REVIEW/ESCALATE)


# =============================================================================
# Prompts
# =============================================================================

BANK_INTERPRETATION_SYSTEM_PROMPT = """당신은 한국 금융기관의 기업여신 심사역입니다.
주어진 시그널을 "당행 관점"에서 재해석하여 실무에 도움이 되는 인사이트를 제공합니다.

# 핵심 원칙
1. **주체 변환**: "이 기업이..." → "당행의 {기업명} 여신이..."
2. **노출액 연결**: 모든 해석에 당행 여신 노출액 대비 영향도 언급
3. **권고 수준**: 결정이 아닌 "검토 권고" 수준으로만 작성
4. **숫자 정확성**: 제공된 숫자만 사용, 새로운 숫자 생성 금지

# 금지 표현
- "즉시 조치 필요", "반드시", "확실히"
- "~할 것이다", "~일 것이다" (단정적 미래 예측)
- "대출 회수", "여신 축소" (결정 사항)

# 허용 표현
- "검토 권고", "모니터링 강화 권고", "점검 권고"
- "~가능성 있음", "~로 추정됨", "~고려 필요"
- "담보 재평가 검토", "한도 검토"

# 출력 형식
JSON 형식으로 응답:
```json
{
  "interpretation": "당행 관점 해석 (2-3문장)",
  "portfolio_impact": "HIGH|MED|LOW",
  "recommended_action": "권고 조치 (1문장)",
  "action_priority": "URGENT|NORMAL|LOW"
}
```

# Portfolio Impact 기준
- HIGH: 여신 노출액 100억 이상 또는 담보 부족 우려
- MED: 여신 노출액 10억~100억 또는 등급 변동 가능성
- LOW: 여신 노출액 10억 미만 또는 모니터링 수준

# Action Priority 기준
- URGENT: 연체 발생, 등급 하락, 담보 가치 급락
- NORMAL: 업황 변화, 재무 변동, 외부 리스크
- LOW: 일반 모니터링, 긍정적 기회 요인
"""


def build_bank_interpretation_prompt(
    signal: dict,
    bank_context: BankContext,
) -> str:
    """은행 관점 재해석을 위한 User Prompt 생성"""

    # 시그널 정보 추출
    signal_type = signal.get("signal_type", "")
    event_type = signal.get("event_type", "")
    impact_direction = signal.get("impact_direction", "")
    impact_strength = signal.get("impact_strength", "")
    title = signal.get("title", "")
    summary = signal.get("summary", "")

    prompt = f"""# 시그널 정보
- 유형: {signal_type} / {event_type}
- 영향: {impact_direction} ({impact_strength})
- 제목: {title}
- 요약: {summary}

{bank_context.to_prompt_context()}

# 요청
위 시그널을 당행 관점에서 재해석하세요.
- 당행 여신 {bank_context._format_krw(bank_context.total_exposure_krw) if bank_context.total_exposure_krw else "정보 없음"}에 미치는 영향 분석
- 담보 비율 {f"{bank_context.collateral_ratio_pct:.1f}%" if bank_context.collateral_ratio_pct else "정보 없음"} 고려
- 내부 등급 {bank_context.internal_risk_grade or "정보 없음"} 기준 평가

JSON 형식으로 응답하세요.
"""

    return prompt


# =============================================================================
# Service Class
# =============================================================================

class BankInterpretationService:
    """
    은행 관점 시그널 재해석 서비스

    MVP 구현:
    - 기존 시그널 + Internal Snapshot → LLM → 은행 관점 해석
    - 숫자는 템플릿 변수로 주입 (hallucination 방지)
    - 권고 조치만 (결정 사항 아님)
    """

    def __init__(self):
        self.llm = LLMService()

    def interpret(
        self,
        signal: dict,
        snapshot: dict,
        corp_profile: Optional[dict] = None,
    ) -> Optional[BankInterpretation]:
        """
        시그널을 은행 관점으로 재해석

        Args:
            signal: 기존 시그널 dict
            snapshot: Internal Snapshot JSON
            corp_profile: Corp Profile (선택)

        Returns:
            BankInterpretation 또는 None (실패 시)
        """
        try:
            # 1. Bank Context 구축
            bank_context = self._build_bank_context(signal, snapshot, corp_profile)

            # 2. LLM 호출
            user_prompt = build_bank_interpretation_prompt(signal, bank_context)

            messages = [
                {"role": "system", "content": BANK_INTERPRETATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            response = self.llm.call_with_fallback(
                messages=messages,
                temperature=0.3,  # 일관성 중시
                max_tokens=500,
            )

            # 3. 응답 파싱
            interpretation = self._parse_response(response)

            if interpretation:
                logger.info(
                    f"[BankInterpretation] Generated for {bank_context.corp_name}: "
                    f"impact={interpretation.portfolio_impact}, "
                    f"priority={interpretation.action_priority}"
                )

            return interpretation

        except Exception as e:
            logger.error(f"[BankInterpretation] Failed: {e}")
            return None

    def interpret_batch(
        self,
        signals: list[dict],
        snapshot: dict,
        corp_profile: Optional[dict] = None,
    ) -> list[tuple[dict, Optional[BankInterpretation]]]:
        """
        여러 시그널 일괄 재해석

        Returns:
            List of (signal, interpretation) tuples
        """
        results = []

        for signal in signals:
            interpretation = self.interpret(signal, snapshot, corp_profile)
            results.append((signal, interpretation))

        return results

    def _build_bank_context(
        self,
        signal: dict,
        snapshot: dict,
        corp_profile: Optional[dict] = None,
    ) -> BankContext:
        """Internal Snapshot에서 Bank Context 추출"""

        corp_id = signal.get("corp_id", "")
        corp_name = snapshot.get("corp", {}).get("corp_name", "")

        # Credit 정보 추출
        credit = snapshot.get("credit", {})
        loan_summary = credit.get("loan_summary", {})

        # Collateral 정보 추출
        collateral = snapshot.get("collateral", {})

        # KYC 정보 추출
        kyc_status = snapshot.get("corp", {}).get("kyc_status", {})

        return BankContext(
            corp_id=corp_id,
            corp_name=corp_name,
            # 여신 정보
            total_exposure_krw=loan_summary.get("total_exposure_krw"),
            loan_count=loan_summary.get("loan_count"),
            largest_loan_krw=loan_summary.get("largest_loan_krw"),
            # 담보 정보
            collateral_value_krw=collateral.get("total_value_krw"),
            collateral_ratio_pct=collateral.get("coverage_ratio_pct"),
            # 신용 정보
            internal_risk_grade=kyc_status.get("internal_risk_grade"),
            overdue_flag=loan_summary.get("overdue_flag", False),
            overdue_days=loan_summary.get("overdue_days"),
            # 업종 정보
            industry_code=snapshot.get("corp", {}).get("industry_code"),
        )

    def _parse_response(self, response: str) -> Optional[BankInterpretation]:
        """LLM 응답 파싱"""
        import json
        import re

        try:
            # JSON 블록 추출
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                logger.warning("[BankInterpretation] No JSON found in response")
                return None

            data = json.loads(json_match.group())

            # 필수 필드 검증
            interpretation = data.get("interpretation", "")
            portfolio_impact = data.get("portfolio_impact", "MED")
            recommended_action = data.get("recommended_action", "")
            action_priority = data.get("action_priority", "NORMAL")

            # Enum 검증
            if portfolio_impact not in ("HIGH", "MED", "LOW"):
                portfolio_impact = "MED"
            if action_priority not in ("URGENT", "NORMAL", "LOW"):
                action_priority = "NORMAL"

            # 금지 표현 체크
            forbidden = ["즉시 조치", "반드시", "확실히", "대출 회수", "여신 축소"]
            for word in forbidden:
                if word in interpretation or word in recommended_action:
                    logger.warning(f"[BankInterpretation] Forbidden word detected: {word}")
                    # 표현 완화
                    interpretation = interpretation.replace(word, "검토 권고")
                    recommended_action = recommended_action.replace(word, "검토 권고")

            return BankInterpretation(
                interpretation=interpretation,
                portfolio_impact=portfolio_impact,
                recommended_action=recommended_action,
                action_priority=action_priority,
                generated_at=datetime.utcnow(),
                exposure_mentioned="여신" in interpretation or "노출" in interpretation,
            )

        except json.JSONDecodeError as e:
            logger.error(f"[BankInterpretation] JSON parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"[BankInterpretation] Parse error: {e}")
            return None


# =============================================================================
# Pipeline Class
# =============================================================================

class BankInterpretationPipeline:
    """
    은행 관점 재해석 파이프라인

    Signal Extraction 후 실행하여 각 시그널에 은행 관점 해석 추가
    """

    def __init__(self):
        self.service = BankInterpretationService()

    def execute(
        self,
        signals: list[dict],
        context: dict,
    ) -> list[dict]:
        """
        시그널 리스트에 은행 관점 해석 추가

        Args:
            signals: Signal Extraction 결과
            context: Unified Context (snapshot 포함)

        Returns:
            은행 관점 해석이 추가된 시그널 리스트
        """
        if not signals:
            return signals

        snapshot = context.get("snapshot_json", {})
        corp_profile = context.get("corp_profile", {})
        corp_name = context.get("corp_name", "")

        logger.info(
            f"[BankInterpretation] Starting interpretation for {len(signals)} signals "
            f"(corp: {corp_name})"
        )

        enriched_signals = []
        success_count = 0

        for signal in signals:
            interpretation = self.service.interpret(signal, snapshot, corp_profile)

            if interpretation:
                # 시그널에 은행 관점 해석 추가
                signal["bank_interpretation"] = interpretation.interpretation
                signal["portfolio_impact"] = interpretation.portfolio_impact
                signal["recommended_action"] = interpretation.recommended_action
                signal["action_priority"] = interpretation.action_priority
                signal["interpretation_generated_at"] = interpretation.generated_at.isoformat()
                success_count += 1
            else:
                # 해석 실패 시 기본값
                signal["bank_interpretation"] = None
                signal["portfolio_impact"] = None
                signal["recommended_action"] = None
                signal["action_priority"] = None

            enriched_signals.append(signal)

        logger.info(
            f"[BankInterpretation] Completed: "
            f"total={len(signals)}, interpreted={success_count}"
        )

        return enriched_signals


# =============================================================================
# Helper Functions
# =============================================================================

def get_bank_interpretation_service() -> BankInterpretationService:
    """싱글톤 서비스 인스턴스 반환"""
    return BankInterpretationService()


def get_bank_interpretation_pipeline() -> BankInterpretationPipeline:
    """싱글톤 파이프라인 인스턴스 반환"""
    return BankInterpretationPipeline()
