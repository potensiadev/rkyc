#!/usr/bin/env python
"""
Test LLM Loan Insight Generation (Direct LLM call)
"""

import sys
import os
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Mock Data
MOCK_SIGNALS = [
    {
        "signal_type": "ENVIRONMENT",
        "event_type": "POLICY_REGULATION_CHANGE",
        "impact_direction": "OPPORTUNITY",
        "impact_strength": "HIGH",
        "title": "정부의 로봇산업 지원 정책",
        "summary": "산업 전반의 성장 가능성을 높이며, 기업의 기술 개발 및 시장 확장을 지원할 수 있음.",
    },
    {
        "signal_type": "ENVIRONMENT",
        "event_type": "POLICY_REGULATION_CHANGE",
        "impact_direction": "OPPORTUNITY",
        "impact_strength": "MED",
        "title": "AI 및 자율주행 기술 수요 증가",
        "summary": "기술 혁신을 통해 시장 경쟁력을 강화할 수 있는 기회.",
    },
    {
        "signal_type": "DIRECT",
        "event_type": "KYC_REFRESH",
        "impact_direction": "RISK",
        "impact_strength": "MED",
        "title": "KYC 갱신 지연",
        "summary": "569일 경과로 최신 재무정보 및 주주현황의 불확실성이 존재함.",
    },
    {
        "signal_type": "DIRECT",
        "event_type": "GOVERNANCE_CHANGE",
        "impact_direction": "RISK",
        "impact_strength": "HIGH",
        "title": "매매거래 정지",
        "summary": "2026년 1월 19일 한국거래소 시장감시규정에 따라 매매거래가 정지되었으며, 이는 상환능력에 대한 우려를 제기함.",
    },
]

MOCK_BANKING_DATA = {
    "loan_exposure": {
        "total_exposure_krw": 85_0000_0000,
        "by_type": {"working_capital": 35_0000_0000, "facility": 40_0000_0000, "trade_finance": 10_0000_0000},
        "risk_indicators": {"internal_grade": "MED", "overdue_flag": False},
    },
    "collateral_detail": {
        "total_collateral_value": 110_0000_0000,
        "avg_ltv": 77.3,
        "collaterals": [
            {"type": "부동산", "value": 80_0000_0000, "ltv_ratio": 75, "description": "경기도 화성 공장 부지"},
            {"type": "기계장비", "value": 30_0000_0000, "ltv_ratio": 80, "description": "로봇 생산 설비"},
        ],
    },
    "deposit_trend": {"current_balance": 12_0000_0000, "trend": "STABLE"},
    "trade_finance": {
        "export": {"current_receivables_usd": 2_500_000},
        "import": {"current_payables_usd": 1_800_000},
        "fx_exposure": {"net_position_usd": 700_000, "hedge_ratio": 28},
    },
    "risk_alerts": [
        {"severity": "HIGH", "title": "환헤지율 저조", "description": "환헤지율 28%로 권고치 50% 대비 크게 미달"},
        {"severity": "MED", "title": "매매거래 정지", "description": "2026년 1월 19일 매매거래 정지"},
    ],
    "opportunity_signals": [
        "로봇산업 정책 지원 확대로 시설자금 대출 수요 증가 예상",
        "자율주행 기술 수요 증가로 수출 확대 가능성",
    ],
}

MOCK_PROFILE = {
    "business_summary": "산업용 로봇 및 자동화 설비 제조업체",
    "business_model": "로봇 시스템 및 자동화 솔루션 설계/제조/판매",
    "revenue_krw": 150_0000_0000,
    "export_ratio_pct": 35,
}


