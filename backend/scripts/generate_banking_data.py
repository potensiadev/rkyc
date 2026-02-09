#!/usr/bin/env python3
"""
5개 신규 기업에 대해 DART 재무제표 + Banking Data 생성

Usage:
    cd backend
    python -m scripts.generate_banking_data
"""

import asyncio
import sys
import os
import ssl
import json
from datetime import datetime, timezone, date
from typing import Optional
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

from app.services.dart_api import (
    load_corp_codes,
    get_corp_code,
    get_financial_statements,
    get_company_info_by_name,
)

# 대상 기업 목록 (corp_id는 DB에서 조회)
TARGET_CORPS = [
    {"name": "대한과학", "industry": "도매업", "scenario": "과학기기 유통, 안정적 현금흐름"},
    {"name": "파이오링크", "industry": "IT/네트워크", "scenario": "ADC 전문, 기술주, R&D 투자"},
    {"name": "팬엔터테인먼트", "industry": "엔터테인먼트", "scenario": "드라마 제작, 현금흐름 변동성"},
    {"name": "이엘피", "industry": "조명/LED", "scenario": "자동차 LED, 수출 의존"},
    {"name": "크라우드웍스", "industry": "AI/플랫폼", "scenario": "AI 데이터, 스타트업 고성장"},
]

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.jvvhfylycswfedppmkld:aMgngVn1YKhb8iki@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
)


def build_financial_statements_json(dart_financials: list, corp_name: str) -> dict:
    """DART 재무제표 -> banking_data.financial_statements JSON 변환"""
    years_data = {}

    for fs in dart_financials:
        year = fs.bsns_year
        years_data[year] = {
            "assets": fs.total_assets or 0,
            "liabilities": fs.total_liabilities or 0,
            "equity": fs.total_equity or 0,
            "revenue": fs.revenue or 0,
            "operating_income": fs.operating_profit or 0,
            "net_income": fs.net_income or 0,
            "current_assets": None,  # DART API에서 미제공
            "current_liabilities": None,
            "debt_ratio": fs.debt_ratio or 0,
            "current_ratio": None,
            "interest_coverage": None,
        }

    # YoY 성장률 계산
    years_sorted = sorted(years_data.keys(), reverse=True)
    yoy_growth = {"revenue": 0, "operating_income": 0, "net_income": 0}

    if len(years_sorted) >= 2:
        curr = years_data[years_sorted[0]]
        prev = years_data[years_sorted[1]]

        if prev["revenue"] and prev["revenue"] > 0:
            yoy_growth["revenue"] = round((curr["revenue"] - prev["revenue"]) / prev["revenue"] * 100, 1)
        if prev["operating_income"] and prev["operating_income"] != 0:
            yoy_growth["operating_income"] = round((curr["operating_income"] - prev["operating_income"]) / abs(prev["operating_income"]) * 100, 1)
        if prev["net_income"] and prev["net_income"] != 0:
            yoy_growth["net_income"] = round((curr["net_income"] - prev["net_income"]) / abs(prev["net_income"]) * 100, 1)

    # 재무건전성 판단
    if years_data:
        latest = years_data[years_sorted[0]] if years_sorted else {}
        debt_ratio = latest.get("debt_ratio", 0) or 0

        if debt_ratio < 100:
            health = "EXCELLENT"
        elif debt_ratio < 150:
            health = "GOOD"
        elif debt_ratio < 200:
            health = "CAUTION"
        elif debt_ratio < 300:
            health = "WARNING"
        else:
            health = "CRITICAL"

        # 성장 중이면 IMPROVING
        if yoy_growth["revenue"] > 20 and yoy_growth["net_income"] > 0:
            health = "IMPROVING"
    else:
        health = "CAUTION"

    return {
        "source": "DART",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "years": years_data,
        "yoy_growth": yoy_growth,
        "financial_health": health,
    }


