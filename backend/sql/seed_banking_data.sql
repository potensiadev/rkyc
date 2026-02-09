-- ============================================================
-- rKYC Seed: Internal Banking Data for 4 Seed Companies
-- PRD: Internal Banking Data Integration v1.1
--
-- 시나리오:
-- 1. 엠케이전자: 수출 호조, 환헤지 부족 리스크
-- 2. 동부건설: 담보 인프라 수혜, 부채비율 상승 리스크
-- 3. 삼성전자: 대기업 우량, 시설투자 기회
-- 4. 휴림로봇: 스타트업 성장, 신용대출 비중 높음
-- ============================================================

-- 1. 엠케이전자 (8001-3719240) - 반도체, 수출 호조, 환헤지 부족
INSERT INTO rkyc_banking_data (corp_id, data_date, loan_exposure, deposit_trend, card_usage, collateral_detail, trade_finance, financial_statements, risk_alerts, opportunity_signals)
VALUES (
    '8001-3719240',
    '2026-01-31',
    -- loan_exposure
    '{
        "as_of_date": "2026-01-31",
        "total_exposure_krw": 12000000000,
        "yearly_trend": [
            {"year": 2024, "secured": 5000, "unsecured": 2000, "fx": 1000, "total": 8000},
            {"year": 2025, "secured": 6000, "unsecured": 2500, "fx": 1500, "total": 10000},
            {"year": 2026, "secured": 7000, "unsecured": 3000, "fx": 2000, "total": 12000}
        ],
        "composition": {
            "secured_loan": {"amount": 7000000000, "ratio": 58.3},
            "unsecured_loan": {"amount": 3000000000, "ratio": 25.0},
            "fx_loan": {"amount": 2000000000, "ratio": 16.7}
        },
        "risk_indicators": {
            "overdue_flag": false,
            "overdue_days": 0,
            "overdue_amount": 0,
            "watch_list": false,
            "watch_list_reason": null,
            "internal_grade": "A2",
            "grade_change": null,
            "next_review_date": "2026-06-30"
        }
    }'::jsonb,
    -- deposit_trend
    '{
        "monthly_balance": [
            {"month": "2025-07", "balance": 2500000000},
            {"month": "2025-08", "balance": 2800000000},
            {"month": "2025-09", "balance": 2600000000},
            {"month": "2025-10", "balance": 3100000000},
            {"month": "2025-11", "balance": 2900000000},
            {"month": "2025-12", "balance": 3200000000},
            {"month": "2026-01", "balance": 3500000000}
        ],
        "current_balance": 3500000000,
        "avg_balance_6m": 2943000000,
        "min_balance_6m": 2500000000,
        "max_balance_6m": 3500000000,
        "trend": "INCREASING",
        "volatility": "LOW",
        "large_withdrawal_alerts": []
    }'::jsonb,
    -- card_usage
    '{
        "monthly_usage": [
            {"month": "2025-07", "amount": 45000000, "tx_count": 234},
            {"month": "2025-08", "amount": 52000000, "tx_count": 267},
            {"month": "2025-09", "amount": 48000000, "tx_count": 245},
            {"month": "2025-10", "amount": 61000000, "tx_count": 312},
            {"month": "2025-11", "amount": 58000000, "tx_count": 298},
            {"month": "2025-12", "amount": 72000000, "tx_count": 356},
            {"month": "2026-01", "amount": 55000000, "tx_count": 278}
        ],
        "category_breakdown": {
            "travel": 35.2,
            "entertainment": 18.5,
            "office_supplies": 22.1,
            "fuel": 12.3,
            "others": 11.9
        },
        "card_limit": 100000000,
        "utilization_rate": 55.0,
        "avg_monthly_usage": 55857000,
        "usage_trend": "STABLE",
        "anomaly_flags": []
    }'::jsonb,
    -- collateral_detail
    '{
        "collaterals": [
            {
                "id": "COL-MK-001",
                "type": "REAL_ESTATE",
                "description": "울산 남구 무거동 반도체 공장",
                "location": {
                    "address": "울산광역시 남구 무거동 산업단지 123-45",
                    "coordinates": {"lat": 35.5384, "lng": 129.2569}
                },
                "appraisal": {
                    "value": 15000000000,
                    "date": "2024-08-15",
                    "appraiser": "한국감정원",
                    "next_appraisal_date": "2026-08-15",
                    "market_trend": "STABLE"
                },
                "loan_amount": 7000000000,
                "ltv_ratio": 46.7,
                "nearby_development": {
                    "project_name": "문수로 우회도로",
                    "distance_km": 1.8,
                    "impact": "MEDIUM",
                    "description": "2.71km 왕복 4차로, 교통 개선",
                    "expected_completion": "2028-12",
                    "status": "APPROVED"
                },
                "risk_factors": []
            }
        ],
        "total_collateral_value": 15000000000,
        "total_loan_against": 7000000000,
        "avg_ltv": 46.7,
        "high_ltv_collaterals": [],
        "expiring_appraisals": []
    }'::jsonb,
    -- trade_finance (환헤지 부족 리스크)
    '{
        "export": {
            "monthly_receivables": [
                {"month": "2025-07", "amount_usd": 2200000},
                {"month": "2025-08", "amount_usd": 2450000},
                {"month": "2025-09", "amount_usd": 2380000},
                {"month": "2025-10", "amount_usd": 2620000},
                {"month": "2025-11", "amount_usd": 2780000},
                {"month": "2025-12", "amount_usd": 2950000},
                {"month": "2026-01", "amount_usd": 3100000}
            ],
            "current_receivables_usd": 3100000,
            "avg_collection_days": 42,
            "overdue_receivables_usd": 0,
            "major_countries": ["US", "JP", "DE", "TW"],
            "country_concentration": {"US": 38, "JP": 25, "DE": 20, "TW": 17}
        },
        "import": {
            "monthly_payables": [
                {"month": "2025-07", "amount_usd": 1100000},
                {"month": "2025-08", "amount_usd": 1250000},
                {"month": "2025-09", "amount_usd": 1180000},
                {"month": "2025-10", "amount_usd": 1320000},
                {"month": "2025-11", "amount_usd": 1280000},
                {"month": "2025-12", "amount_usd": 1450000},
                {"month": "2026-01", "amount_usd": 1380000}
            ],
            "current_payables_usd": 1380000,
            "major_countries": ["JP", "TW", "CN"],
            "country_concentration": {"JP": 45, "TW": 35, "CN": 20}
        },
        "usance": {
            "limit_usd": 3000000,
            "utilized_usd": 1200000,
            "utilization_rate": 40.0,
            "avg_tenor_days": 90,
            "upcoming_maturities": []
        },
        "fx_exposure": {
            "net_position_usd": 1720000,
            "hedge_ratio": 35.0,
            "hedge_instruments": ["forward"],
            "var_1d_usd": 52000
        }
    }'::jsonb,
    -- financial_statements
    '{
        "source": "DART",
        "last_updated": "2026-01-15",
        "years": {
            "2023": {
                "assets": 45000000000,
                "liabilities": 28000000000,
                "equity": 17000000000,
                "revenue": 62000000000,
                "operating_income": 4800000000,
                "net_income": 3200000000,
                "current_assets": 18000000000,
                "current_liabilities": 12000000000,
                "debt_ratio": 164.7,
                "current_ratio": 150.0,
                "interest_coverage": 4.2
            },
            "2024": {
                "assets": 52000000000,
                "liabilities": 31000000000,
                "equity": 21000000000,
                "revenue": 71000000000,
                "operating_income": 5600000000,
                "net_income": 4100000000,
                "current_assets": 21000000000,
                "current_liabilities": 14000000000,
                "debt_ratio": 147.6,
                "current_ratio": 150.0,
                "interest_coverage": 4.8
            },
            "2025": {
                "assets": 58000000000,
                "liabilities": 33000000000,
                "equity": 25000000000,
                "revenue": 78000000000,
                "operating_income": 6200000000,
                "net_income": 4800000000,
                "current_assets": 24000000000,
                "current_liabilities": 15000000000,
                "debt_ratio": 132.0,
                "current_ratio": 160.0,
                "interest_coverage": 5.5
            }
        },
        "yoy_growth": {
            "revenue": 9.9,
            "operating_income": 10.7,
            "net_income": 17.1
        },
        "financial_health": "GOOD"
    }'::jsonb,
    -- risk_alerts
    '[
        {
            "id": "RISK-MK-001",
            "severity": "MED",
            "category": "TRADE",
            "signal_type": "ENVIRONMENT",
            "title": "환헤지 부족",
            "description": "환헤지 비율 35%, 순외화포지션 $1,720,000 노출. 환율 급변 시 환차손 위험.",
            "recommended_action": "선물환 또는 옵션을 통한 환헤지 비율 50% 이상 확대 권고",
            "detected_at": "2026-01-31T09:00:00Z"
        }
    ]'::jsonb,
    -- opportunity_signals
    '[
        "수출대금 $310만 → 월평균 26% 성장, 수출금융 한도 확대 제안",
        "유산스 이용률 40% - 한도 여유, 수입 증가 시 확대 가능",
        "법인카드 출장비 35% - 항공마일리지 카드 크로스셀 기회"
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

