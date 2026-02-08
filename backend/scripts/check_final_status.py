"""최종 상태 확인"""
import asyncio
import sys
import os
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine


async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT c.corp_id, c.corp_name, c.industry_code, c.ceo_name,
                   c.dart_corp_code, l.snapshot_version,
                   s.snapshot_json
            FROM corp c
            LEFT JOIN rkyc_internal_snapshot_latest l ON c.corp_id = l.corp_id
            LEFT JOIN rkyc_internal_snapshot s ON l.snapshot_id = s.snapshot_id
            ORDER BY c.corp_name
        """))

        print("=" * 80)
        print("해커톤 시연 기업 목록 (9개)")
        print("=" * 80)

        for row in result:
            dart = "O" if row[4] else "X"
            snap = f"v{row[5]}" if row[5] else "X"
            print(f"[DART:{dart}][SNAP:{snap}] {row[1]}")
            print(f"   corp_id: {row[0]} | 업종: {row[2]} | 대표: {row[3]}")

            if row[6]:
                snapshot = row[6] if isinstance(row[6], dict) else json.loads(row[6])
                fin = snapshot.get("financial", {})
                if fin and fin.get("revenue_krw"):
                    rev = fin["revenue_krw"] / 100000000
                    print(f"   매출: {rev:.0f}억 ({fin.get('fiscal_year', 'N/A')}년)")

                # 여신 정보
                credit = snapshot.get("credit", {})
                if credit.get("loan_summary"):
                    loan = credit["loan_summary"]
                    exposure = loan.get("total_exposure_krw", 0) / 100000000
                    grade = loan.get("risk_grade_internal", "N/A")
                    print(f"   여신: {exposure:.0f}억 | 등급: {grade}")
            print()


if __name__ == "__main__":
    asyncio.run(check())
