"""
Rule-Based Signal Generator - Deterministic signal extraction from Internal Snapshot

PM Report 결정 사항 (2026-02-06):
- Q1: Option A - 이전 스냅샷 없으면 변화 감지 시그널 스킵 (보수적)
- Q2: 임계값 - LOAN/COLLATERAL ±10%, KYC 365일, FINANCIAL ±20%
- Q3: Option A - 기존 데이터 마이그레이션 포함

Purpose:
- LLM 의존 없이 Internal Snapshot에서 결정론적 시그널 생성
- OVERDUE_FLAG_ON, INTERNAL_RISK_GRADE_CHANGE 등 핵심 리스크 100% 감지 보장
- confidence: HIGH (내부 데이터 기반)

Event Types Covered (5종):
1. OVERDUE_FLAG_ON - 연체 발생
2. INTERNAL_RISK_GRADE_CHANGE - 내부 등급 변경
3. LOAN_EXPOSURE_CHANGE - 여신 노출 변화 (±10%)
4. COLLATERAL_CHANGE - 담보 변화 (±10%)
5. KYC_REFRESH - KYC 갱신 필요 (365일 초과)
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration (PM 결정 임계값)
# =============================================================================

# 변화 감지 임계값
LOAN_EXPOSURE_CHANGE_THRESHOLD = 0.10  # ±10%
COLLATERAL_CHANGE_THRESHOLD = 0.10  # ±10%
FINANCIAL_CHANGE_THRESHOLD = 0.20  # ±20%
KYC_REFRESH_DAYS = 365  # 1년

# 등급 순서 (높은 등급 → 낮은 등급)
RISK_GRADE_ORDER = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]
RISK_GRADE_RANK = {grade: idx for idx, grade in enumerate(RISK_GRADE_ORDER)}

# 한글 등급 매핑
KOREAN_GRADE_MAP = {
    "저위험": "A",
    "중위험": "BBB",
    "고위험": "BB",
    "초고위험": "CCC",
    "위험": "B",
}


@dataclass
class RuleBasedSignal:
    """결정론적으로 생성된 시그널"""
    signal_type: str = "DIRECT"
    event_type: str = ""
    impact_direction: str = "RISK"
    impact_strength: str = "HIGH"
    confidence: str = "HIGH"  # 내부 데이터 기반이므로 항상 HIGH
    title: str = ""
    summary: str = ""
    evidence: list = field(default_factory=list)
    event_signature: str = ""

    def to_dict(self) -> dict:
        return {
            "signal_type": self.signal_type,
            "event_type": self.event_type,
            "impact_direction": self.impact_direction,
            "impact_strength": self.impact_strength,
            "confidence": self.confidence,
            "title": self.title,
            "summary": self.summary,
            "evidence": self.evidence,
            "event_signature": self.event_signature,
        }


class RuleBasedSignalGenerator:
    """
    Internal Snapshot에서 결정론적 시그널 생성

    - LLM 호출 불필요 (100% 결정론적)
    - confidence: HIGH (내부 데이터 기반)
    - 5종 event_type 지원
    """

    def __init__(self):
        self.generated_count = 0

    def generate(
        self,
        corp_id: str,
        corp_name: str,
        snapshot: dict,
        prev_snapshot: Optional[dict] = None,
    ) -> list[dict]:
        """
        Internal Snapshot에서 결정론적 시그널 생성

        Args:
            corp_id: 기업 ID
            corp_name: 기업명
            snapshot: 현재 Internal Snapshot JSON
            prev_snapshot: 이전 Internal Snapshot JSON (변화 감지용)

        Returns:
            list[dict]: 생성된 시그널 목록
        """
        signals = []

        # Rule 1: OVERDUE_FLAG_ON (이전 스냅샷 불필요)
        overdue_signal = self._check_overdue(corp_id, corp_name, snapshot)
        if overdue_signal:
            signals.append(overdue_signal)

        # Rule 2: INTERNAL_RISK_GRADE_CHANGE (이전 스냅샷 필요)
        if prev_snapshot:
            grade_signal = self._check_grade_change(corp_id, corp_name, snapshot, prev_snapshot)
            if grade_signal:
                signals.append(grade_signal)

        # Rule 3: LOAN_EXPOSURE_CHANGE (이전 스냅샷 필요)
        if prev_snapshot:
            loan_signal = self._check_loan_exposure_change(corp_id, corp_name, snapshot, prev_snapshot)
            if loan_signal:
                signals.append(loan_signal)

        # Rule 4: COLLATERAL_CHANGE (이전 스냅샷 필요)
        if prev_snapshot:
            collateral_signal = self._check_collateral_change(corp_id, corp_name, snapshot, prev_snapshot)
            if collateral_signal:
                signals.append(collateral_signal)

        # Rule 5: KYC_REFRESH (이전 스냅샷 불필요)
        kyc_signal = self._check_kyc_refresh(corp_id, corp_name, snapshot)
        if kyc_signal:
            signals.append(kyc_signal)

        self.generated_count = len(signals)
        logger.info(
            f"[RuleBasedGenerator] Generated {len(signals)} deterministic signals for {corp_name}"
        )

        return [s.to_dict() for s in signals]

    def _check_overdue(
        self,
        corp_id: str,
        corp_name: str,
        snapshot: dict,
    ) -> Optional[RuleBasedSignal]:
        """
        Rule 1: OVERDUE_FLAG_ON - 연체 발생 감지

        Trigger: /credit/loan_summary/overdue_flag == true
        """
        try:
            credit = snapshot.get("credit", {})
            loan_summary = credit.get("loan_summary", {})
            overdue_flag = loan_summary.get("overdue_flag", False)

            if not overdue_flag:
                return None

            # 추가 정보 수집
            overdue_days = loan_summary.get("overdue_days", 30)
            total_exposure = loan_summary.get("total_exposure_krw", 0)
            risk_grade = loan_summary.get("risk_grade_internal", "N/A")

            # 금액 포맷팅
            exposure_text = self._format_krw(total_exposure)

            signal = RuleBasedSignal(
                event_type="OVERDUE_FLAG_ON",
                impact_direction="RISK",
                impact_strength="HIGH",
                confidence="HIGH",
                title=f"{corp_name} 연체 발생 ({overdue_days}일 이상)",
                summary=(
                    f"{corp_name}의 기업여신 계좌에서 {overdue_days}일 이상 연체가 확인됨. "
                    f"총 여신 규모는 {exposure_text}이며, 내부 등급은 {risk_grade}. "
                    f"상환능력 저하 신호로 담보 점검 및 추가 모니터링 권고."
                ),
                evidence=[
                    {
                        "evidence_type": "INTERNAL_FIELD",
                        "ref_type": "SNAPSHOT_KEYPATH",
                        "ref_value": "/credit/loan_summary/overdue_flag",
                        "snippet": f"overdue_flag: true, overdue_days: {overdue_days}",
                    }
                ],
            )
            signal.event_signature = self._compute_signature(corp_id, signal)

            logger.info(f"[RuleBasedGenerator] OVERDUE_FLAG_ON detected for {corp_name}")
            return signal

        except Exception as e:
            logger.warning(f"[RuleBasedGenerator] Error checking overdue: {e}")
            return None

    def _check_grade_change(
        self,
        corp_id: str,
        corp_name: str,
        snapshot: dict,
        prev_snapshot: dict,
    ) -> Optional[RuleBasedSignal]:
        """
        Rule 2: INTERNAL_RISK_GRADE_CHANGE - 내부 등급 변경 감지

        Trigger: /corp/kyc_status/internal_risk_grade 변경
        """
        try:
            # 현재 등급
            current_grade = self._get_nested(snapshot, "corp.kyc_status.internal_risk_grade")
            # 이전 등급
            prev_grade = self._get_nested(prev_snapshot, "corp.kyc_status.internal_risk_grade")

            if not current_grade or not prev_grade:
                return None

            # 한글 등급 변환
            current_grade_normalized = KOREAN_GRADE_MAP.get(current_grade, current_grade)
            prev_grade_normalized = KOREAN_GRADE_MAP.get(prev_grade, prev_grade)

            if current_grade_normalized == prev_grade_normalized:
                return None

            # 등급 순위 비교
            current_rank = RISK_GRADE_RANK.get(current_grade_normalized, 5)
            prev_rank = RISK_GRADE_RANK.get(prev_grade_normalized, 5)

            grade_diff = current_rank - prev_rank

            if grade_diff == 0:
                return None

            # 등급 하락 (숫자가 커짐) = RISK
            # 등급 상승 (숫자가 작아짐) = OPPORTUNITY
            if grade_diff > 0:
                impact_direction = "RISK"
                impact_strength = "HIGH" if grade_diff >= 2 else "MED"
                direction_text = "하락"
            else:
                impact_direction = "OPPORTUNITY"
                impact_strength = "MED" if abs(grade_diff) >= 2 else "LOW"
                direction_text = "상승"

            signal = RuleBasedSignal(
                event_type="INTERNAL_RISK_GRADE_CHANGE",
                impact_direction=impact_direction,
                impact_strength=impact_strength,
                confidence="HIGH",
                title=f"{corp_name} 내부신용등급 {abs(grade_diff)}단계 {direction_text}",
                summary=(
                    f"{corp_name}의 내부신용등급이 {prev_grade}에서 {current_grade}로 "
                    f"{abs(grade_diff)}단계 {direction_text}함. "
                    f"{'기존 여신 조건 재검토 및 추가 모니터링 권고.' if impact_direction == 'RISK' else '긍정적 신용 변화로 여신 확대 검토 가능.'}"
                ),
                evidence=[
                    {
                        "evidence_type": "INTERNAL_FIELD",
                        "ref_type": "SNAPSHOT_KEYPATH",
                        "ref_value": "/corp/kyc_status/internal_risk_grade",
                        "snippet": f"internal_risk_grade: {current_grade} (이전: {prev_grade})",
                    }
                ],
            )
            signal.event_signature = self._compute_signature(corp_id, signal)

            logger.info(f"[RuleBasedGenerator] INTERNAL_RISK_GRADE_CHANGE detected for {corp_name}: {prev_grade} → {current_grade}")
            return signal

        except Exception as e:
            logger.warning(f"[RuleBasedGenerator] Error checking grade change: {e}")
            return None

    def _check_loan_exposure_change(
        self,
        corp_id: str,
        corp_name: str,
        snapshot: dict,
        prev_snapshot: dict,
    ) -> Optional[RuleBasedSignal]:
        """
        Rule 3: LOAN_EXPOSURE_CHANGE - 여신 노출 변화 감지 (±10%)

        Trigger: /credit/loan_summary/total_exposure_krw ±10% 변화
        """
        try:
            current_exposure = self._get_nested(snapshot, "credit.loan_summary.total_exposure_krw")
            prev_exposure = self._get_nested(prev_snapshot, "credit.loan_summary.total_exposure_krw")

            if current_exposure is None or prev_exposure is None:
                return None

            current_exposure = float(current_exposure)
            prev_exposure = float(prev_exposure)

            if prev_exposure == 0:
                return None

            change_ratio = (current_exposure - prev_exposure) / prev_exposure

            if abs(change_ratio) < LOAN_EXPOSURE_CHANGE_THRESHOLD:
                return None

            change_pct = abs(change_ratio) * 100

            if change_ratio > 0:
                impact_direction = "RISK" if change_ratio > 0.3 else "NEUTRAL"
                direction_text = "증가"
            else:
                impact_direction = "OPPORTUNITY"
                direction_text = "감소"

            impact_strength = "HIGH" if abs(change_ratio) >= 0.3 else "MED"

            signal = RuleBasedSignal(
                event_type="LOAN_EXPOSURE_CHANGE",
                impact_direction=impact_direction,
                impact_strength=impact_strength,
                confidence="HIGH",
                title=f"{corp_name} 여신 노출 {change_pct:.0f}% {direction_text}",
                summary=(
                    f"{corp_name}의 총 여신 노출이 {self._format_krw(prev_exposure)}에서 "
                    f"{self._format_krw(current_exposure)}로 {change_pct:.1f}% {direction_text}함. "
                    f"{'여신 한도 및 담보 적정성 재검토 권고.' if impact_direction == 'RISK' else '여신 축소로 리스크 익스포저 감소.'}"
                ),
                evidence=[
                    {
                        "evidence_type": "INTERNAL_FIELD",
                        "ref_type": "SNAPSHOT_KEYPATH",
                        "ref_value": "/credit/loan_summary/total_exposure_krw",
                        "snippet": f"total_exposure_krw: {current_exposure:,.0f} (이전: {prev_exposure:,.0f})",
                    }
                ],
            )
            signal.event_signature = self._compute_signature(corp_id, signal)

            logger.info(f"[RuleBasedGenerator] LOAN_EXPOSURE_CHANGE detected for {corp_name}: {change_pct:.1f}%")
            return signal

        except Exception as e:
            logger.warning(f"[RuleBasedGenerator] Error checking loan exposure change: {e}")
            return None

    def _check_collateral_change(
        self,
        corp_id: str,
        corp_name: str,
        snapshot: dict,
        prev_snapshot: dict,
    ) -> Optional[RuleBasedSignal]:
        """
        Rule 4: COLLATERAL_CHANGE - 담보 변화 감지 (±10%)

        Trigger: /collateral/total_collateral_value_krw ±10% 변화
        """
        try:
            current_collateral = self._get_nested(snapshot, "collateral.total_collateral_value_krw")
            prev_collateral = self._get_nested(prev_snapshot, "collateral.total_collateral_value_krw")

            if current_collateral is None or prev_collateral is None:
                return None

            current_collateral = float(current_collateral)
            prev_collateral = float(prev_collateral)

            if prev_collateral == 0:
                return None

            change_ratio = (current_collateral - prev_collateral) / prev_collateral

            if abs(change_ratio) < COLLATERAL_CHANGE_THRESHOLD:
                return None

            change_pct = abs(change_ratio) * 100

            if change_ratio < 0:
                impact_direction = "RISK"
                direction_text = "감소"
            else:
                impact_direction = "OPPORTUNITY"
                direction_text = "증가"

            impact_strength = "HIGH" if abs(change_ratio) >= 0.3 else "MED"

            signal = RuleBasedSignal(
                event_type="COLLATERAL_CHANGE",
                impact_direction=impact_direction,
                impact_strength=impact_strength,
                confidence="HIGH",
                title=f"{corp_name} 담보 가치 {change_pct:.0f}% {direction_text}",
                summary=(
                    f"{corp_name}의 담보 가치가 {self._format_krw(prev_collateral)}에서 "
                    f"{self._format_krw(current_collateral)}로 {change_pct:.1f}% {direction_text}함. "
                    f"{'담보 부족 가능성 점검 및 추가 담보 요청 검토 권고.' if impact_direction == 'RISK' else '담보 여력 증가로 여신 확대 여력 확보.'}"
                ),
                evidence=[
                    {
                        "evidence_type": "INTERNAL_FIELD",
                        "ref_type": "SNAPSHOT_KEYPATH",
                        "ref_value": "/collateral/total_collateral_value_krw",
                        "snippet": f"total_collateral_value_krw: {current_collateral:,.0f} (이전: {prev_collateral:,.0f})",
                    }
                ],
            )
            signal.event_signature = self._compute_signature(corp_id, signal)

            logger.info(f"[RuleBasedGenerator] COLLATERAL_CHANGE detected for {corp_name}: {change_pct:.1f}%")
            return signal

        except Exception as e:
            logger.warning(f"[RuleBasedGenerator] Error checking collateral change: {e}")
            return None

    def _check_kyc_refresh(
        self,
        corp_id: str,
        corp_name: str,
        snapshot: dict,
    ) -> Optional[RuleBasedSignal]:
        """
        Rule 5: KYC_REFRESH - KYC 갱신 필요 감지 (365일 초과)

        Trigger: /corp/kyc_status/last_kyc_updated가 365일 이상 경과
        """
        try:
            last_kyc_updated = self._get_nested(snapshot, "corp.kyc_status.last_kyc_updated")

            if not last_kyc_updated:
                return None

            # 날짜 파싱
            if isinstance(last_kyc_updated, str):
                try:
                    last_kyc_date = datetime.strptime(last_kyc_updated[:10], "%Y-%m-%d")
                except ValueError:
                    return None
            else:
                return None

            days_since_kyc = (datetime.now() - last_kyc_date).days

            if days_since_kyc < KYC_REFRESH_DAYS:
                return None

            # 경과 기간에 따른 강도 결정
            if days_since_kyc >= 730:  # 2년 이상
                impact_strength = "HIGH"
            elif days_since_kyc >= 548:  # 1.5년 이상
                impact_strength = "MED"
            else:
                impact_strength = "LOW"

            signal = RuleBasedSignal(
                event_type="KYC_REFRESH",
                impact_direction="RISK",
                impact_strength=impact_strength,
                confidence="HIGH",
                title=f"{corp_name} KYC 갱신 필요 ({days_since_kyc}일 경과)",
                summary=(
                    f"{corp_name}의 마지막 KYC 갱신일({last_kyc_updated[:10]})로부터 "
                    f"{days_since_kyc}일이 경과함. 규정상 연 1회 갱신 필요하며, "
                    f"최신 재무정보 및 주주현황 업데이트 권고."
                ),
                evidence=[
                    {
                        "evidence_type": "INTERNAL_FIELD",
                        "ref_type": "SNAPSHOT_KEYPATH",
                        "ref_value": "/corp/kyc_status/last_kyc_updated",
                        "snippet": f"last_kyc_updated: {last_kyc_updated}, days_elapsed: {days_since_kyc}",
                    }
                ],
            )
            signal.event_signature = self._compute_signature(corp_id, signal)

            logger.info(f"[RuleBasedGenerator] KYC_REFRESH detected for {corp_name}: {days_since_kyc} days")
            return signal

        except Exception as e:
            logger.warning(f"[RuleBasedGenerator] Error checking KYC refresh: {e}")
            return None

    # =============================================================================
    # Helper Methods
    # =============================================================================

    def _get_nested(self, data: dict, path: str, default=None):
        """Dot notation으로 중첩 딕셔너리 값 조회"""
        if not data:
            return default

        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def _format_krw(self, amount: float) -> str:
        """금액을 한글 단위로 포맷팅"""
        if amount >= 1_0000_0000_0000:  # 1조 이상
            return f"{amount / 1_0000_0000_0000:.1f}조원"
        elif amount >= 1_0000_0000:  # 1억 이상
            return f"{amount / 1_0000_0000:.0f}억원"
        elif amount >= 1_0000:  # 1만 이상
            return f"{amount / 1_0000:.0f}만원"
        else:
            return f"{amount:,.0f}원"

    def _compute_signature(self, corp_id: str, signal: RuleBasedSignal) -> str:
        """시그널 고유 서명 계산 (중복 방지용)"""
        # 동일 기업, 동일 event_type, 동일 날짜의 시그널은 동일 signature
        today = datetime.now().strftime("%Y-%m-%d")
        signature_input = f"{corp_id}|{signal.event_type}|{today}|RULE_BASED"
        return hashlib.sha256(signature_input.encode()).hexdigest()[:32]


# =============================================================================
# Singleton Instance
# =============================================================================

_generator_instance: Optional[RuleBasedSignalGenerator] = None


def get_rule_based_generator() -> RuleBasedSignalGenerator:
    """Get singleton instance of RuleBasedSignalGenerator"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = RuleBasedSignalGenerator()
    return _generator_instance


def reset_rule_based_generator() -> None:
    """Reset singleton instance (for testing)"""
    global _generator_instance
    _generator_instance = None