-- 2. 동부건설 (8000-7647330) - 건설, 담보 인프라 수혜, 부채비율 상승
INSERT INTO rkyc_banking_data (corp_id, data_date, loan_exposure, deposit_trend, card_usage, collateral_detail, trade_finance, financial_statements, risk_alerts, opportunity_signals)
VALUES (
    '8000-7647330',
    '2026-01-31',
    -- loan_exposure (부채비율 높음)
    '{
        "as_of_date": "2026-01-31",
        "total_exposure_krw": 25000000000,
        "yearly_trend": [
            {"year": 2024, "secured": 12000, "unsecured": 3000, "fx": 500, "total": 15500},
            {"year": 2025, "secured": 16000, "unsecured": 4000, "fx": 800, "total": 20800},
            {"year": 2026, "secured": 19000, "unsecured": 5000, "fx": 1000, "total": 25000}
        ],
        "composition": {
            "secured_loan": {"amount": 19000000000, "ratio": 76.0},
            "unsecured_loan": {"amount": 5000000000, "ratio": 20.0},
            "fx_loan": {"amount": 1000000000, "ratio": 4.0}
        },
        "risk_indicators": {
            "overdue_flag": false,
            "overdue_days": 0,
            "overdue_amount": 0,
            "watch_list": false,
            "watch_list_reason": null,
            "internal_grade": "B1",
            "grade_change": "DOWN",
            "next_review_date": "2026-04-30"
        }
    }'::jsonb,
    -- deposit_trend
    '{
        "monthly_balance": [
            {"month": "2025-07", "balance": 1800000000},
            {"month": "2025-08", "balance": 1650000000},
            {"month": "2025-09", "balance": 1720000000},
            {"month": "2025-10", "balance": 1580000000},
            {"month": "2025-11", "balance": 1690000000},
            {"month": "2025-12", "balance": 1850000000},
            {"month": "2026-01", "balance": 1920000000}
        ],
        "current_balance": 1920000000,
        "avg_balance_6m": 1735000000,
        "min_balance_6m": 1580000000,
        "max_balance_6m": 1920000000,
        "trend": "STABLE",
        "volatility": "MEDIUM",
        "large_withdrawal_alerts": []
    }'::jsonb,
    -- card_usage
    '{
        "monthly_usage": [
            {"month": "2025-07", "amount": 82000000, "tx_count": 456},
            {"month": "2025-08", "amount": 95000000, "tx_count": 512},
            {"month": "2025-09", "amount": 88000000, "tx_count": 478},
            {"month": "2025-10", "amount": 102000000, "tx_count": 534},
            {"month": "2025-11", "amount": 98000000, "tx_count": 521},
            {"month": "2025-12", "amount": 115000000, "tx_count": 589},
            {"month": "2026-01", "amount": 92000000, "tx_count": 498}
        ],
        "category_breakdown": {
            "travel": 15.2,
            "entertainment": 12.8,
            "office_supplies": 8.5,
            "fuel": 42.3,
            "others": 21.2
        },
        "card_limit": 150000000,
        "utilization_rate": 61.3,
        "avg_monthly_usage": 96000000,
        "usage_trend": "STABLE",
        "anomaly_flags": []
    }'::jsonb,
    -- collateral_detail (인프라 개발 수혜)
    '{
        "collaterals": [
            {
                "id": "COL-DB-001",
                "type": "REAL_ESTATE",
                "description": "울산 남구 무거동 공장부지",
                "location": {
                    "address": "울산광역시 남구 무거동 123-45",
                    "coordinates": {"lat": 35.5384, "lng": 129.2569}
                },
                "appraisal": {
                    "value": 18500000000,
                    "date": "2024-06-15",
                    "appraiser": "한국감정원",
                    "next_appraisal_date": "2026-06-15",
                    "market_trend": "INCREASING"
                },
                "loan_amount": 11100000000,
                "ltv_ratio": 60.0,
                "nearby_development": {
                    "project_name": "문수로 우회도로",
                    "distance_km": 1.2,
                    "impact": "HIGH",
                    "description": "2.71km 왕복 4차로, 9,490세대 배후",
                    "expected_completion": "2028-12",
                    "status": "APPROVED"
                },
                "risk_factors": []
            },
            {
                "id": "COL-DB-002",
                "type": "REAL_ESTATE",
                "description": "강원 동해시 물류창고",
                "location": {
                    "address": "강원도 동해시 송정동 456-78",
                    "coordinates": {"lat": 37.5244, "lng": 129.1142}
                },
                "appraisal": {
                    "value": 8200000000,
                    "date": "2024-09-20",
                    "appraiser": "한국감정원",
                    "next_appraisal_date": "2026-09-20",
                    "market_trend": "INCREASING"
                },
                "loan_amount": 4920000000,
                "ltv_ratio": 60.0,
                "nearby_development": {
                    "project_name": "동해역~동해항 연결도로",
                    "distance_km": 0.8,
                    "impact": "MEDIUM",
                    "description": "437m 도로, KTX 연계 물류 활성화",
                    "expected_completion": "2025-11",
                    "status": "UNDER_CONSTRUCTION"
                },
                "risk_factors": []
            }
        ],
        "total_collateral_value": 26700000000,
        "total_loan_against": 16020000000,
        "avg_ltv": 60.0,
        "high_ltv_collaterals": [],
        "expiring_appraisals": [],
        "reappraisal_opportunities": [
            "COL-DB-001: 문수로 우회도로 착공 시 재감정 권고 (예상 +15%)",
            "COL-DB-002: 동해역~동해항 도로 개통 후 재감정 권고 (예상 +8%)"
        ]
    }'::jsonb,
    -- trade_finance (건설업 특성상 적음)
    '{
        "export": {
            "monthly_receivables": [],
            "current_receivables_usd": 0,
            "avg_collection_days": 0,
            "overdue_receivables_usd": 0,
            "major_countries": [],
            "country_concentration": {}
        },
        "import": {
            "monthly_payables": [
                {"month": "2025-07", "amount_usd": 120000},
                {"month": "2025-08", "amount_usd": 150000},
                {"month": "2025-09", "amount_usd": 135000},
                {"month": "2025-10", "amount_usd": 180000},
                {"month": "2025-11", "amount_usd": 165000},
                {"month": "2025-12", "amount_usd": 195000},
                {"month": "2026-01", "amount_usd": 175000}
            ],
            "current_payables_usd": 175000,
            "major_countries": ["CN", "DE"],
            "country_concentration": {"CN": 65, "DE": 35}
        },
        "usance": {
            "limit_usd": 500000,
            "utilized_usd": 175000,
            "utilization_rate": 35.0,
            "avg_tenor_days": 60,
            "upcoming_maturities": []
        },
        "fx_exposure": {
            "net_position_usd": -175000,
            "hedge_ratio": 80.0,
            "hedge_instruments": ["forward"],
            "var_1d_usd": 3500
        }
    }'::jsonb,
    -- financial_statements (부채비율 상승)
    '{
        "source": "DART",
        "last_updated": "2026-01-15",
        "years": {
            "2023": {
                "assets": 85000000000,
                "liabilities": 55000000000,
                "equity": 30000000000,
                "revenue": 120000000000,
                "operating_income": 7200000000,
                "net_income": 4500000000,
                "current_assets": 35000000000,
                "current_liabilities": 28000000000,
                "debt_ratio": 183.3,
                "current_ratio": 125.0,
                "interest_coverage": 3.8
            },
            "2024": {
                "assets": 95000000000,
                "liabilities": 65000000000,
                "equity": 30000000000,
                "revenue": 115000000000,
                "operating_income": 6100000000,
                "net_income": 3200000000,
                "current_assets": 38000000000,
                "current_liabilities": 32000000000,
                "debt_ratio": 216.7,
                "current_ratio": 118.8,
                "interest_coverage": 3.2
            },
            "2025": {
                "assets": 105000000000,
                "liabilities": 76000000000,
                "equity": 29000000000,
                "revenue": 108000000000,
                "operating_income": 5200000000,
                "net_income": 2100000000,
                "current_assets": 40000000000,
                "current_liabilities": 35000000000,
                "debt_ratio": 262.1,
                "current_ratio": 114.3,
                "interest_coverage": 2.6
            }
        },
        "yoy_growth": {
            "revenue": -6.1,
            "operating_income": -14.8,
            "net_income": -34.4
        },
        "financial_health": "CAUTION"
    }'::jsonb,
    -- risk_alerts
    '[
        {
            "id": "RISK-DB-001",
            "severity": "MED",
            "category": "FINANCIAL",
            "signal_type": "DIRECT",
            "title": "부채비율 급증",
            "description": "부채비율 183% → 262% (YoY +45%p). 재무구조 악화 추세.",
            "recommended_action": "자본확충 또는 부채 상환 계획 확인 필요",
            "detected_at": "2026-01-31T09:00:00Z"
        },
        {
            "id": "RISK-DB-002",
            "severity": "LOW",
            "category": "FINANCIAL",
            "signal_type": "DIRECT",
            "title": "수익성 하락",
            "description": "영업이익 YoY -14.8%, 순이익 YoY -34.4% 감소.",
            "recommended_action": "수주 현황 및 원가 관리 점검",
            "detected_at": "2026-01-31T09:00:00Z"
        },
        {
            "id": "RISK-DB-003",
            "severity": "LOW",
            "category": "LOAN",
            "signal_type": "DIRECT",
            "title": "내부등급 하향",
            "description": "내부등급 B1으로 하향 조정됨.",
            "recommended_action": "정기심사 시 면밀한 검토 필요",
            "detected_at": "2026-01-31T09:00:00Z"
        }
    ]'::jsonb,
    -- opportunity_signals
    '[
        "담보 COL-DB-001 인근 문수로 우회도로 개발 - 재감정 시 +15% 예상, 추가 여신 가능",
        "담보 COL-DB-002 동해역~동해항 도로 개통 임박 - 물류 활성화로 가치 상승 예상",
        "법인카드 주유비 42% - 건설장비 특성, 주유 할인 카드 제안"
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