def generate_loan_exposure(corp_name: str, scenario: str, total_exposure: int, internal_grade: str) -> dict:
    """대출 익스포저 생성"""
    # 시나리오별 구성 비율
    if "스타트업" in scenario or "고성장" in scenario:
        secured_ratio = 0.30
        unsecured_ratio = 0.60
        fx_ratio = 0.10
    elif "수출" in scenario:
        secured_ratio = 0.45
        unsecured_ratio = 0.35
        fx_ratio = 0.20
    else:
        secured_ratio = 0.55
        unsecured_ratio = 0.35
        fx_ratio = 0.10

    secured = int(total_exposure * secured_ratio)
    unsecured = int(total_exposure * unsecured_ratio)
    fx = total_exposure - secured - unsecured

    return {
        "as_of_date": "2026-01-31",
        "total_exposure_krw": total_exposure,
        "yearly_trend": [
            {"year": 2024, "secured": int(secured * 0.7 / 100000000), "unsecured": int(unsecured * 0.7 / 100000000), "fx": int(fx * 0.7 / 100000000), "total": int(total_exposure * 0.7 / 100000000)},
            {"year": 2025, "secured": int(secured * 0.85 / 100000000), "unsecured": int(unsecured * 0.85 / 100000000), "fx": int(fx * 0.85 / 100000000), "total": int(total_exposure * 0.85 / 100000000)},
            {"year": 2026, "secured": int(secured / 100000000), "unsecured": int(unsecured / 100000000), "fx": int(fx / 100000000), "total": int(total_exposure / 100000000)},
        ],
        "composition": {
            "secured_loan": {"amount": secured, "ratio": round(secured_ratio * 100, 1)},
            "unsecured_loan": {"amount": unsecured, "ratio": round(unsecured_ratio * 100, 1)},
            "fx_loan": {"amount": fx, "ratio": round(fx_ratio * 100, 1)},
        },
        "risk_indicators": {
            "overdue_flag": False,
            "overdue_days": 0,
            "overdue_amount": 0,
            "watch_list": False,
            "watch_list_reason": None,
            "internal_grade": internal_grade,
            "grade_change": None,
            "next_review_date": "2026-06-30",
        },
    }


def generate_deposit_trend(total_exposure: int) -> dict:
    """예금 추이 생성"""
    avg_balance = int(total_exposure * 0.15)  # 여신의 15% 수준

    balances = []
    for i, month in enumerate(["2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12", "2026-01"]):
        variation = random.uniform(0.85, 1.15)
        balances.append({"month": month, "balance": int(avg_balance * variation)})

    return {
        "monthly_balance": balances,
        "current_balance": balances[-1]["balance"],
        "avg_balance_6m": int(sum(b["balance"] for b in balances) / len(balances)),
        "min_balance_6m": min(b["balance"] for b in balances),
        "max_balance_6m": max(b["balance"] for b in balances),
        "trend": random.choice(["INCREASING", "STABLE", "STABLE"]),
        "volatility": "LOW",
        "large_withdrawal_alerts": [],
    }


def generate_card_usage(total_exposure: int) -> dict:
    """카드 사용 내역 생성"""
    monthly_avg = int(total_exposure * 0.005)  # 여신의 0.5% 수준

    usages = []
    for i, month in enumerate(["2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12", "2026-01"]):
        variation = random.uniform(0.8, 1.2)
        amount = int(monthly_avg * variation)
        tx_count = int(amount / 200000)  # 건당 20만원 가정
        usages.append({"month": month, "amount": amount, "tx_count": tx_count})

    return {
        "monthly_usage": usages,
        "category_breakdown": {
            "travel": round(random.uniform(20, 40), 1),
            "entertainment": round(random.uniform(10, 20), 1),
            "office_supplies": round(random.uniform(15, 25), 1),
            "fuel": round(random.uniform(5, 15), 1),
            "others": round(random.uniform(10, 20), 1),
        },
        "card_limit": monthly_avg * 3,
        "utilization_rate": round(random.uniform(40, 70), 1),
        "avg_monthly_usage": int(sum(u["amount"] for u in usages) / len(usages)),
        "usage_trend": "STABLE",
        "anomaly_flags": [],
    }


