"""
해커톤 시연 준비 상태 확인 스크립트

모든 체크리스트 항목을 자동으로 확인합니다.
"""
import asyncio
import sys
import os
import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine

# 설정
API_BASE = os.getenv("API_BASE_URL", "https://rkyc-production.up.railway.app")
FRONTEND_URL = "https://rkyc-wine.vercel.app"
EXPECTED_CORPS = 9


async def check_database():
    """데이터베이스 상태 확인"""
    print("\n[1] 데이터베이스 상태")
    print("-" * 40)

    issues = []

    async with engine.connect() as conn:
        # 기업 수 확인
        result = await conn.execute(text("SELECT COUNT(*) FROM corp"))
        corp_count = result.scalar()
        status = "✅" if corp_count == EXPECTED_CORPS else "❌"
        print(f"  {status} 기업 수: {corp_count}/{EXPECTED_CORPS}")
        if corp_count != EXPECTED_CORPS:
            issues.append(f"기업 수 불일치: {corp_count}/{EXPECTED_CORPS}")

        # 스냅샷 확인
        result = await conn.execute(text("SELECT COUNT(*) FROM rkyc_internal_snapshot_latest"))
        snap_count = result.scalar()
        status = "✅" if snap_count == EXPECTED_CORPS else "⚠️"
        print(f"  {status} 스냅샷 수: {snap_count}/{EXPECTED_CORPS}")
        if snap_count != EXPECTED_CORPS:
            issues.append(f"스냅샷 수 불일치: {snap_count}/{EXPECTED_CORPS}")

        # 시그널 수 확인 (빈 화면 시작이면 0이어야 함)
        result = await conn.execute(text("SELECT COUNT(*) FROM rkyc_signal"))
        signal_count = result.scalar()
        if signal_count == 0:
            print(f"  ✅ 시그널 수: {signal_count} (빈 화면 준비 완료)")
        else:
            print(f"  ⚠️ 시그널 수: {signal_count} (빈 화면이 아님)")

        # 기업별 상태
        result = await conn.execute(text("""
            SELECT c.corp_name, c.dart_corp_code, l.snapshot_version
            FROM corp c
            LEFT JOIN rkyc_internal_snapshot_latest l ON c.corp_id = l.corp_id
            ORDER BY c.corp_name
        """))
        rows = result.fetchall()

        print("\n  기업별 상태:")
        for row in rows:
            dart = "✓" if row[1] else "✗"
            snap = f"v{row[2]}" if row[2] else "없음"
            print(f"    - {row[0]}: DART[{dart}] Snapshot[{snap}]")

    return issues


def check_api():
    """API 서버 상태 확인"""
    print("\n[2] API 서버 상태")
    print("-" * 40)

    issues = []

    try:
        # Health check
        response = httpx.get(f"{API_BASE}/health", timeout=10)
        if response.status_code == 200:
            print(f"  ✅ Health: {API_BASE}/health")
        else:
            print(f"  ❌ Health: {response.status_code}")
            issues.append("API 서버 health check 실패")

        # Corporations endpoint
        response = httpx.get(f"{API_BASE}/api/v1/corporations", timeout=10)
        if response.status_code == 200:
            corps = response.json()
            print(f"  ✅ Corporations: {len(corps)}개")
        else:
            print(f"  ❌ Corporations: {response.status_code}")
            issues.append("기업 목록 API 실패")

        # Signals endpoint
        response = httpx.get(f"{API_BASE}/api/v1/signals", timeout=10)
        if response.status_code == 200:
            signals = response.json()
            count = len(signals) if isinstance(signals, list) else signals.get("total", 0)
            print(f"  ✅ Signals: {count}개")
        else:
            print(f"  ❌ Signals: {response.status_code}")
            issues.append("시그널 목록 API 실패")

    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
        issues.append(f"API 연결 실패: {e}")

    return issues


def check_frontend():
    """Frontend 상태 확인"""
    print("\n[3] Frontend 상태")
    print("-" * 40)

    issues = []

    try:
        response = httpx.get(FRONTEND_URL, timeout=10)
        if response.status_code == 200:
            print(f"  ✅ Frontend: {FRONTEND_URL}")
        else:
            print(f"  ❌ Frontend: {response.status_code}")
            issues.append("Frontend 접속 실패")
    except Exception as e:
        print(f"  ❌ Frontend 연결 실패: {e}")
        issues.append(f"Frontend 연결 실패: {e}")

    return issues


async def main():
    print("=" * 60)
    print("해커톤 시연 준비 상태 확인")
    print("=" * 60)

    all_issues = []

    # 1. 데이터베이스
    db_issues = await check_database()
    all_issues.extend(db_issues)

    # 2. API 서버
    api_issues = check_api()
    all_issues.extend(api_issues)

    # 3. Frontend
    frontend_issues = check_frontend()
    all_issues.extend(frontend_issues)

    # 최종 결과
    print("\n" + "=" * 60)
    if not all_issues:
        print("✅ 시연 준비 완료!")
        print("=" * 60)
        print("\n다음 단계:")
        print(f"  1. 브라우저에서 {FRONTEND_URL} 접속")
        print("  2. Demo Panel에서 기업 선택")
        print("  3. '분석 실행 (시연용)' 버튼 클릭")
    else:
        print("❌ 시연 준비 미완료")
        print("=" * 60)
        print("\n해결 필요:")
        for issue in all_issues:
            print(f"  - {issue}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
