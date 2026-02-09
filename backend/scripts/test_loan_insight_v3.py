#!/usr/bin/env python
"""
Test Loan Insight v3.0 - Banking Data 통합 테스트

Usage:
    python scripts/test_loan_insight_v3.py --corp-id 6701-4567890
"""

import asyncio
import argparse
import logging
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Mock Banking Data (휴림로봇 예시)
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
                "hedge_ratio": 28,  # 권고치 50% 미달
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
    "8001-3719240": {  # 엠케이전자
        "data_date": "2026-02-09",
        "loan_exposure": {
            "total_exposure_krw": 120_0000_0000,  # 1200억
            "by_type": {
                "working_capital": 50_0000_0000,
                "facility": 60_0000_0000,
                "trade_finance": 10_0000_0000,
            },
            "risk_indicators": {
                "internal_grade": "MED",
                "overdue_flag": False,
            },
        },
        "collateral_detail": {
            "total_collateral_value": 150_0000_0000,
            "avg_ltv": 65.5,
            "collaterals": [
                {"type": "부동산", "value": 100_0000_0000, "ltv_ratio": 60, "description": "울산 공장 부지 및 건물"},
                {"type": "기계장비", "value": 50_0000_0000, "ltv_ratio": 75, "description": "반도체 생산 설비"},
            ],
        },
        "deposit_trend": {
            "current_balance": 45_0000_0000,
            "trend": "INCREASING",
            "avg_balance_3m": 42_0000_0000,
        },
        "trade_finance": {
            "export": {
                "current_receivables_usd": 12_500_000,
            },
            "import": {
                "current_payables_usd": 8_000_000,
            },
            "fx_exposure": {
                "net_position_usd": 4_500_000,
                "hedge_ratio": 35,
            },
        },
        "risk_alerts": [
            {"id": "RA003", "severity": "MED", "title": "환헤지율 주의", "description": "환헤지율 35%로 권고치 50% 미달", "category": "TRADE"},
        ],
        "opportunity_signals": [
            "반도체 업황 회복으로 매출 증가 예상",
            "담보물 인근 인프라 개발로 감정가 상승 기대",
        ],
    },
}


async def get_db_connection():
    """DB 연결 생성"""
    import asyncpg
    import ssl

    db_url = os.getenv('DATABASE_URL', '')
    if '?' in db_url:
        db_url = db_url.split('?')[0]

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    return await asyncpg.connect(
        db_url,
        ssl=ssl_context,
        statement_cache_size=0
    )


async def get_signals(conn, corp_id: str) -> list:
    """기업의 시그널 조회"""
    rows = await conn.fetch("""
        SELECT signal_id, signal_type, event_type, impact_direction, impact_strength,
               confidence, summary, title
        FROM rkyc_signal_index
        WHERE corp_id = $1
        ORDER BY detected_at DESC
        LIMIT 10
    """, corp_id)

    return [dict(row) for row in rows]


async def get_profile(conn, corp_id: str) -> dict:
    """기업 프로필 조회"""
    row = await conn.fetchrow("""
        SELECT business_summary, business_model, industry_overview,
               revenue_krw, export_ratio_pct, country_exposure,
               key_customers, key_materials, competitors
        FROM rkyc_corp_profile
        WHERE corp_id = $1
    """, corp_id)

    if row:
        return dict(row)
    return {}


async def test_banking_data_formatting(corp_id: str):
    """Banking Data 포맷팅 테스트"""
    from app.worker.pipelines.insight import InsightPipeline

    pipeline = InsightPipeline()

    # Mock Banking Data 사용
    banking_data = MOCK_BANKING_DATA.get(corp_id, {})

    if not banking_data:
        print(f"[WARN] No mock banking data for {corp_id}")
        banking_data = MOCK_BANKING_DATA.get("6701-4567890")  # 기본값

    # 포맷팅 테스트
    formatted = pipeline._format_banking_data_for_loan_insight(banking_data, "테스트기업")

    print("\n" + "="*60)
    print("Banking Data 포맷팅 결과 (LLM에 전달될 내용)")
    print("="*60)
    print(formatted)
    print("="*60 + "\n")

    return formatted


