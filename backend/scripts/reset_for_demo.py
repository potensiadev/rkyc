"""
해커톤 시연 전 데이터 초기화 스크립트

시그널, 프로필, 작업 데이터 삭제 (기업/스냅샷 유지)
빈 화면 시작 시나리오를 위한 준비
"""
import asyncio
import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine


async def reset_demo_data():
    print("=" * 60)
    print("해커톤 시연 데이터 초기화")
    print("=" * 60)
    print()
    print("삭제 대상:")
    print("  - rkyc_signal_index (Dashboard 인덱스)")
    print("  - rkyc_evidence (시그널 근거)")
    print("  - rkyc_signal (시그널)")
    print("  - rkyc_corp_profile (기업 프로필)")
    print("  - rkyc_job (분석 작업)")
    print()
    print("유지 대상:")
    print("  - corp (기업 마스터)")
    print("  - rkyc_internal_snapshot (내부 스냅샷)")
    print("  - rkyc_internal_snapshot_latest (최신 포인터)")
    print()

    confirm = input("계속하시겠습니까? (y/N): ")
    if confirm.lower() != 'y':
        print("취소되었습니다.")
        return

    async with engine.begin() as conn:
        # 삭제 순서: FK 의존성 고려
        tables = [
            ("rkyc_signal_index", "Dashboard 인덱스"),
            ("rkyc_evidence", "시그널 근거"),
            ("rkyc_signal", "시그널"),
            ("rkyc_corp_profile", "기업 프로필"),
            ("rkyc_job", "분석 작업"),
        ]

        for table, desc in tables:
            result = await conn.execute(text(f"DELETE FROM {table}"))
            print(f"  [OK] {desc} ({table}): {result.rowcount}개 삭제")

    print()
    print("=" * 60)
    print("초기화 완료!")
    print("=" * 60)

    # 최종 상태 확인
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT c.corp_name, l.snapshot_version
            FROM corp c
            LEFT JOIN rkyc_internal_snapshot_latest l ON c.corp_id = l.corp_id
            ORDER BY c.corp_name
        """))
        rows = result.fetchall()

        print()
        print(f"시연 준비 완료 - {len(rows)}개 기업:")
        for row in rows:
            snap = f"v{row[1]}" if row[1] else "없음"
            print(f"  - {row[0]} (Snapshot: {snap})")

    print()
    print("이제 Frontend에서 빈 화면이 표시됩니다.")
    print("Demo Panel에서 기업을 선택하고 분석을 실행하세요.")


if __name__ == "__main__":
    asyncio.run(reset_demo_data())