-- 3. 삼성전자 (4301-3456789) - 대기업 우량, 시설투자 기회
INSERT INTO rkyc_banking_data (corp_id, data_date, loan_exposure, deposit_trend, card_usage, collateral_detail, trade_finance, financial_statements, risk_alerts, opportunity_signals)
VALUES (
    '4301-3456789',
    '2026-01-31',
    -- loan_exposure (대기업 우량)
    '{
        "as_of_date": "2026-01-31",
        "total_exposure_krw": 150000000000,
        "yearly_trend": [
            {"year": 2024, "secured": 50000, "unsecured": 60000, "fx": 20000, "total": 130000},
            {"year": 2025, "secured": 55000, "unsecured": 65000, "fx": 22000, "total": 142000},
            {"year": 2026, "secured": 60000, "unsecured": 70000, "fx": 20000, "total": 150000}
        ],
        "composition": {
            "secured_loan": {"amount": 60000000000, "ratio": 40.0},
            "unsecured_loan": {"amount": 70000000000, "ratio": 46.7},
            "fx_loan": {"amount": 20000000000, "ratio": 13.3}
        },
        "risk_indicators": {
            "overdue_flag": false,
            "overdue_days": 0,
            "overdue_amount": 0,
            "watch_list": false,
            "watch_list_reason": null,
            "internal_grade": "AAA",
            "grade_change": null,
            "next_review_date": "2026-12-31"
        }
    }'::jsonb,
    -- deposit_trend
    '{
        "monthly_balance": [
            {"month": "2025-07", "balance": 85000000000},
            {"month": "2025-08", "balance": 92000000000},
            {"month": "2025-09", "balance": 88000000000},
            {"month": "2025-10", "balance": 95000000000},
            {"month": "2025-11", "balance": 98000000000},
            {"month": "2025-12", "balance": 105000000000},
            {"month": "2026-01", "balance": 102000000000}
        ],
        "current_balance": 102000000000,
        "avg_balance_6m": 95000000000,
        "min_balance_6m": 85000000000,
        "max_balance_6m": 105000000000,
        "trend": "INCREASING",
        "volatility": "LOW",
        "large_withdrawal_alerts": []
    }'::jsonb,
    -- card_usage
    '{
        "monthly_usage": [
            {"month": "2025-07", "amount": 850000000, "tx_count": 4567},
            {"month": "2025-08", "amount": 920000000, "tx_count": 4892},
            {"month": "2025-09", "amount": 880000000, "tx_count": 4723},
            {"month": "2025-10", "amount": 950000000, "tx_count": 5012},
            {"month": "2025-11", "amount": 980000000, "tx_count": 5189},
            {"month": "2025-12", "amount": 1150000000, "tx_count": 5834},
            {"month": "2026-01", "amount": 920000000, "tx_count": 4912}
        ],
        "category_breakdown": {
            "travel": 42.5,
            "entertainment": 18.2,
            "office_supplies": 15.8,
            "fuel": 8.5,
            "others": 15.0
        },
        "card_limit": 2000000000,
        "utilization_rate": 46.0,
        "avg_monthly_usage": 950000000,
        "usage_trend": "STABLE",
        "anomaly_flags": []
    }'::jsonb,
    -- collateral_detail
    '{
        "collaterals": [
            {
                "id": "COL-SS-001",
                "type": "REAL_ESTATE",
                "description": "경기 화성시 반도체 생산라인",
                "location": {
                    "address": "경기도 화성시 삼성전자로 1",
                    "coordinates": {"lat": 37.2095, "lng": 127.0294}
                },
                "appraisal": {
                    "value": 250000000000,
                    "date": "2025-06-01",
                    "appraiser": "삼일회계법인",
                    "next_appraisal_date": "2027-06-01",
                    "market_trend": "STABLE"
                },
                "loan_amount": 60000000000,
                "ltv_ratio": 24.0,
                "nearby_development": null,
                "risk_factors": []
            }
        ],
        "total_collateral_value": 250000000000,
        "total_loan_against": 60000000000,
        "avg_ltv": 24.0,
        "high_ltv_collaterals": [],
        "expiring_appraisals": []
    }'::jsonb,
    -- trade_finance
    '{
        "export": {
            "monthly_receivables": [
                {"month": "2025-07", "amount_usd": 1200000000},
                {"month": "2025-08", "amount_usd": 1350000000},
                {"month": "2025-09", "amount_usd": 1280000000},
                {"month": "2025-10", "amount_usd": 1420000000},
                {"month": "2025-11", "amount_usd": 1380000000},
                {"month": "2025-12", "amount_usd": 1550000000},
                {"month": "2026-01", "amount_usd": 1480000000}
            ],
            "current_receivables_usd": 1480000000,
            "avg_collection_days": 38,
            "overdue_receivables_usd": 0,
            "major_countries": ["US", "CN", "EU", "JP", "IN"],
            "country_concentration": {"US": 28, "CN": 22, "EU": 20, "JP": 15, "IN": 15}
        },
        "import": {
            "monthly_payables": [
                {"month": "2025-07", "amount_usd": 650000000},
                {"month": "2025-08", "amount_usd": 720000000},
                {"month": "2025-09", "amount_usd": 680000000},
                {"month": "2025-10", "amount_usd": 780000000},
                {"month": "2025-11", "amount_usd": 750000000},
                {"month": "2025-12", "amount_usd": 850000000},
                {"month": "2026-01", "amount_usd": 800000000}
            ],
            "current_payables_usd": 800000000,
            "major_countries": ["JP", "US", "TW", "NL"],
            "country_concentration": {"JP": 35, "US": 25, "TW": 22, "NL": 18}
        },
        "usance": {
            "limit_usd": 2000000000,
            "utilized_usd": 800000000,
            "utilization_rate": 40.0,
            "avg_tenor_days": 60,
            "upcoming_maturities": []
        },
        "fx_exposure": {
            "net_position_usd": 680000000,
            "hedge_ratio": 85.0,
            "hedge_instruments": ["forward", "option", "swap"],
            "var_1d_usd": 8500000
        }
    }'::jsonb,
    -- financial_statements (대기업 우량)
    '{
        "source": "DART",
        "last_updated": "2026-01-15",
        "years": {
            "2023": {
                "assets": 455000000000000,
                "liabilities": 105000000000000,
                "equity": 350000000000000,
                "revenue": 259000000000000,
                "operating_income": 6600000000000,
                "net_income": 15500000000000,
                "current_assets": 185000000000000,
                "current_liabilities": 72000000000000,
                "debt_ratio": 30.0,
                "current_ratio": 256.9,
                "interest_coverage": 45.2
            },
            "2024": {
                "assets": 478000000000000,
                "liabilities": 108000000000000,
                "equity": 370000000000000,
                "revenue": 300000000000000,
                "operating_income": 32000000000000,
                "net_income": 28000000000000,
                "current_assets": 195000000000000,
                "current_liabilities": 75000000000000,
                "debt_ratio": 29.2,
                "current_ratio": 260.0,
                "interest_coverage": 52.8
            },
            "2025": {
                "assets": 502000000000000,
                "liabilities": 112000000000000,
                "equity": 390000000000000,
                "revenue": 320000000000000,
                "operating_income": 38000000000000,
                "net_income": 33000000000000,
                "current_assets": 210000000000000,
                "current_liabilities": 78000000000000,
                "debt_ratio": 28.7,
                "current_ratio": 269.2,
                "interest_coverage": 58.5
            }
        },
        "yoy_growth": {
            "revenue": 6.7,
            "operating_income": 18.8,
            "net_income": 17.9
        },
        "financial_health": "EXCELLENT"
    }'::jsonb,
    -- risk_alerts (리스크 없음)
    '[]'::jsonb,
    -- opportunity_signals
    '[
        "AAA 등급 우량 - 대규모 시설투자 자금 주선 기회",
        "법인카드 출장비 42% - 글로벌 마일리지 통합 서비스 제안",
        "LTV 24% - 추가 담보여력 활용 대규모 프로젝트 금융",
        "환헤지 비율 85% - 체계적 리스크 관리, 파생상품 자문 서비스"
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