async def test_full_loan_insight(corp_id: str, corp_name: str):
    """전체 Loan Insight 생성 테스트 (LLM 호출 포함)"""
    from app.worker.pipelines.insight import InsightPipeline

    conn = await get_db_connection()

    try:
        # 데이터 조회
        signals = await get_signals(conn, corp_id)
        profile = await get_profile(conn, corp_id)
        banking_data = MOCK_BANKING_DATA.get(corp_id, {})

        print(f"\n=== Loan Insight 생성 테스트: {corp_name} ===")
        print(f"시그널 수: {len(signals)}")
        print(f"프로필 존재: {'예' if profile else '아니오'}")
        print(f"Banking Data 존재: {'예' if banking_data else '아니오'}")

        if not signals:
            print("[WARN] 시그널이 없습니다. 먼저 분석을 실행하세요.")
            return

        # 시그널 목록 출력
        print("\n[감지된 시그널]")
        for s in signals[:5]:
            print(f"  - [{s['signal_type']}][{s['impact_direction']}] {s.get('title', s['summary'][:50])}")

        # InsightPipeline 실행
        pipeline = InsightPipeline()

        # Context 구성
        context = {
            "corp_id": corp_id,
            "corp_name": corp_name,
            "industry_name": "로봇/자동화",
            "profile": profile,
            "banking_data": banking_data,
        }

        # Loan Insight 생성 및 저장
        print("\n[LLM 호출 중...]")
        pipeline._generate_and_save_loan_insight(
            corp_id=corp_id,
            corp_name=corp_name,
            industry_name="로봇/자동화",
            signals=signals,
            profile=profile,
            banking_data=banking_data,
        )

        # 결과 확인
        print("\n[Loan Insight 저장 완료]")

        # DB에서 결과 조회
        result = await conn.fetchrow("""
            SELECT stance_level, stance_label, executive_summary, narrative,
                   key_risks, key_opportunities, mitigating_factors, action_items,
                   is_fallback, generation_model
            FROM rkyc_loan_insight
            WHERE corp_id = $1
        """, corp_id)

        if result:
            print("\n" + "="*60)
            print("생성된 Loan Insight")
            print("="*60)
            print(f"Stance: {result['stance_level']} ({result['stance_label']})")
            print(f"Model: {result['generation_model']}")
            print(f"Fallback: {result['is_fallback']}")
            print(f"\n[Executive Summary]\n{result['executive_summary']}")
            print(f"\n[Narrative]\n{result['narrative']}")

            risks = json.loads(result['key_risks']) if result['key_risks'] else []
            print(f"\n[핵심 리스크 요인] ({len(risks)}건)")
            for r in risks:
                print(f"  • {r}")

            opps = json.loads(result['key_opportunities']) if result['key_opportunities'] else []
            print(f"\n[핵심 기회 요인] ({len(opps)}건)")
            for o in opps:
                print(f"  • {o}")

            actions = json.loads(result['action_items']) if result['action_items'] else []
            print(f"\n[Action Items] ({len(actions)}건)")
            for a in actions:
                print(f"  • {a}")

            print("="*60)

    finally:
        await conn.close()


async def main():
    parser = argparse.ArgumentParser(description='Test Loan Insight v3.0')
    parser.add_argument('--corp-id', default='6701-4567890', help='Corp ID to test')
    parser.add_argument('--format-only', action='store_true', help='Only test formatting')
    args = parser.parse_args()

    corp_names = {
        "6701-4567890": "휴림로봇",
        "8001-3719240": "엠케이전자",
        "8000-7647330": "동부건설",
        "4301-3456789": "삼성전자",
    }

    corp_name = corp_names.get(args.corp_id, "테스트기업")

    # 1. Banking Data 포맷팅 테스트
    await test_banking_data_formatting(args.corp_id)

    # 2. 전체 Loan Insight 테스트 (옵션)
    if not args.format_only:
        await test_full_loan_insight(args.corp_id, corp_name)


if __name__ == '__main__':
    asyncio.run(main())