def generate_collateral(corp_name: str, scenario: str, secured_loan: int) -> dict:
    """담보 정보 생성"""
    if secured_loan == 0:
        return {
            "collaterals": [],
            "total_collateral_value": 0,
            "total_loan_against": 0,
            "avg_ltv": 0,
            "high_ltv_collaterals": [],
            "expiring_appraisals": [],
        }

    ltv = random.uniform(45, 65)
    collateral_value = int(secured_loan / (ltv / 100))

    return {
        "collaterals": [
            {
                "id": f"COL-{corp_name[:2].upper()}-001",
                "type": "REAL_ESTATE",
                "description": f"{corp_name} 사옥/공장",
                "location": {
                    "address": "서울특별시 또는 경기도",
                    "coordinates": {"lat": 37.5, "lng": 127.0},
                },
                "appraisal": {
                    "value": collateral_value,
                    "date": "2024-06-15",
                    "appraiser": "한국감정원",
                    "next_appraisal_date": "2026-06-15",
                    "market_trend": "STABLE",
                },
                "loan_amount": secured_loan,
                "ltv_ratio": round(ltv, 1),
                "nearby_development": None,
                "risk_factors": [],
            }
        ],
        "total_collateral_value": collateral_value,
        "total_loan_against": secured_loan,
        "avg_ltv": round(ltv, 1),
        "high_ltv_collaterals": [],
        "expiring_appraisals": [],
    }


def generate_trade_finance(scenario: str, total_exposure: int) -> dict:
    """무역금융 생성"""
    if "수출" in scenario:
        export_ratio = 0.7
        import_ratio = 0.3
    elif "IT" in scenario or "AI" in scenario:
        export_ratio = 0.3
        import_ratio = 0.2
    else:
        export_ratio = 0.1
        import_ratio = 0.1

    export_amount = int(total_exposure * export_ratio * 0.01)  # USD
    import_amount = int(total_exposure * import_ratio * 0.01)

    export_monthly = []
    import_monthly = []
    for month in ["2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12", "2026-01"]:
        export_monthly.append({"month": month, "amount_usd": int(export_amount * random.uniform(0.8, 1.2))})
        import_monthly.append({"month": month, "amount_usd": int(import_amount * random.uniform(0.8, 1.2))})

    net_position = export_amount - import_amount
    hedge_ratio = random.uniform(40, 70) if abs(net_position) > 100000 else 0

    return {
        "export": {
            "monthly_receivables": export_monthly if export_amount > 0 else [],
            "current_receivables_usd": export_monthly[-1]["amount_usd"] if export_monthly else 0,
            "avg_collection_days": random.randint(35, 55),
            "overdue_receivables_usd": 0,
            "major_countries": ["US", "JP", "DE"][:2] if export_amount > 0 else [],
            "country_concentration": {"US": 45, "JP": 35, "DE": 20} if export_amount > 0 else {},
        },
        "import": {
            "monthly_payables": import_monthly if import_amount > 0 else [],
            "current_payables_usd": import_monthly[-1]["amount_usd"] if import_monthly else 0,
            "major_countries": ["CN", "JP"][:2] if import_amount > 0 else [],
            "country_concentration": {"CN": 55, "JP": 45} if import_amount > 0 else {},
        },
        "usance": {
            "limit_usd": int(import_amount * 1.5) if import_amount > 0 else 0,
            "utilized_usd": import_amount,
            "utilization_rate": round(import_amount / (import_amount * 1.5) * 100, 1) if import_amount > 0 else 0,
            "avg_tenor_days": 60,
            "upcoming_maturities": [],
        },
        "fx_exposure": {
            "net_position_usd": net_position,
            "hedge_ratio": round(hedge_ratio, 1),
            "hedge_instruments": ["forward"] if hedge_ratio > 0 else [],
            "var_1d_usd": int(abs(net_position) * 0.02),
        },
    }


