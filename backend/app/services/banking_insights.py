"""
Banking Insights Rule Engine
Rule-based 방식으로 Banking Data + Signal을 교차 분석하여 인사이트 생성

Option A: 결정론적, Hallucination 없음
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class InsightType(str, Enum):
    RISK = "RISK"
    OPPORTUNITY = "OPPORTUNITY"


class InsightPriority(str, Enum):
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


@dataclass
class BankingInsight:
    """교차 분석 인사이트"""
    type: InsightType
    priority: InsightPriority
    title: str
    description: str
    related_signal_ids: List[str] = field(default_factory=list)
    related_signal_titles: List[str] = field(default_factory=list)
    metric_name: str = ""
    metric_value: str = ""
    threshold: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "related_signal_ids": self.related_signal_ids,
            "related_signal_titles": self.related_signal_titles,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
        }


class BankingInsightsEngine:
    """
    Rule-based Banking Insights Engine
    Banking Data + Signal 교차 분석
    """

    def __init__(
        self,
        banking_data: Dict[str, Any],
        signals: List[Dict[str, Any]],
        corp_name: str = ""
    ):
        self.banking_data = banking_data or {}
        self.signals = signals or []
        self.corp_name = corp_name
        self.insights: List[BankingInsight] = []

        # 주요 지표 추출
        self._extract_metrics()

    def _extract_metrics(self):
        """Banking Data에서 주요 지표 추출"""
        # 여신
        loan = self.banking_data.get("loan_exposure", {}) or {}
        self.total_loan = loan.get("total_exposure_krw", 0) or 0
        self.loan_composition = loan.get("composition", {}) or {}
        self.risk_indicators = loan.get("risk_indicators", {}) or {}

        # 수신
        deposit = self.banking_data.get("deposit_trend", {}) or {}
        self.total_deposit = deposit.get("current_balance", 0) or 0
        self.deposit_trend = deposit.get("trend", "STABLE")

        # 담보
        collateral = self.banking_data.get("collateral_detail", {}) or {}
        self.total_collateral = collateral.get("total_collateral_value", 0) or 0
        self.avg_ltv = collateral.get("avg_ltv", 0) or 0

        # 무역금융
        trade = self.banking_data.get("trade_finance", {}) or {}
        fx_exposure = trade.get("fx_exposure", {}) or {}
        self.hedge_ratio = fx_exposure.get("hedge_ratio", 0) or 0
        self.net_fx_position = fx_exposure.get("net_position_usd", 0) or 0

        export_data = trade.get("export", {}) or {}
        self.export_receivables = export_data.get("current_receivables_usd", 0) or 0

        # 재무
        financial = self.banking_data.get("financial_statements", {}) or {}
        self.financial_health = financial.get("financial_health", "")
        yoy = financial.get("yoy_growth", {}) or {}
        self.revenue_growth = yoy.get("revenue", 0) or 0

        # 비율 계산
        self.deposit_loan_ratio = (self.total_deposit / self.total_loan * 100) if self.total_loan > 0 else 0
        self.unsecured_ratio = 0
        if self.loan_composition:
            unsecured = self.loan_composition.get("unsecured_loan", {}) or {}
            self.unsecured_ratio = unsecured.get("ratio", 0) or 0

    def _get_signals_by_keyword(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """키워드로 관련 시그널 검색"""
        matched = []
        for signal in self.signals:
            title = (signal.get("title", "") or "").lower()
            summary = (signal.get("summary", "") or "").lower()
            text = f"{title} {summary}"

            for keyword in keywords:
                if keyword.lower() in text:
                    matched.append(signal)
                    break
        return matched

    def _get_signals_by_type(self, signal_type: str) -> List[Dict[str, Any]]:
        """signal_type으로 시그널 필터"""
        return [s for s in self.signals if s.get("signal_type") == signal_type]

    def _get_signals_by_impact(self, impact: str) -> List[Dict[str, Any]]:
        """impact_direction으로 시그널 필터"""
        return [s for s in self.signals if s.get("impact_direction") == impact]

    def _format_krw(self, value: int) -> str:
        """금액 포맷팅"""
        if value >= 1_0000_0000_0000:
            return f"{value / 1_0000_0000_0000:.1f}조원"
        if value >= 1_0000_0000:
            return f"{value / 1_0000_0000:.0f}억원"
        if value >= 1_0000:
            return f"{value / 1_0000:.0f}만원"
        return f"{value:,}원"

    def _format_usd(self, value: int) -> str:
        """USD 포맷팅"""
        if value >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        if value >= 1_000:
            return f"${value / 1_000:.0f}K"
        return f"${value:,}"

    def analyze(self) -> List[Dict[str, Any]]:
        """전체 분석 실행"""
        self.insights = []

        # Rule 1: 수신/여신 비율 분석
        self._rule_deposit_loan_ratio()

        # Rule 2: 환헤지 + 수출 시그널
        self._rule_fx_hedge_export()

        # Rule 3: 신용대출 비중 + 매출 시그널
        self._rule_unsecured_loan_revenue()

        # Rule 4: LTV + 업황 시그널
        self._rule_ltv_industry()

        # Rule 5: 내부등급 변동
        self._rule_grade_change()

        # Rule 6: 연체 플래그
        self._rule_overdue()

        # Rule 7: 수신 추세 + 시그널
        self._rule_deposit_trend()

        # Rule 8: 재무건전성 + 시그널
        self._rule_financial_health()

        # 우선순위 정렬 (HIGH > MED > LOW)
        priority_order = {"HIGH": 0, "MED": 1, "LOW": 2}
        self.insights.sort(key=lambda x: priority_order.get(x.priority.value, 99))

        return [i.to_dict() for i in self.insights]

    def _rule_deposit_loan_ratio(self):
        """Rule 1: 수신/여신 비율"""
        if self.total_loan == 0:
            return

        ratio = self.deposit_loan_ratio

        if ratio < 20:
            self.insights.append(BankingInsight(
                type=InsightType.OPPORTUNITY,
                priority=InsightPriority.MED,
                title="예금 유치 마케팅 대상",
                description=f"수신/여신 비율 {ratio:.1f}%로 예금 유치 여력 큼. 급여이체, 퇴직연금 등 수신상품 제안 권고.",
                metric_name="수신/여신 비율",
                metric_value=f"{ratio:.1f}%",
                threshold="< 20%",
            ))
        elif ratio > 80:
            self.insights.append(BankingInsight(
                type=InsightType.OPPORTUNITY,
                priority=InsightPriority.MED,
                title="여신 확대 여력 충분",
                description=f"수신/여신 비율 {ratio:.1f}%로 추가 여신 여력 있음. 시설자금, 운전자금 대출 제안 검토.",
                metric_name="수신/여신 비율",
                metric_value=f"{ratio:.1f}%",
                threshold="> 80%",
            ))

    def _rule_fx_hedge_export(self):
        """Rule 2: 환헤지 + 수출 시그널"""
        if self.export_receivables == 0:
            return

        # 수출 관련 시그널 검색
        export_signals = self._get_signals_by_keyword(["수출", "export", "해외", "달러", "환율"])

        if self.hedge_ratio < 50:
            # 환헤지 부족 리스크
            self.insights.append(BankingInsight(
                type=InsightType.RISK,
                priority=InsightPriority.HIGH if self.hedge_ratio < 30 else InsightPriority.MED,
                title="환헤지 부족으로 환노출 위험",
                description=f"환헤지율 {self.hedge_ratio:.0f}%, 순외화포지션 {self._format_usd(self.net_fx_position)} 노출. 환율 급변 시 여신 {self._format_krw(self.total_loan)} 손실 위험.",
                related_signal_ids=[s.get("id", "") for s in export_signals],
                related_signal_titles=[s.get("title", "") for s in export_signals],
                metric_name="환헤지율",
                metric_value=f"{self.hedge_ratio:.0f}%",
                threshold="< 50%",
            ))

        # 수출금융 확대 기회
        usance = self.banking_data.get("trade_finance", {}).get("usance", {}) or {}
        usance_util = usance.get("utilization_rate", 100) or 100

        if usance_util < 60 and export_signals:
            self.insights.append(BankingInsight(
                type=InsightType.OPPORTUNITY,
                priority=InsightPriority.MED,
                title="수출금융 한도 확대 기회",
                description=f"유산스 이용률 {usance_util:.0f}%로 여유 있음. 수출채권 {self._format_usd(self.export_receivables)} 기반 한도 확대 제안.",
                related_signal_ids=[s.get("id", "") for s in export_signals],
                related_signal_titles=[s.get("title", "") for s in export_signals],
                metric_name="유산스 이용률",
                metric_value=f"{usance_util:.0f}%",
                threshold="< 60%",
            ))

    def _rule_unsecured_loan_revenue(self):
        """Rule 3: 신용대출 비중 + 매출 시그널"""
        if self.unsecured_ratio < 30:
            return

        # 매출 관련 시그널 검색
        revenue_down_signals = self._get_signals_by_keyword(["매출 감소", "매출 하락", "실적 악화", "영업이익 감소"])
        revenue_up_signals = self._get_signals_by_keyword(["매출 증가", "매출 성장", "실적 개선", "영업이익 증가"])

        unsecured_amount = self.total_loan * self.unsecured_ratio / 100

        if self.unsecured_ratio > 50 and revenue_down_signals:
            self.insights.append(BankingInsight(
                type=InsightType.RISK,
                priority=InsightPriority.HIGH,
                title="무담보 여신 회수 위험",
                description=f"신용대출 비중 {self.unsecured_ratio:.0f}% ({self._format_krw(int(unsecured_amount))}), 매출 감소 시그널과 함께 회수 위험 상승.",
                related_signal_ids=[s.get("id", "") for s in revenue_down_signals],
                related_signal_titles=[s.get("title", "") for s in revenue_down_signals],
                metric_name="신용대출 비중",
                metric_value=f"{self.unsecured_ratio:.0f}%",
                threshold="> 50%",
            ))
        elif self.unsecured_ratio > 50 and revenue_up_signals:
            self.insights.append(BankingInsight(
                type=InsightType.OPPORTUNITY,
                priority=InsightPriority.LOW,
                title="담보 전환으로 금리 인하 가능",
                description=f"매출 성장 중이나 신용대출 비중 {self.unsecured_ratio:.0f}%로 높음. 담보 설정 시 금리 인하 제안.",
                related_signal_ids=[s.get("id", "") for s in revenue_up_signals],
                related_signal_titles=[s.get("title", "") for s in revenue_up_signals],
                metric_name="신용대출 비중",
                metric_value=f"{self.unsecured_ratio:.0f}%",
                threshold="> 50%",
            ))

    def _rule_ltv_industry(self):
        """Rule 4: LTV + 업황 시그널"""
        if self.avg_ltv == 0 or self.total_collateral == 0:
            return

        # 업황 관련 시그널 검색
        industry_up_signals = self._get_signals_by_keyword(["업황 회복", "업황 호조", "산업 성장", "수요 증가"])
        industry_down_signals = self._get_signals_by_keyword(["업황 악화", "업황 부진", "산업 침체", "수요 감소"])

        if self.avg_ltv < 50 and industry_up_signals:
            collateral_headroom = self.total_collateral - (self.total_collateral * self.avg_ltv / 100)
            self.insights.append(BankingInsight(
                type=InsightType.OPPORTUNITY,
                priority=InsightPriority.MED,
                title="담보 여력 활용 추가 여신 기회",
                description=f"LTV {self.avg_ltv:.0f}%로 담보여력 {self._format_krw(int(collateral_headroom))} 있음. 업황 호조와 함께 추가 여신 검토.",
                related_signal_ids=[s.get("id", "") for s in industry_up_signals],
                related_signal_titles=[s.get("title", "") for s in industry_up_signals],
                metric_name="평균 LTV",
                metric_value=f"{self.avg_ltv:.0f}%",
                threshold="< 50%",
            ))
        elif self.avg_ltv > 70 and industry_down_signals:
            self.insights.append(BankingInsight(
                type=InsightType.RISK,
                priority=InsightPriority.HIGH,
                title="담보가치 하락 시 LTV 초과 위험",
                description=f"LTV {self.avg_ltv:.0f}%로 높은 상태에서 업황 부진 시그널. 담보가치 하락 시 추가 담보 요청 필요.",
                related_signal_ids=[s.get("id", "") for s in industry_down_signals],
                related_signal_titles=[s.get("title", "") for s in industry_down_signals],
                metric_name="평균 LTV",
                metric_value=f"{self.avg_ltv:.0f}%",
                threshold="> 70%",
            ))

    def _rule_grade_change(self):
        """Rule 5: 내부등급 변동"""
        grade_change = self.risk_indicators.get("grade_change")
        internal_grade = self.risk_indicators.get("internal_grade", "")

        if grade_change == "DOWN":
            self.insights.append(BankingInsight(
                type=InsightType.RISK,
                priority=InsightPriority.MED,
                title="내부등급 하향 조정",
                description=f"내부등급 {internal_grade}으로 하향. 여신 {self._format_krw(self.total_loan)} 모니터링 강화 필요.",
                metric_name="내부등급",
                metric_value=internal_grade,
                threshold="DOWN",
            ))
        elif grade_change == "UP":
            self.insights.append(BankingInsight(
                type=InsightType.OPPORTUNITY,
                priority=InsightPriority.LOW,
                title="내부등급 상향으로 금리 인하 가능",
                description=f"내부등급 {internal_grade}으로 상향. 기존 여신 금리 인하 또는 추가 여신 협상 가능.",
                metric_name="내부등급",
                metric_value=internal_grade,
                threshold="UP",
            ))

    def _rule_overdue(self):
        """Rule 6: 연체 플래그"""
        overdue_flag = self.risk_indicators.get("overdue_flag", False)
        overdue_days = self.risk_indicators.get("overdue_days", 0) or 0
        overdue_amount = self.risk_indicators.get("overdue_amount", 0) or 0

        if overdue_flag:
            priority = InsightPriority.HIGH if overdue_days > 30 else InsightPriority.MED
            self.insights.append(BankingInsight(
                type=InsightType.RISK,
                priority=priority,
                title="연체 발생",
                description=f"연체 {overdue_days}일, 연체금액 {self._format_krw(overdue_amount)}. 즉시 연락 및 회수 조치 검토.",
                metric_name="연체일수",
                metric_value=f"{overdue_days}일",
                threshold="연체 발생",
            ))

    def _rule_deposit_trend(self):
        """Rule 7: 수신 추세"""
        if self.deposit_trend == "DECREASING":
            # 수신 감소 + 리스크 시그널
            risk_signals = self._get_signals_by_impact("RISK")
            if risk_signals:
                self.insights.append(BankingInsight(
                    type=InsightType.RISK,
                    priority=InsightPriority.MED,
                    title="수신 감소 추세 주의",
                    description=f"수신 잔액 감소 추세. 리스크 시그널과 함께 자금 유출 가능성 모니터링 필요.",
                    related_signal_ids=[s.get("id", "") for s in risk_signals[:3]],
                    related_signal_titles=[s.get("title", "") for s in risk_signals[:3]],
                    metric_name="수신 추세",
                    metric_value="DECREASING",
                    threshold="감소",
                ))
        elif self.deposit_trend == "INCREASING":
            self.insights.append(BankingInsight(
                type=InsightType.OPPORTUNITY,
                priority=InsightPriority.LOW,
                title="수신 증가 추세 - 관계 강화 기회",
                description=f"수신 잔액 증가 추세. 정기예금, 기업자금관리 서비스 등 추가 상품 제안 적기.",
                metric_name="수신 추세",
                metric_value="INCREASING",
                threshold="증가",
            ))

    def _rule_financial_health(self):
        """Rule 8: 재무건전성"""
        if self.financial_health in ["WARNING", "CRITICAL"]:
            self.insights.append(BankingInsight(
                type=InsightType.RISK,
                priority=InsightPriority.HIGH,
                title="재무건전성 악화",
                description=f"재무건전성 '{self.financial_health}' 상태. 여신 {self._format_krw(self.total_loan)} 정기 점검 강화 필요.",
                metric_name="재무건전성",
                metric_value=self.financial_health,
                threshold="WARNING/CRITICAL",
            ))
        elif self.financial_health == "IMPROVING":
            self.insights.append(BankingInsight(
                type=InsightType.OPPORTUNITY,
                priority=InsightPriority.MED,
                title="재무구조 개선 중 - 거래 확대 기회",
                description=f"재무건전성 개선 추세. 성장자금 지원, 금리 우대 등 거래 확대 제안 적기.",
                metric_name="재무건전성",
                metric_value=self.financial_health,
                threshold="IMPROVING",
            ))


def generate_banking_insights(
    banking_data: Dict[str, Any],
    signals: List[Dict[str, Any]],
    corp_name: str = ""
) -> Dict[str, Any]:
    """
    Banking Data + Signal 교차 분석하여 인사이트 생성

    Returns:
        {
            "risk_insights": [...],
            "opportunity_insights": [...],
            "total_risk_count": int,
            "total_opportunity_count": int,
        }
    """
    engine = BankingInsightsEngine(banking_data, signals, corp_name)
    all_insights = engine.analyze()

    risk_insights = [i for i in all_insights if i["type"] == "RISK"]
    opportunity_insights = [i for i in all_insights if i["type"] == "OPPORTUNITY"]

    return {
        "risk_insights": risk_insights,
        "opportunity_insights": opportunity_insights,
        "total_risk_count": len(risk_insights),
        "total_opportunity_count": len(opportunity_insights),
    }
