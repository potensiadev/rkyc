#!/usr/bin/env python
"""
Test Banking Data Formatting (No DB required)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Banking Data
MOCK_BANKING_DATA = {
    "6701-4567890": {  # 휴림로봇
        "data_date": "2026-02-09",
        "loan_exposure": {
            "total_exposure_krw": 85_0000_0000,  # 850억
            "by_type": {
                "working_capital": 35_0000_0000,
                "facility": 40_0000_0000,
                "trade_finance": 10_0000_0000,
            },
            "risk_indicators": {
                "internal_grade": "MED",
                "overdue_flag": False,
            },
        },
        "collateral_detail": {
            "total_collateral_value": 110_0000_0000,  # 1100억
            "avg_ltv": 77.3,
            "collaterals": [
                {"type": "부동산", "value": 80_0000_0000, "ltv_ratio": 75, "description": "경기도 화성 공장 부지"},
                {"type": "기계장비", "value": 30_0000_0000, "ltv_ratio": 80, "description": "로봇 생산 설비"},
            ],
        },
        "deposit_trend": {
            "current_balance": 12_0000_0000,
            "trend": "STABLE",
            "avg_balance_3m": 11_5000_0000,
        },
        "trade_finance": {
            "export": {
                "current_receivables_usd": 2_500_000,
            },
            "import": {
                "current_payables_usd": 1_800_000,
            },
            "fx_exposure": {
                "net_position_usd": 700_000,
                "hedge_ratio": 28,
            },
        },
        "risk_alerts": [
            {"id": "RA001", "severity": "HIGH", "title": "환헤지율 저조", "description": "환헤지율 28%로 권고치 50% 대비 크게 미달", "category": "TRADE"},
            {"id": "RA002", "severity": "MED", "title": "매매거래 정지", "description": "2026년 1월 19일 한국거래소 시장감시규정에 따라 매매거래 정지", "category": "MARKET"},
        ],
        "opportunity_signals": [
            "로봇산업 정책 지원 확대로 시설자금 대출 수요 증가 예상",
            "자율주행 기술 수요 증가로 수출 확대 가능성",
        ],
    },
}


def format_banking_data_for_loan_insight(banking_data: dict, corp_name: str) -> str:
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

    # 1. 여신 현황
    loan = banking_data.get("loan_exposure", {})
    if loan:
        lines.append("## 여신 현황 (Loan Exposure)")
        if loan.get("total_exposure_krw"):
            lines.append(f"- 총 여신 잔액: {fmt_krw(loan['total_exposure_krw'])}")

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

        risk_ind = loan.get("risk_indicators", {})
        if risk_ind:
            if risk_ind.get("internal_grade"):
                lines.append(f"- 내부 신용등급: {risk_ind['internal_grade']}")
            if risk_ind.get("overdue_flag") is not None:
                status = "연체 발생" if risk_ind["overdue_flag"] else "정상"
                lines.append(f"- 연체 상태: {status}")

    # 2. 담보 현황
    collateral = banking_data.get("collateral_detail", {})
    if collateral:
        lines.append("\n## 담보 현황 (Collateral)")
        if collateral.get("total_collateral_value"):
            lines.append(f"- 총 담보가치: {fmt_krw(collateral['total_collateral_value'])}")
        if collateral.get("avg_ltv") is not None:
            ltv = collateral["avg_ltv"]
            ltv_status = "양호" if ltv < 60 else ("주의" if ltv < 80 else "위험")
            lines.append(f"- 평균 LTV: {ltv}% ({ltv_status})")

        if collateral.get("collaterals"):
            for col in collateral["collaterals"][:3]:
                col_type = col.get("type", "기타")
                col_value = fmt_krw(col.get("value", 0))
                col_ltv = col.get("ltv_ratio", 0)
                desc = col.get("description", "")[:30]
                lines.append(f"  - {col_type}: {col_value} (LTV {col_ltv}%) - {desc}")

    # 3. 예수금 현황
    deposit = banking_data.get("deposit_trend", {})
    if deposit:
        lines.append("\n## 예수금 현황 (Deposit)")
        if deposit.get("current_balance"):
            lines.append(f"- 현재 잔액: {fmt_krw(deposit['current_balance'])}")
        if deposit.get("trend"):
            lines.append(f"- 추이: {deposit['trend']}")

    # 4. 무역금융 / 환 노출
    trade = banking_data.get("trade_finance", {})
    if trade:
        lines.append("\n## 무역금융 / 환 노출 (Trade Finance)")

        export = trade.get("export", {})
        if export and export.get("current_receivables_usd"):
            lines.append(f"- 수출 채권: {fmt_usd(export['current_receivables_usd'])}")

        imp = trade.get("import", {})
        if imp and imp.get("current_payables_usd"):
            lines.append(f"- 수입 채무: {fmt_usd(imp['current_payables_usd'])}")

        fx = trade.get("fx_exposure", {})
        if fx:
            if fx.get("net_position_usd"):
                lines.append(f"- 순 외화 포지션: {fmt_usd(fx['net_position_usd'])}")
            if fx.get("hedge_ratio") is not None:
                hedge = fx["hedge_ratio"]
                hedge_status = "양호" if hedge >= 50 else ("주의" if hedge >= 30 else "위험")
                lines.append(f"- 환헤지 비율: {hedge}% ({hedge_status}, 권고치 50%)")

    # 5. Risk Alerts
    risk_alerts = banking_data.get("risk_alerts", [])
    if risk_alerts:
        lines.append("\n## 당행 시스템 감지 Risk Alerts ⚠️")
        for alert in risk_alerts[:5]:
            severity = alert.get("severity", "MED")
            title = alert.get("title", "알림")
            desc = alert.get("description", "")[:80]
            lines.append(f"- [{severity}] {title}: {desc}")

    # 6. Opportunity Signals
    opp_signals = banking_data.get("opportunity_signals", [])
    if opp_signals:
        lines.append("\n## 당행 시스템 감지 영업 기회 🎯")
        for opp in opp_signals[:5]:
            if isinstance(opp, str):
                lines.append(f"- {opp}")
            elif isinstance(opp, dict):
                lines.append(f"- {opp.get('title', opp)}")

    return "\n".join(lines)


def main():
    print("=" * 70)
    print("Banking Data 포맷팅 테스트 (휴림로봇)")
    print("=" * 70)

    banking_data = MOCK_BANKING_DATA["6701-4567890"]
    formatted = format_banking_data_for_loan_insight(banking_data, "휴림로봇")

    print("\n[LLM 프롬프트에 전달될 Banking Data Context]\n")
    print(formatted)
    print("\n" + "=" * 70)

    # 프롬프트 전체 미리보기
    print("\n[완성된 System Prompt 미리보기]\n")

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
"""

    print(LOAN_INSIGHT_SYSTEM_PROMPT.format(
        corp_name="휴림로봇",
        industry_name="로봇/자동화",
        profile_context="(프로필 정보 생략)",
        banking_context=formatted,
    ))


if __name__ == '__main__':
    main()