def generate_risk_alerts(corp_name: str, scenario: str, financial_health: str, loan_exposure: dict, trade_finance: dict) -> list:
    """리스크 알림 생성"""
    alerts = []

    # 신용대출 비중 높으면 경고
    unsecured_ratio = loan_exposure["composition"]["unsecured_loan"]["ratio"]
    if unsecured_ratio > 50:
        alerts.append({
            "id": f"RISK-{corp_name[:2].upper()}-001",
            "severity": "LOW",
            "category": "LOAN",
            "signal_type": "DIRECT",
            "title": "신용대출 비중 과다",
            "description": f"신용대출 비중 {unsecured_ratio}%, 담보 확충 모니터링 필요.",
            "recommended_action": "담보 추가 또는 기술보증 활용 검토",
            "detected_at": datetime.now(timezone.utc).isoformat(),
        })

    # 환헤지 부족
    fx_exposure = trade_finance.get("fx_exposure", {})
    if fx_exposure.get("net_position_usd", 0) > 500000 and fx_exposure.get("hedge_ratio", 0) < 50:
        alerts.append({
            "id": f"RISK-{corp_name[:2].upper()}-002",
            "severity": "MED",
            "category": "TRADE",
            "signal_type": "ENVIRONMENT",
            "title": "환헤지 부족",
            "description": f"환헤지 비율 {fx_exposure['hedge_ratio']}%, 순외화포지션 ${fx_exposure['net_position_usd']:,} 노출.",
            "recommended_action": "선물환 또는 옵션을 통한 환헤지 비율 확대 권고",
            "detected_at": datetime.now(timezone.utc).isoformat(),
        })

    # 재무건전성 경고
    if financial_health in ["WARNING", "CRITICAL"]:
        alerts.append({
            "id": f"RISK-{corp_name[:2].upper()}-003",
            "severity": "HIGH" if financial_health == "CRITICAL" else "MED",
            "category": "FINANCIAL",
            "signal_type": "DIRECT",
            "title": "재무건전성 주의",
            "description": f"재무건전성 등급 {financial_health}, 부채비율 모니터링 필요.",
            "recommended_action": "정기심사 시 재무구조 개선 계획 확인",
            "detected_at": datetime.now(timezone.utc).isoformat(),
        })

    return alerts


def generate_opportunities(corp_name: str, scenario: str, loan_exposure: dict, trade_finance: dict) -> list:
    """영업 기회 생성"""
    opportunities = []

    if "고성장" in scenario or "스타트업" in scenario:
        opportunities.append(f"고성장 기업 - 성장 자금 지원 및 추가 여신 기회")

    if "수출" in scenario:
        opportunities.append(f"수출 비중 높음 - 수출금융/무역보험 패키지 제안")

    if "IT" in scenario or "AI" in scenario:
        opportunities.append(f"기술 기업 - 기술금융 우대금리 적용 검토")

    # LTV 여유
    collateral = loan_exposure.get("composition", {}).get("secured_loan", {})
    if collateral.get("ratio", 0) > 40:
        opportunities.append(f"담보 여력 충분 - 추가 시설자금 대출 가능")

    # 카드 크로스셀
    opportunities.append(f"법인카드 이용 활성화 - 마일리지/포인트 카드 크로스셀 기회")

    return opportunities


