#!/usr/bin/env python
"""
Insert Banking Data for Missing Corporations
"""

import sys
import os
import json
import asyncio
import ssl
from datetime import date

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# 5개 누락 기업의 Banking Data
MISSING_CORPS_DATA = [
    {
        'corp_id': '9001-0000001',
        'corp_name': '주식회사 크라우드웍스',
        'industry': 'J62',
        'scenario': 'AI 데이터 라벨링 스타트업, 성장세 뚜렷하나 현금흐름 불안정',
        'loan_exposure': {
            'as_of_date': '2026-01-31',
            'total_exposure_krw': 3000000000,
            'yearly_trend': [
                {'year': 2024, 'secured': 500, 'unsecured': 1000, 'fx': 0, 'total': 1500},
                {'year': 2025, 'secured': 800, 'unsecured': 1500, 'fx': 200, 'total': 2500},
                {'year': 2026, 'secured': 1000, 'unsecured': 1800, 'fx': 200, 'total': 3000}
            ],
            'composition': {
                'secured_loan': {'amount': 1000000000, 'ratio': 33.3},
                'unsecured_loan': {'amount': 1800000000, 'ratio': 60.0},
                'fx_loan': {'amount': 200000000, 'ratio': 6.7}
            },
            'risk_indicators': {
                'overdue_flag': False, 'overdue_days': 0, 'overdue_amount': 0,
                'watch_list': False, 'internal_grade': 'B1',
                'next_review_date': '2026-07-31'
            }
        },
        'deposit_trend': {
            'monthly_balance': [
                {'month': '2025-08', 'balance': 450000000},
                {'month': '2025-09', 'balance': 380000000},
                {'month': '2025-10', 'balance': 520000000},
                {'month': '2025-11', 'balance': 410000000},
                {'month': '2025-12', 'balance': 680000000},
                {'month': '2026-01', 'balance': 550000000}
            ],
            'current_balance': 550000000,
            'avg_balance_6m': 498000000,
            'trend': 'VOLATILE',
            'volatility': 'HIGH'
        },
        'card_usage': {
            'monthly_usage': [
                {'month': '2025-12', 'amount': 25000000, 'tx_count': 180},
                {'month': '2026-01', 'amount': 28000000, 'tx_count': 195}
            ],
            'category_breakdown': {'cloud_services': 45.0, 'office': 25.0, 'travel': 20.0, 'others': 10.0},
            'card_limit': 50000000,
            'utilization_rate': 56.0,
            'usage_trend': 'INCREASING'
        },
        'collateral_detail': {
            'collaterals': [
                {'id': 'COL-CW-001', 'type': 'DEPOSIT', 'description': '정기예금 담보', 'value': 500000000, 'ltv': 80.0}
            ],
            'total_value': 500000000,
            'avg_ltv': 80.0,
            'coverage_ratio': 50.0
        },
        'trade_finance': {
            'export': {'current_receivables_usd': 150000, 'monthly_avg_usd': 120000},
            'import': {'current_payables_usd': 80000},
            'fx_exposure': {'net_position_usd': 70000, 'hedge_ratio': 0}
        },
        'financial_statements': {
            'latest_year': 2025,
            'revenue_krw': 8500000000,
            'operating_profit_krw': 850000000,
            'net_profit_krw': 620000000,
            'debt_ratio': 180.5,
            'current_ratio': 95.2
        },
        'risk_alerts': [
            {'id': 'RA-CW-001', 'severity': 'MED', 'category': 'LIQUIDITY', 'title': '예금 변동성 높음', 'description': '월별 예금잔액 변동폭 40% 이상'},
            {'id': 'RA-CW-002', 'severity': 'LOW', 'category': 'CREDIT', 'title': '무담보 대출 비중 높음', 'description': '무담보 대출 60%로 담보 커버리지 부족'}
        ],
        'opportunity_signals': [
            'AI 데이터 시장 성장으로 매출 증가 추세 (YoY +45%)',
            '대기업 협력사 지정으로 안정적 매출처 확보 기대'
        ]
    },
    {
        'corp_id': '9001-0000002',
        'corp_name': '(주)이엘피',
        'industry': 'C26',
        'scenario': '반도체 장비 제조, 수출 의존도 높음',
        'loan_exposure': {
            'as_of_date': '2026-01-31',
            'total_exposure_krw': 8500000000,
            'yearly_trend': [
                {'year': 2024, 'secured': 4000, 'unsecured': 1500, 'fx': 1000, 'total': 6500},
                {'year': 2025, 'secured': 5000, 'unsecured': 2000, 'fx': 1200, 'total': 8200},
                {'year': 2026, 'secured': 5500, 'unsecured': 2000, 'fx': 1000, 'total': 8500}
            ],
            'composition': {
                'secured_loan': {'amount': 5500000000, 'ratio': 64.7},
                'unsecured_loan': {'amount': 2000000000, 'ratio': 23.5},
                'fx_loan': {'amount': 1000000000, 'ratio': 11.8}
            },
            'risk_indicators': {
                'overdue_flag': False, 'overdue_days': 0, 'overdue_amount': 0,
                'watch_list': False, 'internal_grade': 'A3',
                'next_review_date': '2026-06-30'
            }
        },
        'deposit_trend': {
            'monthly_balance': [
                {'month': '2025-08', 'balance': 1200000000},
                {'month': '2025-09', 'balance': 1350000000},
                {'month': '2025-10', 'balance': 1280000000},
                {'month': '2025-11', 'balance': 1450000000},
                {'month': '2025-12', 'balance': 1520000000},
                {'month': '2026-01', 'balance': 1680000000}
            ],
            'current_balance': 1680000000,
            'avg_balance_6m': 1413000000,
            'trend': 'INCREASING',
            'volatility': 'LOW'
        },
        'card_usage': {
            'monthly_usage': [
                {'month': '2025-12', 'amount': 42000000, 'tx_count': 210},
                {'month': '2026-01', 'amount': 38000000, 'tx_count': 195}
            ],
            'category_breakdown': {'equipment': 40.0, 'travel': 25.0, 'office': 20.0, 'others': 15.0},
            'card_limit': 80000000,
            'utilization_rate': 47.5,
            'usage_trend': 'STABLE'
        },
        'collateral_detail': {
            'collaterals': [
                {'id': 'COL-ELP-001', 'type': 'REAL_ESTATE', 'description': '경기도 평택 반도체 장비 공장', 'value': 12000000000, 'ltv': 45.8},
                {'id': 'COL-ELP-002', 'type': 'MACHINERY', 'description': '반도체 장비 제조설비', 'value': 3000000000, 'ltv': 66.7}
            ],
            'total_value': 15000000000,
            'avg_ltv': 51.2,
            'coverage_ratio': 176.5
        },
        'trade_finance': {
            'export': {'current_receivables_usd': 2800000, 'monthly_avg_usd': 2200000},
            'import': {'current_payables_usd': 1500000},
            'fx_exposure': {'net_position_usd': 1300000, 'hedge_ratio': 42}
        },
        'financial_statements': {
            'latest_year': 2025,
            'revenue_krw': 45000000000,
            'operating_profit_krw': 5400000000,
            'net_profit_krw': 4100000000,
            'debt_ratio': 120.5,
            'current_ratio': 145.2
        },
        'risk_alerts': [
            {'id': 'RA-ELP-001', 'severity': 'MED', 'category': 'TRADE', 'title': '환헤지율 부족', 'description': '환헤지율 42%로 권고치 50% 미달'}
        ],
        'opportunity_signals': [
            '반도체 장비 수출 호조로 매출 성장 기대',
            '평택 공장 증설로 시설자금 대출 수요 예상'
        ]
    },
    {
        'corp_id': '9001-0000003',
        'corp_name': '주식회사 터',
        'industry': 'R90',
        'scenario': '문화콘텐츠 기업, 계절성 매출 변동 큼',
        'loan_exposure': {
            'as_of_date': '2026-01-31',
            'total_exposure_krw': 1500000000,
            'yearly_trend': [
                {'year': 2024, 'secured': 500, 'unsecured': 800, 'fx': 0, 'total': 1300},
                {'year': 2025, 'secured': 600, 'unsecured': 900, 'fx': 0, 'total': 1500},
                {'year': 2026, 'secured': 600, 'unsecured': 900, 'fx': 0, 'total': 1500}
            ],
            'composition': {
                'secured_loan': {'amount': 600000000, 'ratio': 40.0},
                'unsecured_loan': {'amount': 900000000, 'ratio': 60.0},
                'fx_loan': {'amount': 0, 'ratio': 0}
            },
            'risk_indicators': {
                'overdue_flag': False, 'overdue_days': 0, 'overdue_amount': 0,
                'watch_list': False, 'internal_grade': 'B2',
                'next_review_date': '2026-08-31'
            }
        },
        'deposit_trend': {
            'monthly_balance': [
                {'month': '2025-08', 'balance': 180000000},
                {'month': '2025-09', 'balance': 220000000},
                {'month': '2025-10', 'balance': 350000000},
                {'month': '2025-11', 'balance': 280000000},
                {'month': '2025-12', 'balance': 420000000},
                {'month': '2026-01', 'balance': 250000000}
            ],
            'current_balance': 250000000,
            'avg_balance_6m': 283000000,
            'trend': 'VOLATILE',
            'volatility': 'HIGH'
        },
        'card_usage': {
            'monthly_usage': [
                {'month': '2025-12', 'amount': 18000000, 'tx_count': 145},
                {'month': '2026-01', 'amount': 12000000, 'tx_count': 98}
            ],
            'category_breakdown': {'production': 35.0, 'marketing': 30.0, 'travel': 20.0, 'others': 15.0},
            'card_limit': 30000000,
            'utilization_rate': 40.0,
            'usage_trend': 'DECREASING'
        },
        'collateral_detail': {
            'collaterals': [
                {'id': 'COL-TER-001', 'type': 'IP_RIGHTS', 'description': 'IP 저작권 담보', 'value': 800000000, 'ltv': 75.0}
            ],
            'total_value': 800000000,
            'avg_ltv': 75.0,
            'coverage_ratio': 53.3
        },
        'trade_finance': None,
        'financial_statements': {
            'latest_year': 2025,
            'revenue_krw': 4200000000,
            'operating_profit_krw': 320000000,
            'net_profit_krw': 180000000,
            'debt_ratio': 210.5,
            'current_ratio': 85.2
        },
        'risk_alerts': [
            {'id': 'RA-TER-001', 'severity': 'MED', 'category': 'LIQUIDITY', 'title': '계절성 현금흐름', 'description': '분기별 매출 변동폭 50% 이상'},
            {'id': 'RA-TER-002', 'severity': 'LOW', 'category': 'CREDIT', 'title': '유동비율 미달', 'description': '유동비율 85.2%로 100% 미달'}
        ],
        'opportunity_signals': [
            'K-콘텐츠 해외 수출 확대 기회',
            '정부 문화산업 지원 정책 수혜 가능'
        ]
    },
    {
        'corp_id': '9001-0000004',
        'corp_name': '대한주식회사',
        'industry': 'C27',
        'scenario': '의료기기 제조, 수출 성장세',
        'loan_exposure': {
            'as_of_date': '2026-01-31',
            'total_exposure_krw': 6000000000,
            'yearly_trend': [
                {'year': 2024, 'secured': 3000, 'unsecured': 1500, 'fx': 500, 'total': 5000},
                {'year': 2025, 'secured': 3500, 'unsecured': 1800, 'fx': 700, 'total': 6000},
                {'year': 2026, 'secured': 3500, 'unsecured': 1800, 'fx': 700, 'total': 6000}
            ],
            'composition': {
                'secured_loan': {'amount': 3500000000, 'ratio': 58.3},
                'unsecured_loan': {'amount': 1800000000, 'ratio': 30.0},
                'fx_loan': {'amount': 700000000, 'ratio': 11.7}
            },
            'risk_indicators': {
                'overdue_flag': False, 'overdue_days': 0, 'overdue_amount': 0,
                'watch_list': False, 'internal_grade': 'A2',
                'next_review_date': '2026-06-30'
            }
        },
        'deposit_trend': {
            'monthly_balance': [
                {'month': '2025-08', 'balance': 950000000},
                {'month': '2025-09', 'balance': 1020000000},
                {'month': '2025-10', 'balance': 1080000000},
                {'month': '2025-11', 'balance': 1150000000},
                {'month': '2025-12', 'balance': 1220000000},
                {'month': '2026-01', 'balance': 1350000000}
            ],
            'current_balance': 1350000000,
            'avg_balance_6m': 1128000000,
            'trend': 'INCREASING',
            'volatility': 'LOW'
        },
        'card_usage': {
            'monthly_usage': [
                {'month': '2025-12', 'amount': 35000000, 'tx_count': 178},
                {'month': '2026-01', 'amount': 32000000, 'tx_count': 165}
            ],
            'category_breakdown': {'equipment': 35.0, 'travel': 30.0, 'office': 20.0, 'others': 15.0},
            'card_limit': 60000000,
            'utilization_rate': 53.3,
            'usage_trend': 'STABLE'
        },
        'collateral_detail': {
            'collaterals': [
                {'id': 'COL-DH-001', 'type': 'REAL_ESTATE', 'description': '인천 남동공단 의료기기 공장', 'value': 8000000000, 'ltv': 43.8},
                {'id': 'COL-DH-002', 'type': 'MACHINERY', 'description': '정밀 의료기기 제조설비', 'value': 2000000000, 'ltv': 70.0}
            ],
            'total_value': 10000000000,
            'avg_ltv': 50.0,
            'coverage_ratio': 166.7
        },
        'trade_finance': {
            'export': {'current_receivables_usd': 1800000, 'monthly_avg_usd': 1500000},
            'import': {'current_payables_usd': 900000},
            'fx_exposure': {'net_position_usd': 900000, 'hedge_ratio': 55}
        },
        'financial_statements': {
            'latest_year': 2025,
            'revenue_krw': 32000000000,
            'operating_profit_krw': 4200000000,
            'net_profit_krw': 3100000000,
            'debt_ratio': 95.5,
            'current_ratio': 165.2
        },
        'risk_alerts': [],
        'opportunity_signals': [
            '의료기기 수출 확대로 무역금융 수요 증가 예상',
            '정부 바이오헬스 산업 지원 정책 수혜 기대',
            'FDA 인증 획득으로 미국 시장 진출 가속화'
        ]
    },
    {
        'corp_id': '9001-0000005',
        'corp_name': '이오 주식회사',
        'industry': 'J62',
        'scenario': 'B2B SaaS 기업, 구독 수익 모델',
        'loan_exposure': {
            'as_of_date': '2026-01-31',
            'total_exposure_krw': 2000000000,
            'yearly_trend': [
                {'year': 2024, 'secured': 500, 'unsecured': 800, 'fx': 0, 'total': 1300},
                {'year': 2025, 'secured': 700, 'unsecured': 1100, 'fx': 0, 'total': 1800},
                {'year': 2026, 'secured': 800, 'unsecured': 1200, 'fx': 0, 'total': 2000}
            ],
            'composition': {
                'secured_loan': {'amount': 800000000, 'ratio': 40.0},
                'unsecured_loan': {'amount': 1200000000, 'ratio': 60.0},
                'fx_loan': {'amount': 0, 'ratio': 0}
            },
            'risk_indicators': {
                'overdue_flag': False, 'overdue_days': 0, 'overdue_amount': 0,
                'watch_list': False, 'internal_grade': 'B1',
                'next_review_date': '2026-07-31'
            }
        },
        'deposit_trend': {
            'monthly_balance': [
                {'month': '2025-08', 'balance': 320000000},
                {'month': '2025-09', 'balance': 340000000},
                {'month': '2025-10', 'balance': 360000000},
                {'month': '2025-11', 'balance': 380000000},
                {'month': '2025-12', 'balance': 420000000},
                {'month': '2026-01', 'balance': 450000000}
            ],
            'current_balance': 450000000,
            'avg_balance_6m': 378000000,
            'trend': 'INCREASING',
            'volatility': 'LOW'
        },
        'card_usage': {
            'monthly_usage': [
                {'month': '2025-12', 'amount': 15000000, 'tx_count': 120},
                {'month': '2026-01', 'amount': 16500000, 'tx_count': 132}
            ],
            'category_breakdown': {'cloud_services': 50.0, 'office': 25.0, 'travel': 15.0, 'others': 10.0},
            'card_limit': 30000000,
            'utilization_rate': 55.0,
            'usage_trend': 'INCREASING'
        },
        'collateral_detail': {
            'collaterals': [
                {'id': 'COL-EO-001', 'type': 'DEPOSIT', 'description': '정기예금 담보', 'value': 400000000, 'ltv': 80.0}
            ],
            'total_value': 400000000,
            'avg_ltv': 80.0,
            'coverage_ratio': 50.0
        },
        'trade_finance': None,
        'financial_statements': {
            'latest_year': 2025,
            'revenue_krw': 5800000000,
            'operating_profit_krw': 580000000,
            'net_profit_krw': 420000000,
            'debt_ratio': 145.5,
            'current_ratio': 125.2
        },
        'risk_alerts': [
            {'id': 'RA-EO-001', 'severity': 'LOW', 'category': 'CREDIT', 'title': '무담보 비중 높음', 'description': '무담보 대출 60%로 담보 커버리지 부족'}
        ],
        'opportunity_signals': [
            'SaaS 구독 수익 안정적 성장 (MRR +15% YoY)',
            '대기업 고객사 확대로 매출 성장 기대',
            '클라우드 전환 트렌드로 시장 확대 중'
        ]
    }
]


