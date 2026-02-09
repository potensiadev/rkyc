"""
Supabase에 직접 연결하여 하림 banking data를 삽입하는 스크립트
복사/붙여넣기 0x0d 문제를 우회합니다.
"""
import asyncio
import ssl
import asyncpg

# Supabase Transaction Pooler 연결 정보
DATABASE_URL = "postgresql://postgres.jvvhfylycswfedppmkld:aMgngVn1YKhb8iki@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

async def main():
    # SSL 설정
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    print("[INFO] Supabase 연결 중...")

    conn = await asyncpg.connect(
        DATABASE_URL,
        ssl=ssl_context,
        statement_cache_size=0  # pgbouncer 호환
    )

    try:
        # 하림 banking data INSERT/UPDATE
        sql = """
INSERT INTO rkyc_banking_data (corp_id, data_date, loan_exposure, deposit_trend, card_usage, collateral_detail, trade_finance, financial_statements, risk_alerts, opportunity_signals)
VALUES (
    '4038-161113',
    '2026-01-31',
    '{"as_of_date":"2026-01-31","total_exposure_krw":120944754450,"yearly_trend":[{"year":2024,"secured":60,"unsecured":36,"fx":24,"total":96},{"year":2025,"secured":66,"unsecured":38,"fx":27,"total":108},{"year":2026,"secured":72,"unsecured":30,"fx":18,"total":120}],"composition":{"secured_loan":{"amount":72566852670,"ratio":60.0},"unsecured_loan":{"amount":30236188612,"ratio":25.0},"fx_loan":{"amount":18141713167,"ratio":15.0}},"risk_indicators":{"overdue_flag":false,"overdue_days":0,"overdue_amount":0,"watch_list":false,"watch_list_reason":null,"internal_grade":"B1","grade_change":"DOWN","next_review_date":"2026-06-30"}}'::jsonb,
    '{"monthly_balance":[{"month":"2025-07","balance":4500000000},{"month":"2025-08","balance":4800000000},{"month":"2025-09","balance":4600000000},{"month":"2025-10","balance":5100000000},{"month":"2025-11","balance":4900000000},{"month":"2025-12","balance":5500000000},{"month":"2026-01","balance":5200000000}],"current_balance":5200000000,"avg_balance_6m":4943000000,"min_balance_6m":4500000000,"max_balance_6m":5500000000,"trend":"STABLE","volatility":"LOW","large_withdrawal_alerts":[]}'::jsonb,
    '{"monthly_usage":[{"month":"2025-07","amount":85000000,"tx_count":456},{"month":"2025-08","amount":92000000,"tx_count":489},{"month":"2025-09","amount":88000000,"tx_count":467},{"month":"2025-10","amount":95000000,"tx_count":512},{"month":"2025-11","amount":98000000,"tx_count":534},{"month":"2025-12","amount":115000000,"tx_count":612},{"month":"2026-01","amount":92000000,"tx_count":498}],"category_breakdown":{"travel":18.5,"entertainment":12.2,"office_supplies":15.8,"fuel":28.5,"others":25.0},"card_limit":150000000,"utilization_rate":61.3,"avg_monthly_usage":95000000,"usage_trend":"STABLE","anomaly_flags":[]}'::jsonb,
    '{"collaterals":[{"id":"COL-HR-001","type":"REAL_ESTATE","description":"익산 도축가공 공장","location":{"address":"전북 익산시 함열읍 산업단지","coordinates":{"lat":35.9483,"lng":126.9578}},"appraisal":{"value":25000000000,"date":"2024-08-15","appraiser":"한국감정원","next_appraisal_date":"2026-08-15","market_trend":"STABLE"},"loan_amount":48377901780,"ltv_ratio":193.5,"nearby_development":null,"risk_factors":[]},{"id":"COL-HR-002","type":"REAL_ESTATE","description":"전북 김제 사료공장","location":{"address":"전북 김제시 백산면 산업단지","coordinates":{"lat":35.7983,"lng":126.8812}},"appraisal":{"value":18000000000,"date":"2024-06-20","appraiser":"한국감정원","next_appraisal_date":"2026-06-20","market_trend":"STABLE"},"loan_amount":24188950890,"ltv_ratio":134.4,"nearby_development":null,"risk_factors":[]}],"total_collateral_value":43000000000,"total_loan_against":72566852670,"avg_ltv":168.8,"high_ltv_collaterals":[],"expiring_appraisals":[]}'::jsonb,
    '{"export":{"monthly_receivables":[{"month":"2025-07","amount_usd":850000},{"month":"2025-08","amount_usd":920000},{"month":"2025-09","amount_usd":880000},{"month":"2025-10","amount_usd":950000},{"month":"2025-11","amount_usd":1020000},{"month":"2025-12","amount_usd":1150000},{"month":"2026-01","amount_usd":980000}],"current_receivables_usd":980000,"avg_collection_days":45,"overdue_receivables_usd":0,"major_countries":["JP","HK","VN","PH"],"country_concentration":{"JP":35,"HK":28,"VN":22,"PH":15}},"import":{"monthly_payables":[{"month":"2025-07","amount_usd":2200000},{"month":"2025-08","amount_usd":2450000},{"month":"2025-09","amount_usd":2380000},{"month":"2025-10","amount_usd":2620000},{"month":"2025-11","amount_usd":2780000},{"month":"2025-12","amount_usd":2950000},{"month":"2026-01","amount_usd":2650000}],"current_payables_usd":2650000,"major_countries":["US","BR","AR"],"country_concentration":{"US":42,"BR":35,"AR":23}},"usance":{"limit_usd":5000000,"utilized_usd":2650000,"utilization_rate":53.0,"avg_tenor_days":90,"upcoming_maturities":[]},"fx_exposure":{"net_position_usd":-1670000,"hedge_ratio":65.0,"hedge_instruments":["forward"],"var_1d_usd":42000}}'::jsonb,
    '{"source":"DART","last_updated":"2026-01-15","years":{"2023":{"assets":350000000000,"liabilities":220000000000,"equity":130000000000,"revenue":3800000000000,"operating_income":85000000000,"net_income":52000000000,"debt_ratio":169.2,"current_ratio":125.0,"interest_coverage":4.2},"2024":{"assets":822242764735,"liabilities":521549447397,"equity":300693317338,"revenue":1358340380389,"operating_income":35356963177,"net_income":10049710279,"debt_ratio":173.45,"current_ratio":128.0,"interest_coverage":4.5},"2025":{"assets":806298363000,"liabilities":530615681000,"equity":275682682000,"revenue":1233745815000,"operating_income":22119201000,"net_income":-17965857000,"debt_ratio":192.47,"current_ratio":132.0,"interest_coverage":4.8}},"yoy_growth":{"revenue":-9.2,"operating_income":-37.4,"net_income":-278.8},"financial_health":"CAUTION"}'::jsonb,
    '[{"id":"RISK-HR-001","severity":"HIGH","category":"FINANCIAL","signal_type":"DIRECT","title":"2025년 적자 전환","description":"2025년 당기순손실 -179억원 기록. 전년 대비 매출 -9.2%, 영업이익 -37.4% 감소. 부채비율 192% 상승.","recommended_action":"정기심사 시 수익성 개선 계획 및 현금흐름 점검 필요","detected_at":"2026-01-31T09:00:00Z"},{"id":"RISK-HR-002","severity":"MED","category":"TRADE","signal_type":"ENVIRONMENT","title":"사료 원료 수입 의존","description":"사료 원료(옥수수, 대두) 수입 의존도 높음. 미국/브라질 의존도 77%. 환율 및 국제 곡물가 변동 시 원가 상승 위험.","recommended_action":"곡물 선물 헤지 또는 장기 구매 계약 검토 권고","detected_at":"2026-01-31T09:00:00Z"},{"id":"RISK-HR-003","severity":"LOW","category":"INDUSTRY","signal_type":"INDUSTRY","title":"AI(조류인플루엔자) 상시 위험","description":"축산업 특성상 AI 발생 시 살처분 및 이동 제한으로 매출/수익성 타격 가능.","recommended_action":"방역 현황 및 보험 가입 여부 확인","detected_at":"2026-01-31T09:00:00Z"}]'::jsonb,
    '["일본/홍콩 수출 호조 - 수출금융 한도 확대 및 환헤지 상품 제안","사료 수입 결제 - 유산스 한도 확대로 운전자금 부담 완화 가능","법인카드 주유비 28.5% - 물류차량 특성, 주유 할인 제휴 카드 제안","가금류 수요 증가 추세 - 시설 증설 투자 시 프로젝트 금융 기회","담보 LTV 여유 - 운전자금 추가 여신 여력 있음"]'::jsonb
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
"""

        print("[INFO] SQL 실행 중...")
        result = await conn.execute(sql)
        print(f"[OK] 실행 완료: {result}")

        # 검증 쿼리
        print("\n[INFO] 검증 중...")
        row = await conn.fetchrow("""
            SELECT corp_id, data_date,
                   (loan_exposure->>'total_exposure_krw')::bigint as total_exposure,
                   jsonb_array_length(risk_alerts) as risk_count,
                   jsonb_array_length(opportunity_signals) as opportunity_count
            FROM rkyc_banking_data
            WHERE corp_id = '4038-161113'
        """)

        if row:
            print(f"[OK] 하림 banking data 삽입 완료!")
            print(f"    - Corp ID: {row['corp_id']}")
            print(f"    - Data Date: {row['data_date']}")
            print(f"    - Total Exposure: {row['total_exposure']:,} KRW")
            print(f"    - Risk Alerts: {row['risk_count']}개")
            print(f"    - Opportunities: {row['opportunity_count']}개")
        else:
            print("[ERROR] 데이터 검증 실패")

    finally:
        await conn.close()
        print("\n[INFO] 연결 종료")

if __name__ == "__main__":
    asyncio.run(main())