-- 6. 휴림로봇 (6701-4567890) - 스타트업, 성장, 신용대출 비중 높음
INSERT INTO rkyc_banking_data (corp_id, data_date, loan_exposure, deposit_trend, card_usage, collateral_detail, trade_finance, financial_statements, risk_alerts, opportunity_signals)
VALUES (
    '6701-4567890',
    '2026-01-31',
    -- loan_exposure (신용대출 비중 높음)
    '{
        "as_of_date": "2026-01-31",
        "total_exposure_krw": 3500000000,
        "yearly_trend": [
            {"year": 2024, "secured": 500, "unsecured": 1200, "fx": 300, "total": 2000},
            {"year": 2025, "secured": 800, "unsecured": 1800, "fx": 400, "total": 3000},
            {"year": 2026, "secured": 1000, "unsecured": 2200, "fx": 300, "total": 3500}
        ],
        "composition": {
            "secured_loan": {"amount": 1000000000, "ratio": 28.6},
            "unsecured_loan": {"amount": 2200000000, "ratio": 62.9},
            "fx_loan": {"amount": 300000000, "ratio": 8.5}
        },
        "risk_indicators": {
            "overdue_flag": false,
            "overdue_days": 0,
            "overdue_amount": 0,
            "watch_list": false,
            "watch_list_reason": null,
            "internal_grade": "B2",
            "grade_change": "UP",
            "next_review_date": "2026-06-30"
        }
    }'::jsonb,
    -- deposit_trend
    '{
        "monthly_balance": [
            {"month": "2025-07", "balance": 280000000},
            {"month": "2025-08", "balance": 320000000},
            {"month": "2025-09", "balance": 295000000},
            {"month": "2025-10", "balance": 380000000},
            {"month": "2025-11", "balance": 420000000},
            {"month": "2025-12", "balance": 510000000},
            {"month": "2026-01", "balance": 480000000}
        ],
        "current_balance": 480000000,
        "avg_balance_6m": 384000000,
        "min_balance_6m": 280000000,
        "max_balance_6m": 510000000,
        "trend": "INCREASING",
        "volatility": "MEDIUM",
        "large_withdrawal_alerts": []
    }'::jsonb,
    -- card_usage
    '{
        "monthly_usage": [
            {"month": "2025-07", "amount": 12000000, "tx_count": 89},
            {"month": "2025-08", "amount": 15000000, "tx_count": 112},
            {"month": "2025-09", "amount": 14000000, "tx_count": 98},
            {"month": "2025-10", "amount": 18000000, "tx_count": 125},
            {"month": "2025-11", "amount": 21000000, "tx_count": 142},
            {"month": "2025-12", "amount": 28000000, "tx_count": 178},
            {"month": "2026-01", "amount": 22000000, "tx_count": 148}
        ],
        "category_breakdown": {
            "travel": 28.5,
            "entertainment": 12.2,
            "office_supplies": 32.5,
            "fuel": 8.8,
            "others": 18.0
        },
        "card_limit": 30000000,
        "utilization_rate": 73.3,
        "avg_monthly_usage": 18571000,
        "usage_trend": "INCREASING",
        "anomaly_flags": []
    }'::jsonb,
    -- collateral_detail
    '{
        "collaterals": [
            {
                "id": "COL-HR-001",
                "type": "REAL_ESTATE",
                "description": "대전 유성구 R&D 센터",
                "location": {
                    "address": "대전광역시 유성구 테크노로 123",
                    "coordinates": {"lat": 36.3742, "lng": 127.3631}
                },
                "appraisal": {
                    "value": 2500000000,
                    "date": "2025-03-15",
                    "appraiser": "한국감정원",
                    "next_appraisal_date": "2027-03-15",
                    "market_trend": "INCREASING"
                },
                "loan_amount": 1000000000,
                "ltv_ratio": 40.0,
                "nearby_development": null,
                "risk_factors": []
            }
        ],
        "total_collateral_value": 2500000000,
        "total_loan_against": 1000000000,
        "avg_ltv": 40.0,
        "high_ltv_collaterals": [],
        "expiring_appraisals": []
    }'::jsonb,
    -- trade_finance
    '{
        "export": {
            "monthly_receivables": [
                {"month": "2025-07", "amount_usd": 45000},
                {"month": "2025-08", "amount_usd": 58000},
                {"month": "2025-09", "amount_usd": 52000},
                {"month": "2025-10", "amount_usd": 72000},
                {"month": "2025-11", "amount_usd": 85000},
                {"month": "2025-12", "amount_usd": 98000},
                {"month": "2026-01", "amount_usd": 92000}
            ],
            "current_receivables_usd": 92000,
            "avg_collection_days": 52,
            "overdue_receivables_usd": 0,
            "major_countries": ["US", "DE", "JP"],
            "country_concentration": {"US": 45, "DE": 32, "JP": 23}
        },
        "import": {
            "monthly_payables": [
                {"month": "2025-07", "amount_usd": 32000},
                {"month": "2025-08", "amount_usd": 38000},
                {"month": "2025-09", "amount_usd": 35000},
                {"month": "2025-10", "amount_usd": 42000},
                {"month": "2025-11", "amount_usd": 48000},
                {"month": "2025-12", "amount_usd": 55000},
                {"month": "2026-01", "amount_usd": 52000}
            ],
            "current_payables_usd": 52000,
            "major_countries": ["CN", "JP", "US"],
            "country_concentration": {"CN": 40, "JP": 35, "US": 25}
        },
        "usance": {
            "limit_usd": 100000,
            "utilized_usd": 52000,
            "utilization_rate": 52.0,
            "avg_tenor_days": 60,
            "upcoming_maturities": []
        },
        "fx_exposure": {
            "net_position_usd": 40000,
            "hedge_ratio": 45.0,
            "hedge_instruments": ["forward"],
            "var_1d_usd": 1800
        }
    }'::jsonb,
    -- financial_statements (스타트업 성장)
    '{
        "source": "DART",
        "last_updated": "2026-01-15",
        "years": {
            "2023": {
                "assets": 5500000000,
                "liabilities": 3800000000,
                "equity": 1700000000,
                "revenue": 4200000000,
                "operating_income": -350000000,
                "net_income": -480000000,
                "current_assets": 2800000000,
                "current_liabilities": 2200000000,
                "debt_ratio": 223.5,
                "current_ratio": 127.3,
                "interest_coverage": -1.2
            },
            "2024": {
                "assets": 7200000000,
                "liabilities": 4500000000,
                "equity": 2700000000,
                "revenue": 6800000000,
                "operating_income": 180000000,
                "net_income": 85000000,
                "current_assets": 3800000000,
                "current_liabilities": 2600000000,
                "debt_ratio": 166.7,
                "current_ratio": 146.2,
                "interest_coverage": 1.5
            },
            "2025": {
                "assets": 9500000000,
                "liabilities": 5200000000,
                "equity": 4300000000,
                "revenue": 9800000000,
                "operating_income": 680000000,
                "net_income": 520000000,
                "current_assets": 5200000000,
                "current_liabilities": 2900000000,
                "debt_ratio": 120.9,
                "current_ratio": 179.3,
                "interest_coverage": 3.8
            }
        },
        "yoy_growth": {
            "revenue": 44.1,
            "operating_income": 277.8,
            "net_income": 511.8
        },
        "financial_health": "IMPROVING"
    }'::jsonb,
    -- risk_alerts (신용대출 비중)
    '[
        {
            "id": "RISK-HR-001",
            "severity": "LOW",
            "category": "LOAN",
            "signal_type": "DIRECT",
            "title": "신용대출 비중 과다",
            "description": "신용대출 비중 63%, 담보 없이 22억원 노출. 스타트업 특성상 모니터링 필요.",
            "recommended_action": "성장에 따른 담보 확충 유도, 기술보증 활용 검토",
            "detected_at": "2026-01-31T09:00:00Z"
        }
    ]'::jsonb,
    -- opportunity_signals
    '[
        "매출 YoY 44% 성장 - 고성장 스타트업, 시리즈B 투자 유치 시 추가 여신 기회",
        "흑자 전환 성공 - 내부등급 상향(B2→B1 예상), 금리 인하 협상 가능",
        "법인카드 이용 증가 - 카드 한도 증액 제안 (현 73% 소진)",
        "수출 급증 (YoY 104%) - 수출금융/무역보험 패키지 제안",
        "R&D 센터 담보 LTV 40% - 기술보증 추가 시 신용대출 전환 가능"
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
DO $$
DECLARE
    cnt INTEGER;
BEGIN
    SELECT COUNT(*) INTO cnt FROM rkyc_banking_data;
    RAISE NOTICE 'Seed 완료: rkyc_banking_data에 % 건 삽입됨', cnt;
END $$;