async def insert_banking_data():
    import asyncpg

    db_url = os.getenv('DATABASE_URL', '')
    if '?' in db_url:
        db_url = db_url.split('?')[0]

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(db_url, ssl=ssl_context, statement_cache_size=0)

    print('=' * 70)
    print('Banking Data 생성 시작')
    print('=' * 70)

    for corp in MISSING_CORPS_DATA:
        try:
            await conn.execute('''
                INSERT INTO rkyc_banking_data (
                    corp_id, data_date, loan_exposure, deposit_trend,
                    card_usage, collateral_detail, trade_finance,
                    financial_statements, risk_alerts, opportunity_signals
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ''',
                corp['corp_id'],
                date(2026, 1, 31),
                json.dumps(corp['loan_exposure']),
                json.dumps(corp['deposit_trend']),
                json.dumps(corp['card_usage']),
                json.dumps(corp['collateral_detail']),
                json.dumps(corp['trade_finance']) if corp['trade_finance'] else None,
                json.dumps(corp['financial_statements']),
                json.dumps(corp['risk_alerts']),
                json.dumps(corp['opportunity_signals'])
            )
            exposure = corp['loan_exposure']['total_exposure_krw'] / 100000000
            print(f"  [OK] {corp['corp_name']} ({corp['corp_id']})")
            print(f"       시나리오: {corp['scenario']}")
            print(f"       여신: {exposure:.0f}억원")
        except Exception as e:
            print(f"  [ERR] {corp['corp_name']}: {e}")

    # 확인
    count = await conn.fetchval('SELECT COUNT(*) FROM rkyc_banking_data')
    print()
    print(f'총 Banking Data 레코드: {count}개')

    await conn.close()


if __name__ == '__main__':
    asyncio.run(insert_banking_data())
