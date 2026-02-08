#!/usr/bin/env python
"""
Delete hallucinated signals from database
"""

import asyncio
import asyncpg
import ssl

async def delete_hallucinated_signals():
    # Create SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(
        'postgresql://postgres.jvvhfylycswfedppmkld:aMgngVn1YKhb8iki@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres',
        ssl=ssl_context,
        statement_cache_size=0
    )

    # Hallucinated signal IDs - 엠케이전자 상장폐지 허위 정보
    hallucinated_ids = [
        'daacd2dc-ccdd-4b24-871d-de4e257714a6',  # GOVERNANCE_CHANGE - 상장폐지
        '8dbdc882-ee52-42de-bd1a-d3d29142af85',  # FINANCIAL_STATEMENT_UPDATE - 상장폐지
    ]

    for signal_id in hallucinated_ids:
        # Delete evidence first (FK constraint)
        ev_result = await conn.execute('DELETE FROM rkyc_evidence WHERE signal_id = $1', signal_id)
        print(f'Deleted evidence for {signal_id}: {ev_result}')

        # Delete from signal_index
        idx_result = await conn.execute('DELETE FROM rkyc_signal_index WHERE signal_id = $1', signal_id)
        print(f'Deleted signal_index for {signal_id}: {idx_result}')

        # Delete signal
        sig_result = await conn.execute('DELETE FROM rkyc_signal WHERE signal_id = $1', signal_id)
        print(f'Deleted signal {signal_id}: {sig_result}')
        print('---')

    await conn.close()
    print('Done - hallucinated signals removed')

if __name__ == '__main__':
    asyncio.run(delete_hallucinated_signals())
