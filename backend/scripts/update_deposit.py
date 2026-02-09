"""
Update deposit to 20억 for all companies
"""
import asyncio
import ssl
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def main():
    # Parse and prepare connection
    url = DATABASE_URL.replace("?sslmode=require", "")

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(url, ssl=ssl_context, statement_cache_size=0)

    try:
        # Update deposit_trend.current_balance to 20억
        result = await conn.execute("""
            UPDATE rkyc_banking_data
            SET
                deposit_trend = jsonb_set(
                    deposit_trend,
                    '{current_balance}',
                    '2000000000'::jsonb
                ),
                updated_at = NOW()
        """)
        print(f"Update result: {result}")

        # Verify
        rows = await conn.fetch("""
            SELECT
                bd.corp_id,
                c.corp_name,
                (bd.deposit_trend->>'current_balance')::bigint as deposit_krw
            FROM rkyc_banking_data bd
            JOIN corp c ON bd.corp_id = c.corp_id
            ORDER BY c.corp_name
        """)

        print("\n=== 업데이트 결과 ===")
        for row in rows:
            deposit_억 = row['deposit_krw'] / 100000000
            print(f"{row['corp_name']}: {deposit_억:.0f}억원")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