def format_banking_data(banking_data, corp_name):
    """Banking Data 포맷팅"""
    if not banking_data:
        return f"(당행 거래 데이터 없음 - {corp_name})"

    def fmt_krw(v):
        if not v: return "-"
        if v >= 1_0000_0000_0000: return f"{v/1_0000_0000_0000:.1f}조원"
        if v >= 1_0000_0000: return f"{v/1_0000_0000:.0f}억원"
        return f"{v/1_0000:.0f}만원"

    def fmt_usd(v):
        if not v: return "-"
        if v >= 1_000_000: return f"${v/1_000_000:.1f}M"
        return f"${v/1_000:.0f}K"

    lines = []

    loan = banking_data.get("loan_exposure", {})
    if loan:
        lines.append("## 여신 현황 (Loan Exposure)")
        if loan.get("total_exposure_krw"):
            lines.append(f"- 총 여신 잔액: {fmt_krw(loan['total_exposure_krw'])}")
        if loan.get("by_type"):
            by_type = loan["by_type"]
            parts = []
            if by_type.get("working_capital"): parts.append(f"운전자금 {fmt_krw(by_type['working_capital'])}")
            if by_type.get("facility"): parts.append(f"시설자금 {fmt_krw(by_type['facility'])}")
            if by_type.get("trade_finance"): parts.append(f"무역금융 {fmt_krw(by_type['trade_finance'])}")
            if parts: lines.append(f"- 여신 구성: {', '.join(parts)}")
        risk_ind = loan.get("risk_indicators", {})
        if risk_ind.get("internal_grade"):
            lines.append(f"- 내부 신용등급: {risk_ind['internal_grade']}")
        if risk_ind.get("overdue_flag") is not None:
            lines.append(f"- 연체 상태: {'연체 발생' if risk_ind['overdue_flag'] else '정상'}")

    collateral = banking_data.get("collateral_detail", {})
    if collateral:
        lines.append("\n## 담보 현황 (Collateral)")
        if collateral.get("total_collateral_value"):
            lines.append(f"- 총 담보가치: {fmt_krw(collateral['total_collateral_value'])}")
        if collateral.get("avg_ltv") is not None:
            ltv = collateral["avg_ltv"]
            ltv_status = "양호" if ltv < 60 else ("주의" if ltv < 80 else "위험")
            lines.append(f"- 평균 LTV: {ltv}% ({ltv_status})")
        for col in collateral.get("collaterals", [])[:3]:
            lines.append(f"  - {col.get('type', '기타')}: {fmt_krw(col.get('value', 0))} (LTV {col.get('ltv_ratio', 0)}%)")

    trade = banking_data.get("trade_finance", {})
    if trade:
        lines.append("\n## 무역금융 / 환 노출 (Trade Finance)")
        if trade.get("export", {}).get("current_receivables_usd"):
            lines.append(f"- 수출 채권: {fmt_usd(trade['export']['current_receivables_usd'])}")
        if trade.get("import", {}).get("current_payables_usd"):
            lines.append(f"- 수입 채무: {fmt_usd(trade['import']['current_payables_usd'])}")
        fx = trade.get("fx_exposure", {})
        if fx.get("hedge_ratio") is not None:
            hedge = fx["hedge_ratio"]
            hedge_status = "양호" if hedge >= 50 else ("주의" if hedge >= 30 else "위험")
            lines.append(f"- 환헤지 비율: {hedge}% ({hedge_status}, 권고치 50%)")

    risk_alerts = banking_data.get("risk_alerts", [])
    if risk_alerts:
        lines.append("\n## 당행 시스템 감지 Risk Alerts")
        for alert in risk_alerts[:3]:
            lines.append(f"- [{alert.get('severity', 'MED')}] {alert.get('title', '알림')}: {alert.get('description', '')[:60]}")

    opp_signals = banking_data.get("opportunity_signals", [])
    if opp_signals:
        lines.append("\n## 당행 시스템 감지 영업 기회")
        for opp in opp_signals[:3]:
            lines.append(f"- {opp if isinstance(opp, str) else opp.get('title', opp)}")

    return "\n".join(lines)


def format_profile(profile, corp_name):
    """Profile 포맷팅"""
    if not profile:
        return f"(프로필 정보 없음 - {corp_name})"

    lines = []
    if profile.get("business_summary"):
        lines.append(f"사업 개요: {profile['business_summary']}")
    if profile.get("business_model"):
        lines.append(f"비즈니스 모델: {profile['business_model']}")
    if profile.get("revenue_krw"):
        lines.append(f"연간 매출: {profile['revenue_krw']/1_0000_0000:.0f}억원")
    if profile.get("export_ratio_pct") is not None:
        lines.append(f"수출 비중: {profile['export_ratio_pct']}%")

    return "\n".join(lines) if lines else f"(상세 프로필 없음 - {corp_name})"


def format_signals(signals):
    """시그널 포맷팅"""
    lines = []
    for idx, s in enumerate(signals, 1):
        line = f"{idx}. [{s.get('signal_type', '')}][{s.get('impact_direction', '')}] {s.get('title', '')} (강도: {s.get('impact_strength', '')})"
        if s.get("summary"):
            line += f" - {s.get('summary', '')[:100]}"
        lines.append(line)
    return "\n".join(lines)


