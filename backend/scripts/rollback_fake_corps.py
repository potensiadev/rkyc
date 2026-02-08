"""
가상 기업 (광주정밀기계, 전북식품) DART 데이터 롤백
"""
import asyncio
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine


async def rollback():
    print("=" * 60)
    print("가상 기업 DART 데이터 롤백")
    print("=" * 60)

    async with engine.begin() as conn:
        # 광주정밀기계, 전북식품 DART 데이터 롤백
        await conn.execute(text("""
            UPDATE corp SET
                dart_corp_code = NULL,
                established_date = NULL,
                headquarters = NULL,
                corp_class = NULL,
                homepage_url = NULL,
                jurir_no = NULL,
                corp_name_eng = NULL,
                acc_mt = NULL,
                dart_updated_at = NULL
            WHERE corp_id IN ('6201-2345678', '4028-1234567')
        """))
        print("\n[OK] 롤백 완료: 광주정밀기계, 전북식품")

        # 확인
        result = await conn.execute(text("""
            SELECT corp_id, corp_name, dart_corp_code, dart_updated_at
            FROM corp
            ORDER BY corp_name
        """))

        print("\n현재 corp 테이블 상태:")
        print("-" * 60)
        for row in result:
            dart_status = "[DART O]" if row[2] else "[DART X]"
            print(f"  {dart_status} {row[1]} ({row[0]})")
        print("-" * 60)
        print("\n해커톤 시연 대상: 동부건설, 삼성전자, 엠케이전자, 휴림로봇 (4개)")


if __name__ == "__main__":
    asyncio.run(rollback())
