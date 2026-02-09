"""
Fetch Financial Statements for ALL Corporations in Corp Table

corp 테이블의 모든 기업에 대해 DART API를 통해
최근 3년 재무제표를 가져와서 출력합니다.

Usage:
    python scripts/fetch_all_corp_financials.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import DART API functions
from app.services.dart_api import get_financial_statements_by_name, FinancialStatement


async def get_all_corporations(conn) -> list[dict]:
    """Get all corporations from corp table"""
    rows = await conn.fetch("""
        SELECT corp_id, corp_name, industry_code, ceo_name
        FROM corp
        ORDER BY corp_name
    """)
    return [dict(row) for row in rows]


async def fetch_financials_for_corp(corp_name: str) -> list[FinancialStatement]:
    """Fetch financial statements for a single corporation"""
    try:
        statements = await get_financial_statements_by_name(corp_name)
        return statements
    except Exception as e:
        print(f"  ❌ Error fetching for {corp_name}: {e}")
        return []


def format_currency(amount: int | None) -> str:
    """Format currency in Korean style (억원)"""
    if amount is None:
        return "-"
    # Convert to 억원 (100 million won)
    eok = amount / 100_000_000
    if abs(eok) >= 1:
        return f"{eok:,.1f}억원"
    # If less than 1억, show in 만원
    man = amount / 10_000
    return f"{man:,.0f}만원"


def print_financial_statement(stmt: FinancialStatement):
    """Print a single financial statement"""
    print(f"    📅 {stmt.bsns_year}년:")
    print(f"       매출액: {format_currency(stmt.revenue)}")
    print(f"       영업이익: {format_currency(stmt.operating_profit)}")
    print(f"       당기순이익: {format_currency(stmt.net_income)}")
    print(f"       자산총계: {format_currency(stmt.total_assets)}")
    print(f"       부채총계: {format_currency(stmt.total_liabilities)}")
    print(f"       자본총계: {format_currency(stmt.total_equity)}")
    print(f"       이익잉여금: {format_currency(stmt.retained_earnings)}")
    if stmt.debt_ratio:
        print(f"       부채비율: {stmt.debt_ratio}%")
    print()


async def main():
    print("=" * 70)
    print("DART API - 전체 기업 재무제표 조회")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # Database connection
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        return

    # Parse and fix URL for asyncpg
    if "sslmode=" in database_url:
        database_url = database_url.split("?")[0]

    print("🔗 Connecting to database...")

    try:
        conn = await asyncpg.connect(
            database_url,
            ssl="require",
            statement_cache_size=0
        )
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    try:
        # Get all corporations
        corporations = await get_all_corporations(conn)
        print(f"✅ Found {len(corporations)} corporations in database")
        print()

        # Summary statistics
        total_corps = len(corporations)
        success_count = 0
        fail_count = 0
        all_financials = {}

        for i, corp in enumerate(corporations, 1):
            corp_name = corp["corp_name"]
            corp_id = corp["corp_id"]
            industry = corp.get("industry_code", "N/A")

            print(f"[{i}/{total_corps}] 🏢 {corp_name} ({corp_id})")
            print(f"    업종코드: {industry}")

            statements = await fetch_financials_for_corp(corp_name)

            if statements:
                success_count += 1
                all_financials[corp_name] = statements
                print(f"    ✅ {len(statements)}년치 재무제표 조회 성공")
                for stmt in statements:
                    print_financial_statement(stmt)
            else:
                fail_count += 1
                print(f"    ⚠️ 재무제표를 찾을 수 없음 (비상장 또는 DART 미등록)")
                print()

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        # Print summary
        print("=" * 70)
        print("📊 조회 결과 요약")
        print("=" * 70)
        print(f"  전체 기업 수: {total_corps}")
        print(f"  조회 성공: {success_count}")
        print(f"  조회 실패/미등록: {fail_count}")
        print()

        # Print consolidated table
        if all_financials:
            print("=" * 70)
            print("📈 전체 재무 현황 요약 (최신 연도 기준)")
            print("=" * 70)
            print(f"{'기업명':<20} {'연도':<6} {'매출액':<15} {'영업이익':<15} {'순이익':<15}")
            print("-" * 70)

            for corp_name, statements in all_financials.items():
                if statements:
                    latest = statements[0]  # Most recent year
                    print(f"{corp_name:<20} {latest.bsns_year:<6} "
                          f"{format_currency(latest.revenue):<15} "
                          f"{format_currency(latest.operating_profit):<15} "
                          f"{format_currency(latest.net_income):<15}")

    finally:
        await conn.close()
        print()
        print("✅ Database connection closed")


if __name__ == "__main__":
    asyncio.run(main())
