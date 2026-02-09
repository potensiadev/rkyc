"""
DART API로 하림 기업 정보 조회 및 DB 삽입 스크립트
"""

import asyncio
import json
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.dart_api import (
    get_corp_code,
    get_company_info,
    get_largest_shareholders,
    get_financial_statements,
    get_extended_fact_profile,
    load_corp_codes,
)


async def main():
    """하림 기업 정보 조회"""

    # 1. Corp Code 로드
    print("="*60)
    print("1. DART Corp Code 목록 로드 중...")
    await load_corp_codes()

    # 2. 하림 Corp Code 조회
    print("\n2. '하림' Corp Code 조회 중...")
    corp_code = await get_corp_code(corp_name="하림")

    if not corp_code:
        print("❌ '하림' 기업을 찾을 수 없습니다.")
        # 유사한 이름으로 재검색
        print("\n'하림' 관련 기업 검색...")
        from app.services.dart_api import _corp_code_by_name, _normalize_corp_name

        search_term = _normalize_corp_name("하림")
        matches = [
            (name, code) for name, code in _corp_code_by_name.items()
            if search_term in name or "하림" in name
        ]

        if matches:
            print(f"\n찾은 유사 기업:")
            for name, code in matches[:10]:
                print(f"  - {name}: {code}")

            # 첫 번째 매칭 사용
            corp_code = matches[0][1]
            print(f"\n첫 번째 매칭 사용: {matches[0][0]} ({corp_code})")
        else:
            return

    print(f"✅ Corp Code: {corp_code}")

    # 3. 기업개황 조회
    print("\n3. 기업개황 조회 중...")
    company_info = await get_company_info(corp_code)

    if company_info:
        print(f"✅ 기업명: {company_info.corp_name}")
        print(f"   영문명: {company_info.corp_name_eng}")
        print(f"   종목명: {company_info.stock_name}")
        print(f"   종목코드: {company_info.stock_code}")
        print(f"   대표이사: {company_info.ceo_name}")
        print(f"   법인구분: {company_info.corp_cls}")
        print(f"   법인등록번호: {company_info.jurir_no}")
        print(f"   사업자등록번호: {company_info.bizr_no}")
        print(f"   주소: {company_info.adres}")
        print(f"   홈페이지: {company_info.hm_url}")
        print(f"   업종코드: {company_info.induty_code}")
        print(f"   설립일: {company_info.est_dt}")
        print(f"   결산월: {company_info.acc_mt}")
    else:
        print("❌ 기업개황을 찾을 수 없습니다.")

    # 4. 최대주주 조회
    print("\n4. 최대주주 현황 조회 중...")
    shareholders = await get_largest_shareholders(corp_code)

    if shareholders:
        print(f"✅ 최대주주 {len(shareholders)}명:")
        for sh in shareholders[:5]:
            print(f"   - {sh.nm}: {sh.trmend_posesn_stock_qota_rt}%")
    else:
        print("❌ 최대주주 정보를 찾을 수 없습니다.")

    # 5. 재무제표 조회
    print("\n5. 재무제표 조회 중...")
    financials = await get_financial_statements(corp_code)

    if financials:
        print(f"✅ 재무제표 {len(financials)}년치:")
        for fs in financials:
            print(f"   - {fs.bsns_year}년: 매출 {fs.revenue:,}원, 영업이익 {fs.operating_profit:,}원" if fs.revenue else f"   - {fs.bsns_year}년: 데이터 없음")
    else:
        print("❌ 재무제표를 찾을 수 없습니다.")

    # 6. SQL 생성
    print("\n" + "="*60)
    print("6. SQL INSERT 문 생성...")
    print("="*60)

    if company_info:
        # corp_id 생성 (사업자등록번호 기반)
        biz_no = company_info.bizr_no or ""
        if biz_no:
            corp_id = f"{biz_no[:4]}-{biz_no[4:]}" if len(biz_no) >= 10 else biz_no
        else:
            corp_id = f"DART-{corp_code}"

        print(f"\n-- corp_id: {corp_id}")

        # corp 테이블 INSERT
        corp_sql = f"""
-- ============================================================
-- 하림 기업 정보 삽입 (DART API 기반)
-- ============================================================

-- corp 테이블 삽입
INSERT INTO corp (
    corp_id,
    corp_name,
    corp_reg_no,
    biz_no,
    industry_code,
    dart_corp_code,
    established_date,
    headquarters,
    corp_class,
    homepage_url,
    jurir_no,
    corp_name_eng,
    acc_mt,
    dart_updated_at
) VALUES (
    '{corp_id}',
    '{company_info.corp_name}',
    '{company_info.jurir_no or ""}',
    '{company_info.bizr_no or ""}',
    '{company_info.induty_code or ""}',
    '{corp_code}',
    '{company_info.est_dt or ""}',
    '{company_info.adres or ""}',
    '{company_info.corp_cls or ""}',
    '{company_info.hm_url or ""}',
    '{company_info.jurir_no or ""}',
    '{company_info.corp_name_eng or ""}',
    '{company_info.acc_mt or ""}',
    NOW()
)
ON CONFLICT (corp_id) DO UPDATE SET
    corp_name = EXCLUDED.corp_name,
    corp_reg_no = EXCLUDED.corp_reg_no,
    biz_no = EXCLUDED.biz_no,
    industry_code = EXCLUDED.industry_code,
    dart_corp_code = EXCLUDED.dart_corp_code,
    established_date = EXCLUDED.established_date,
    headquarters = EXCLUDED.headquarters,
    corp_class = EXCLUDED.corp_class,
    homepage_url = EXCLUDED.homepage_url,
    jurir_no = EXCLUDED.jurir_no,
    corp_name_eng = EXCLUDED.corp_name_eng,
    acc_mt = EXCLUDED.acc_mt,
    dart_updated_at = NOW();
"""
        print(corp_sql)

        # rkyc_banking_data 테이블 INSERT (Mock 데이터)
        # 하림은 식품업체이므로 적절한 Mock 데이터 생성

        # 재무 데이터 기반 loan_exposure 계산
        if financials:
            latest = financials[0] if financials else None
            total_assets = latest.total_assets if latest and latest.total_assets else 100000000000
            total_exposure = int(total_assets * 0.15)  # 자산의 15% 정도를 여신으로 가정
        else:
            total_exposure = 15000000000

        banking_sql = f"""
-- rkyc_banking_data 테이블 삽입 (하림 - 식품/축산)
INSERT INTO rkyc_banking_data (corp_id, data_date, loan_exposure, deposit_trend, card_usage, collateral_detail, trade_finance, financial_statements, risk_alerts, opportunity_signals)
VALUES (
    '{corp_id}',
    '2026-01-31',
    -- loan_exposure (식품/축산업)
    '{{
        "as_of_date": "2026-01-31",
        "total_exposure_krw": {total_exposure},
        "yearly_trend": [
            {{"year": 2024, "secured": {int(total_exposure*0.5/1000000000)}, "unsecured": {int(total_exposure*0.3/1000000000)}, "fx": {int(total_exposure*0.2/1000000000)}, "total": {int(total_exposure*0.8/1000000000)}}},
            {{"year": 2025, "secured": {int(total_exposure*0.55/1000000000)}, "unsecured": {int(total_exposure*0.32/1000000000)}, "fx": {int(total_exposure*0.23/1000000000)}, "total": {int(total_exposure*0.9/1000000000)}}},
            {{"year": 2026, "secured": {int(total_exposure*0.6/1000000000)}, "unsecured": {int(total_exposure*0.25/1000000000)}, "fx": {int(total_exposure*0.15/1000000000)}, "total": {int(total_exposure/1000000000)}}}
        ],
        "composition": {{
            "secured_loan": {{"amount": {int(total_exposure*0.6)}, "ratio": 60.0}},
            "unsecured_loan": {{"amount": {int(total_exposure*0.25)}, "ratio": 25.0}},
            "fx_loan": {{"amount": {int(total_exposure*0.15)}, "ratio": 15.0}}
        }},
        "risk_indicators": {{
            "overdue_flag": false,
            "overdue_days": 0,
            "overdue_amount": 0,
            "watch_list": false,
            "watch_list_reason": null,
            "internal_grade": "A3",
            "grade_change": null,
            "next_review_date": "2026-06-30"
        }}
    }}'::jsonb,
    -- deposit_trend
    '{{
        "monthly_balance": [
            {{"month": "2025-07", "balance": 4500000000}},
            {{"month": "2025-08", "balance": 4800000000}},
            {{"month": "2025-09", "balance": 4600000000}},
            {{"month": "2025-10", "balance": 5100000000}},
            {{"month": "2025-11", "balance": 4900000000}},
            {{"month": "2025-12", "balance": 5500000000}},
            {{"month": "2026-01", "balance": 5200000000}}
        ],
        "current_balance": 5200000000,
        "avg_balance_6m": 4943000000,
        "min_balance_6m": 4500000000,
        "max_balance_6m": 5500000000,
        "trend": "STABLE",
        "volatility": "LOW",
        "large_withdrawal_alerts": []
    }}'::jsonb,
    -- card_usage
    '{{
        "monthly_usage": [
            {{"month": "2025-07", "amount": 85000000, "tx_count": 456}},
            {{"month": "2025-08", "amount": 92000000, "tx_count": 489}},
            {{"month": "2025-09", "amount": 88000000, "tx_count": 467}},
            {{"month": "2025-10", "amount": 95000000, "tx_count": 512}},
            {{"month": "2025-11", "amount": 98000000, "tx_count": 534}},
            {{"month": "2025-12", "amount": 115000000, "tx_count": 612}},
            {{"month": "2026-01", "amount": 92000000, "tx_count": 498}}
        ],
        "category_breakdown": {{
            "travel": 18.5,
            "entertainment": 12.2,
            "office_supplies": 15.8,
            "fuel": 28.5,
            "others": 25.0
        }},
        "card_limit": 150000000,
        "utilization_rate": 61.3,
        "avg_monthly_usage": 95000000,
        "usage_trend": "STABLE",
        "anomaly_flags": []
    }}'::jsonb,
    -- collateral_detail (식품/축산 특성)
    '{{
        "collaterals": [
            {{
                "id": "COL-HR-001",
                "type": "REAL_ESTATE",
                "description": "익산 도축/가공 공장",
                "location": {{
                    "address": "전북 익산시 함열읍 산업단지",
                    "coordinates": {{"lat": 35.9483, "lng": 126.9578}}
                }},
                "appraisal": {{
                    "value": 25000000000,
                    "date": "2024-08-15",
                    "appraiser": "한국감정원",
                    "next_appraisal_date": "2026-08-15",
                    "market_trend": "STABLE"
                }},
                "loan_amount": {int(total_exposure*0.4)},
                "ltv_ratio": {round(total_exposure*0.4/25000000000*100, 1)},
                "nearby_development": null,
                "risk_factors": []
            }},
            {{
                "id": "COL-HR-002",
                "type": "REAL_ESTATE",
                "description": "전북 김제 사료공장",
                "location": {{
                    "address": "전북 김제시 백산면 산업단지",
                    "coordinates": {{"lat": 35.7983, "lng": 126.8812}}
                }},
                "appraisal": {{
                    "value": 18000000000,
                    "date": "2024-06-20",
                    "appraiser": "한국감정원",
                    "next_appraisal_date": "2026-06-20",
                    "market_trend": "STABLE"
                }},
                "loan_amount": {int(total_exposure*0.2)},
                "ltv_ratio": {round(total_exposure*0.2/18000000000*100, 1)},
                "nearby_development": null,
                "risk_factors": []
            }}
        ],
        "total_collateral_value": 43000000000,
        "total_loan_against": {int(total_exposure*0.6)},
        "avg_ltv": {round(total_exposure*0.6/43000000000*100, 1)},
        "high_ltv_collaterals": [],
        "expiring_appraisals": []
    }}'::jsonb,
    -- trade_finance (식품 수출입)
    '{{
        "export": {{
            "monthly_receivables": [
                {{"month": "2025-07", "amount_usd": 850000}},
                {{"month": "2025-08", "amount_usd": 920000}},
                {{"month": "2025-09", "amount_usd": 880000}},
                {{"month": "2025-10", "amount_usd": 950000}},
                {{"month": "2025-11", "amount_usd": 1020000}},
                {{"month": "2025-12", "amount_usd": 1150000}},
                {{"month": "2026-01", "amount_usd": 980000}}
            ],
            "current_receivables_usd": 980000,
            "avg_collection_days": 45,
            "overdue_receivables_usd": 0,
            "major_countries": ["JP", "HK", "VN", "PH"],
            "country_concentration": {{"JP": 35, "HK": 28, "VN": 22, "PH": 15}}
        }},
        "import": {{
            "monthly_payables": [
                {{"month": "2025-07", "amount_usd": 2200000}},
                {{"month": "2025-08", "amount_usd": 2450000}},
                {{"month": "2025-09", "amount_usd": 2380000}},
                {{"month": "2025-10", "amount_usd": 2620000}},
                {{"month": "2025-11", "amount_usd": 2780000}},
                {{"month": "2025-12", "amount_usd": 2950000}},
                {{"month": "2026-01", "amount_usd": 2650000}}
            ],
            "current_payables_usd": 2650000,
            "major_countries": ["US", "BR", "AR"],
            "country_concentration": {{"US": 42, "BR": 35, "AR": 23}}
        }},
        "usance": {{
            "limit_usd": 5000000,
            "utilized_usd": 2650000,
            "utilization_rate": 53.0,
            "avg_tenor_days": 90,
            "upcoming_maturities": []
        }},
        "fx_exposure": {{
            "net_position_usd": -1670000,
            "hedge_ratio": 65.0,
            "hedge_instruments": ["forward"],
            "var_1d_usd": 42000
        }}
    }}'::jsonb,
    -- financial_statements (DART 기반)
    '{{
        "source": "DART",
        "last_updated": "2026-01-15",
        "years": {{
            "2023": {{
                "assets": {financials[2].total_assets if len(financials) > 2 and financials[2].total_assets else 350000000000},
                "liabilities": {financials[2].total_liabilities if len(financials) > 2 and financials[2].total_liabilities else 220000000000},
                "equity": {financials[2].total_equity if len(financials) > 2 and financials[2].total_equity else 130000000000},
                "revenue": {financials[2].revenue if len(financials) > 2 and financials[2].revenue else 3800000000000},
                "operating_income": {financials[2].operating_profit if len(financials) > 2 and financials[2].operating_profit else 85000000000},
                "net_income": {financials[2].net_income if len(financials) > 2 and financials[2].net_income else 52000000000},
                "debt_ratio": {financials[2].debt_ratio if len(financials) > 2 and financials[2].debt_ratio else 169.2},
                "current_ratio": 125.0,
                "interest_coverage": 4.2
            }},
            "2024": {{
                "assets": {financials[1].total_assets if len(financials) > 1 and financials[1].total_assets else 380000000000},
                "liabilities": {financials[1].total_liabilities if len(financials) > 1 and financials[1].total_liabilities else 235000000000},
                "equity": {financials[1].total_equity if len(financials) > 1 and financials[1].total_equity else 145000000000},
                "revenue": {financials[1].revenue if len(financials) > 1 and financials[1].revenue else 4200000000000},
                "operating_income": {financials[1].operating_profit if len(financials) > 1 and financials[1].operating_profit else 95000000000},
                "net_income": {financials[1].net_income if len(financials) > 1 and financials[1].net_income else 62000000000},
                "debt_ratio": {financials[1].debt_ratio if len(financials) > 1 and financials[1].debt_ratio else 162.1},
                "current_ratio": 128.0,
                "interest_coverage": 4.5
            }},
            "2025": {{
                "assets": {financials[0].total_assets if financials and financials[0].total_assets else 420000000000},
                "liabilities": {financials[0].total_liabilities if financials and financials[0].total_liabilities else 255000000000},
                "equity": {financials[0].total_equity if financials and financials[0].total_equity else 165000000000},
                "revenue": {financials[0].revenue if financials and financials[0].revenue else 4500000000000},
                "operating_income": {financials[0].operating_profit if financials and financials[0].operating_profit else 105000000000},
                "net_income": {financials[0].net_income if financials and financials[0].net_income else 72000000000},
                "debt_ratio": {financials[0].debt_ratio if financials and financials[0].debt_ratio else 154.5},
                "current_ratio": 132.0,
                "interest_coverage": 4.8
            }}
        }},
        "yoy_growth": {{
            "revenue": 7.1,
            "operating_income": 10.5,
            "net_income": 16.1
        }},
        "financial_health": "GOOD"
    }}'::jsonb,
    -- risk_alerts (식품/축산 특성)
    '[
        {{
            "id": "RISK-HR-001",
            "severity": "MED",
            "category": "TRADE",
            "signal_type": "ENVIRONMENT",
            "title": "사료 원료 수입 의존",
            "description": "사료 원료(옥수수, 대두) 수입 의존도 높음. 미국/브라질 의존도 77%. 환율 및 국제 곡물가 변동 시 원가 상승 위험.",
            "recommended_action": "곡물 선물 헤지 또는 장기 구매 계약 검토 권고",
            "detected_at": "2026-01-31T09:00:00Z"
        }},
        {{
            "id": "RISK-HR-002",
            "severity": "LOW",
            "category": "INDUSTRY",
            "signal_type": "INDUSTRY",
            "title": "AI(조류인플루엔자) 상시 위험",
            "description": "축산업 특성상 AI 발생 시 살처분 및 이동 제한으로 매출/수익성 타격 가능.",
            "recommended_action": "방역 현황 및 보험 가입 여부 확인",
            "detected_at": "2026-01-31T09:00:00Z"
        }}
    ]'::jsonb,
    -- opportunity_signals (식품/축산 영업 기회)
    '[
        "일본/홍콩 수출 호조 - 수출금융 한도 확대 및 환헤지 상품 제안",
        "사료 수입 결제 - 유산스 한도 확대로 운전자금 부담 완화 가능",
        "법인카드 주유비 28.5% - 물류차량 특성, 주유 할인 제휴 카드 제안",
        "가금류 수요 증가 추세 - 시설 증설 투자 시 프로젝트 금융 기회",
        "담보 LTV 여유 - 운전자금 추가 여신 여력 있음"
    ]'::jsonb
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
    updated_at = NOW();

-- 검증
SELECT corp_id, corp_name, dart_corp_code FROM corp WHERE corp_name LIKE '%하림%';
SELECT corp_id, data_date, (loan_exposure->>'total_exposure_krw')::bigint as total_exposure FROM rkyc_banking_data WHERE corp_id = '{corp_id}';
"""
        print(banking_sql)

        # SQL 파일로 저장
        sql_path = os.path.join(os.path.dirname(__file__), '..', 'sql', 'seed_harim.sql')
        with open(sql_path, 'w', encoding='utf-8') as f:
            f.write(corp_sql)
            f.write("\n\n")
            f.write(banking_sql)

        print(f"\n✅ SQL 파일 저장됨: {sql_path}")


if __name__ == "__main__":
    asyncio.run(main())