async def main():
    print("=" * 60)
    print("Banking Data 생성 (DART 재무제표 연동)")
    print("=" * 60)

    # 1. DART corp codes 로드
    print("\n[Step 1] DART corp codes 로드...")
    await load_corp_codes()

    # 2. DB 연결
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(
        DATABASE_URL.replace("?sslmode=require", ""),
        ssl=ssl_context,
        statement_cache_size=0,
    )

    try:
        for corp_info in TARGET_CORPS:
            corp_name = corp_info["name"]
            scenario = corp_info["scenario"]
            industry = corp_info["industry"]

            print(f"\n{'='*50}")
            print(f"[{corp_name}] 처리 중...")
            print(f"  시나리오: {scenario}")

            # 2-1. corp_id 조회
            row = await conn.fetchrow(
                "SELECT corp_id, dart_corp_code FROM corp WHERE corp_name LIKE $1",
                f"%{corp_name}%"
            )
            if not row:
                print(f"  [SKIP] DB에서 corp_id를 찾을 수 없음")
                continue

            corp_id = row["corp_id"]
            dart_corp_code = row["dart_corp_code"]
            print(f"  corp_id: {corp_id}, dart_corp_code: {dart_corp_code}")

            # 2-2. DART 재무제표 조회
            print(f"  [DART] 재무제표 조회 중...")
            dart_financials = []
            if dart_corp_code:
                try:
                    dart_financials = await get_financial_statements(dart_corp_code)
                    print(f"  [DART] {len(dart_financials)}개년 재무제표 조회 완료")
                    for fs in dart_financials:
                        revenue_bil = (fs.revenue or 0) / 100000000
                        print(f"    - {fs.bsns_year}: 매출 {revenue_bil:.0f}억, 순이익 {(fs.net_income or 0) / 100000000:.0f}억")
                except Exception as e:
                    print(f"  [DART] 재무제표 조회 실패: {e}")

            # 2-3. Banking Data 생성
            financial_statements = build_financial_statements_json(dart_financials, corp_name)

            # 총 여신 규모 추정 (매출의 10-20%)
            if dart_financials and dart_financials[0].revenue:
                total_exposure = int(dart_financials[0].revenue * random.uniform(0.10, 0.20))
            else:
                total_exposure = random.randint(2000000000, 10000000000)  # 20억~100억

            # 내부등급 결정
            health = financial_statements.get("financial_health", "CAUTION")
            grade_map = {
                "EXCELLENT": "A1",
                "GOOD": "A2",
                "IMPROVING": "B1",
                "CAUTION": "B2",
                "WARNING": "C1",
                "CRITICAL": "C2",
            }
            internal_grade = grade_map.get(health, "B2")

            loan_exposure = generate_loan_exposure(corp_name, scenario, total_exposure, internal_grade)
            deposit_trend = generate_deposit_trend(total_exposure)
            card_usage = generate_card_usage(total_exposure)
            collateral = generate_collateral(corp_name, scenario, loan_exposure["composition"]["secured_loan"]["amount"])
            trade_finance = generate_trade_finance(scenario, total_exposure)
            risk_alerts = generate_risk_alerts(corp_name, scenario, health, loan_exposure, trade_finance)
            opportunities = generate_opportunities(corp_name, scenario, loan_exposure, trade_finance)

            print(f"  [생성] 총 여신: {total_exposure / 100000000:.0f}억원, 등급: {internal_grade}")
            print(f"  [생성] 리스크: {len(risk_alerts)}건, 기회: {len(opportunities)}건")

            # 2-4. DB 저장
            query = """
                INSERT INTO rkyc_banking_data (
                    corp_id, data_date, loan_exposure, deposit_trend, card_usage,
                    collateral_detail, trade_finance, financial_statements,
                    risk_alerts, opportunity_signals
                ) VALUES (
                    $1, $2, $3::jsonb, $4::jsonb, $5::jsonb,
                    $6::jsonb, $7::jsonb, $8::jsonb,
                    $9::jsonb, $10::jsonb
                )
                ON CONFLICT (corp_id, data_date) DO UPDATE SET
                    loan_exposure = EXCLUDED.loan_exposure,
                    deposit_trend = EXCLUDED.deposit_trend,
                    card_usage = EXCLUDED.card_usage,
                    collateral_detail = EXCLUDED.collateral_detail,
                    trade_finance = EXCLUDED.trade_finance,
                    financial_statements = EXCLUDED.financial_statements,
                    risk_alerts = EXCLUDED.risk_alerts,
                    opportunity_signals = EXCLUDED.opportunity_signals,
                    updated_at = NOW()
                RETURNING id
            """

            result = await conn.fetchval(
                query,
                corp_id,
                date(2026, 1, 31),
                json.dumps(loan_exposure),
                json.dumps(deposit_trend),
                json.dumps(card_usage),
                json.dumps(collateral),
                json.dumps(trade_finance),
                json.dumps(financial_statements),
                json.dumps(risk_alerts),
                json.dumps(opportunities),
            )

            print(f"  [DB] 저장 완료: id={result}")

        # 3. 결과 확인
        print(f"\n{'='*60}")
        print("[결과 확인]")
        rows = await conn.fetch("""
            SELECT
                c.corp_name,
                b.corp_id,
                b.data_date,
                b.loan_exposure->>'total_exposure_krw' as exposure,
                b.financial_statements->>'financial_health' as health,
                jsonb_array_length(b.risk_alerts) as risk_count,
                jsonb_array_length(b.opportunity_signals) as opp_count
            FROM rkyc_banking_data b
            JOIN corp c ON c.corp_id = b.corp_id
            ORDER BY b.updated_at DESC
            LIMIT 10
        """)

        print(f"\n  최근 Banking Data ({len(rows)}건):")
        for row in rows:
            exposure = int(row["exposure"] or 0) / 100000000
            print(f"    - {row['corp_name']}: {exposure:.0f}억원, {row['health']}, 리스크 {row['risk_count']}건")

    finally:
        await conn.close()

    print(f"\n{'='*60}")
    print("완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
