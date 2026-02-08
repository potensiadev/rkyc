"""
가상 기업 (광주정밀기계, 전북식품) 완전 삭제
- DB의 모든 관련 테이블에서 삭제
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

FAKE_CORP_IDS = ['6201-2345678', '4028-1234567']  # 광주정밀기계, 전북식품


async def delete_fake_corps():
    print("=" * 60)
    print("가상 기업 완전 삭제")
    print("대상: 광주정밀기계 (6201-2345678), 전북식품 (4028-1234567)")
    print("=" * 60)

    async with engine.begin() as conn:
        # FK 순서대로 삭제 (자식 테이블 먼저)

        tables_to_clean = [
            # 시그널 관련
            ("rkyc_signal_embedding", "SELECT signal_id FROM rkyc_signal WHERE corp_id = ANY(:ids)", "signal_id"),
            ("rkyc_evidence", "SELECT signal_id FROM rkyc_signal WHERE corp_id = ANY(:ids)", "signal_id"),
            ("rkyc_signal_index", "corp_id"),
            ("rkyc_signal", "corp_id"),

            # 프로필/인사이트
            ("rkyc_corp_profile", "corp_id"),
            ("rkyc_case_index", "corp_id"),

            # Job
            ("rkyc_job", "corp_id"),

            # External Event
            ("rkyc_external_event_target", "corp_id"),

            # Context
            ("rkyc_unified_context", "corp_id"),

            # Document
            ("rkyc_fact", "corp_id"),
            ("rkyc_document_page", "SELECT doc_id FROM rkyc_document WHERE corp_id = ANY(:ids)", "doc_id"),
            ("rkyc_document", "corp_id"),

            # Snapshot
            ("rkyc_internal_snapshot_latest", "corp_id"),
            ("rkyc_internal_snapshot", "corp_id"),

            # Corp (마지막)
            ("corp", "corp_id"),
        ]

        for item in tables_to_clean:
            table = item[0]
            try:
                if len(item) == 2:
                    # 직접 corp_id로 삭제
                    col = item[1]
                    result = await conn.execute(
                        text(f"DELETE FROM {table} WHERE {col} = ANY(:ids)"),
                        {"ids": FAKE_CORP_IDS}
                    )
                    print(f"  [OK] {table}: {result.rowcount}개 삭제")
                else:
                    # 서브쿼리로 삭제
                    subquery = item[1]
                    col = item[2]
                    result = await conn.execute(
                        text(f"DELETE FROM {table} WHERE {col} IN ({subquery})"),
                        {"ids": FAKE_CORP_IDS}
                    )
                    print(f"  [OK] {table}: {result.rowcount}개 삭제")
            except Exception as e:
                if "does not exist" in str(e):
                    print(f"  [SKIP] {table}: 테이블 없음")
                else:
                    print(f"  [ERR] {table}: {e}")

        # 확인
        result = await conn.execute(text("SELECT corp_id, corp_name FROM corp ORDER BY corp_name"))
        rows = result.fetchall()

        print("\n" + "=" * 60)
        print(f"남은 기업 ({len(rows)}개):")
        print("=" * 60)
        for row in rows:
            print(f"  - {row[1]} ({row[0]})")


if __name__ == "__main__":
    asyncio.run(delete_fake_corps())
