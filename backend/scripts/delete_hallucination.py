"""
P0 Hallucination Deletion Script
2026-02-08

탐지된 hallucination 시그널을 삭제(DISMISSED)합니다.
"""

import asyncio
import ssl

import asyncpg


HALLUCINATED_SIGNAL_IDS = [
    "3be62814-7d20-4d15-8950-5824923d71b6",  # 엠케이전자 88% 감소
]


async def main():
    # DB 연결 설정
    db_url = "postgresql://postgres.jvvhfylycswfedppmkld:aMgngVn1YKhb8iki@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

    # SSL 설정
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # 연결
    conn = await asyncpg.connect(
        db_url,
        ssl=ssl_context,
        statement_cache_size=0,
    )

    print("=" * 70)
    print("P0 Hallucination Deletion")
    print("=" * 70)

    for signal_id in HALLUCINATED_SIGNAL_IDS:
        print(f"\nDeleting signal: {signal_id}")

        # rkyc_signal 테이블에서 삭제
        try:
            result = await conn.execute("""
                DELETE FROM rkyc_signal
                WHERE signal_id = $1
            """, signal_id)
            print(f"  rkyc_signal: {result}")
        except Exception as e:
            print(f"  rkyc_signal error: {e}")

        # rkyc_signal_index는 CASCADE로 자동 삭제되어야 하지만 확인
        try:
            result = await conn.execute("""
                DELETE FROM rkyc_signal_index
                WHERE signal_id = $1
            """, signal_id)
            print(f"  rkyc_signal_index: {result}")
        except Exception as e:
            print(f"  rkyc_signal_index error: {e}")

    # 남은 시그널 확인
    remaining = await conn.fetch("""
        SELECT signal_id, title, corp_name
        FROM rkyc_signal_index
    """)

    print("\n" + "=" * 70)
    print(f"Remaining signals: {len(remaining)}")
    print("=" * 70)

    for sig in remaining:
        print(f"  - {sig['corp_name']}: {sig['title']}")

    await conn.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