def call_llm(system_prompt, user_prompt):
    """LLM 호출 (litellm 사용)"""
    import litellm

    # API 키 설정
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if anthropic_key:
        model = "claude-sonnet-4-20250514"
        litellm.api_key = anthropic_key
    elif openai_key:
        model = "gpt-4o"
        litellm.api_key = openai_key
    else:
        print("[ERROR] No API key found (ANTHROPIC_API_KEY or OPENAI_API_KEY)")
        return None

    print(f"[INFO] Using model: {model}")

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )

        content = response.choices[0].message.content

        # JSON 파싱
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())

    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}")
        return None


def main():
    corp_name = "휴림로봇"
    industry_name = "로봇/자동화"

    print("=" * 70)
    print(f"Loan Insight v3.0 테스트 - {corp_name}")
    print("=" * 70)

    # 컨텍스트 포맷팅
    profile_context = format_profile(MOCK_PROFILE, corp_name)
    banking_context = format_banking_data(MOCK_BANKING_DATA, corp_name)
    signals_context = format_signals(MOCK_SIGNALS)

    print("\n[Banking Data Context]")
    print(banking_context)

    # System Prompt
    system_prompt = f"""당신은 은행의 '기업 여신 심사역(Credit Officer)'이자 '기업뱅킹 전문가'입니다.
주어진 기업의 프로필, **당행 거래 현황(Banking Data)**, 그리고 감지된 시그널을 바탕으로 여신 의사결정을 위한 '보조 의견서'를 작성해야 합니다.

# 핵심 역할
- **당행 관점 분석**: 외부 시그널이 "당행 여신 포트폴리오"에 미치는 영향을 구체적으로 분석
- 여신 금액, 담보 현황, 환헤지 비율 등 실제 숫자를 인용하여 근거 기반 분석

# 분석 대상 기업
기업명: {corp_name}
업종: {industry_name}

# 기업 프로필 (외부 수집 정보)
{profile_context}

# 당행 거래 현황 (Banking Data) - 핵심 참고 자료
{banking_context}

# 출력 요구사항 (JSON)
다음 JSON 형식으로 출력하십시오. 마크다운 코드블록 없이 순수 JSON만 출력하세요.

{{
  "executive_summary": "2-3문장. 첫 문장은 기업+주요사업 요약, 둘째 문장은 당행 여신 규모와 핵심 리스크/기회 요약.",
  "stance_level": "CAUTION | MONITORING | STABLE | POSITIVE",
  "stance_label": "한글 라벨",
  "narrative": "종합 의견 서술 (3-4문장). '당행 여신 XXX억원' 등 구체적 숫자를 인용.",
  "key_risks": [
    "은행 관점 핵심 리스크 (예: '당행 여신 85억원이 환율 변동에 노출됨. 환헤지율 28%로 권고치 50% 대비 크게 미달')"
  ],
  "key_opportunities": [
    "은행 관점 핵심 기회 (예: '로봇산업 정책 수혜 예상. 시설자금 대출 확대 검토 가능')"
  ],
  "mitigating_factors": ["리스크 상쇄 요인"],
  "action_items": ["심사역 확인사항"]
}}

# 작성 규칙 (필수)
- **숫자 인용 필수**: "당행 여신 85억원", "LTV 77%", "환헤지율 28%" 등 실제 숫자를 반드시 인용
- **당행 관점 필수**: "당행 포트폴리오에 미치는 영향" 관점으로 작성
"""

    user_prompt = f"""다음 시그널을 분석하여 **은행 관점**의 여신 참고 의견을 작성해 주세요.
Banking Data의 실제 숫자(여신 금액, LTV, 환헤지율 등)를 반드시 인용하여 구체적으로 분석하세요.

[감지된 시그널 목록]
{signals_context}
"""

    print("\n[LLM 호출 중...]")
    result = call_llm(system_prompt, user_prompt)

    if result:
        print("\n" + "=" * 70)
        print("생성된 Loan Insight")
        print("=" * 70)
        print(f"\nStance: {result.get('stance_level')} ({result.get('stance_label')})")
        print(f"\n[Executive Summary]\n{result.get('executive_summary')}")
        print(f"\n[Narrative]\n{result.get('narrative')}")

        print(f"\n[핵심 리스크 요인]")
        for r in result.get('key_risks', []):
            print(f"  - {r}")

        print(f"\n[핵심 기회 요인]")
        for o in result.get('key_opportunities', []):
            print(f"  - {o}")

        print(f"\n[Action Items]")
        for a in result.get('action_items', []):
            print(f"  - {a}")

        print("\n" + "=" * 70)
    else:
        print("[ERROR] Failed to generate Loan Insight")


if __name__ == '__main__':
    main()
