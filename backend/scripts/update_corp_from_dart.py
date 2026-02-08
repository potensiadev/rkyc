"""
DART API를 통해 corp 테이블의 기업 정보를 업데이트하는 스크립트

실행 방법:
    cd backend
    python scripts/update_corp_from_dart.py
"""

import asyncio
import sys
import os

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, UTC
from sqlalchemy import text
from app.core.database import engine
from app.services.dart_api import (
    load_corp_codes,
    get_corp_code,
    get_company_info,
    get_largest_shareholders,
    get_financial_statements,
    get_executives,
)


async def get_all_corporations():
    """corp 테이블에서 모든 기업 조회"""
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT corp_id, corp_name, corp_reg_no, biz_no, industry_code, ceo_name
            FROM corp
            ORDER BY corp_name
        """))
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]


async def update_corporation_with_dart(corp_id: str, dart_data: dict):
    """corp 테이블을 DART 데이터로 업데이트"""
    async with engine.begin() as conn:
        await conn.execute(text("""
            UPDATE corp SET
                dart_corp_code = :dart_corp_code,
                established_date = :established_date,
                headquarters = :headquarters,
                corp_class = :corp_class,
                homepage_url = :homepage_url,
                jurir_no = :jurir_no,
                corp_name_eng = :corp_name_eng,
                acc_mt = :acc_mt,
                dart_updated_at = :dart_updated_at,
                updated_at = NOW()
            WHERE corp_id = :corp_id
        """), {
            "corp_id": corp_id,
            "dart_corp_code": dart_data.get("dart_corp_code"),
            "established_date": dart_data.get("established_date"),
            "headquarters": dart_data.get("headquarters"),
            "corp_class": dart_data.get("corp_class"),
            "homepage_url": dart_data.get("homepage_url"),
            "jurir_no": dart_data.get("jurir_no"),
            "corp_name_eng": dart_data.get("corp_name_eng"),
            "acc_mt": dart_data.get("acc_mt"),
            "dart_updated_at": dart_data.get("dart_updated_at"),
        })
        print(f"  ✅ DB 업데이트 완료: {corp_id}")


async def process_corporation(corp: dict) -> dict:
    """단일 기업에 대해 DART API 조회 및 업데이트"""
    corp_id = corp["corp_id"]
    corp_name = corp["corp_name"]

    print(f"\n{'='*60}")
    print(f"기업: {corp_name} ({corp_id})")
    print(f"{'='*60}")

    # 1. DART corp_code 조회
    print(f"  1. DART 고유번호 조회 중...")
    corp_code = await get_corp_code(corp_name=corp_name)

    if not corp_code:
        print(f"  ❌ DART에서 '{corp_name}' 고유번호를 찾을 수 없음")
        return {"corp_name": corp_name, "status": "NOT_FOUND", "corp_code": None}

    print(f"  ✅ DART 고유번호: {corp_code}")

    # 2. 기업개황 조회
    print(f"  2. 기업개황 조회 중...")
    company_info = await get_company_info(corp_code)

    if not company_info:
        print(f"  ❌ 기업개황 조회 실패")
        return {"corp_name": corp_name, "status": "NO_COMPANY_INFO", "corp_code": corp_code}

    print(f"     - 정식명칭: {company_info.corp_name}")
    print(f"     - 영문명: {company_info.corp_name_eng}")
    print(f"     - 대표이사: {company_info.ceo_name}")
    print(f"     - 법인등록번호: {company_info.jurir_no}")
    print(f"     - 사업자등록번호: {company_info.bizr_no}")
    print(f"     - 설립일: {company_info.est_dt}")
    print(f"     - 본사주소: {company_info.adres}")
    print(f"     - 업종코드: {company_info.induty_code}")
    print(f"     - 결산월: {company_info.acc_mt}")
    print(f"     - 법인구분: {company_info.corp_cls}")
    print(f"     - 홈페이지: {company_info.hm_url}")

    # 3. 최대주주 조회
    print(f"  3. 최대주주 현황 조회 중...")
    shareholders = await get_largest_shareholders(corp_code)
    if shareholders:
        print(f"     - 주주 수: {len(shareholders)}명")
        for i, sh in enumerate(shareholders[:3]):  # 상위 3명만 출력
            print(f"       [{i+1}] {sh.nm}: {sh.trmend_posesn_stock_qota_rt}%")
    else:
        print(f"     - 주주 정보 없음")

    # 4. 재무제표 조회
    print(f"  4. 재무제표 조회 중...")
    financials = await get_financial_statements(corp_code)
    if financials:
        print(f"     - 조회 연도: {len(financials)}개년")
        for f in financials:
            revenue_str = f"{f.revenue:,}" if f.revenue else "N/A"
            print(f"       [{f.bsns_year}] 매출: {revenue_str}원")
    else:
        print(f"     - 재무제표 없음")

    # 5. 임원현황 조회
    print(f"  5. 임원현황 조회 중...")
    executives = await get_executives(corp_code)
    if executives:
        print(f"     - 임원 수: {len(executives)}명")
        for i, ex in enumerate(executives[:3]):  # 상위 3명만 출력
            print(f"       [{i+1}] {ex.nm} ({ex.ofcps})")
    else:
        print(f"     - 임원 정보 없음")

    # 6. DB 업데이트
    print(f"  6. corp 테이블 업데이트 중...")
    dart_data = {
        "dart_corp_code": corp_code,
        "established_date": company_info.est_dt,
        "headquarters": company_info.adres,
        "corp_class": company_info.corp_cls,
        "homepage_url": company_info.hm_url,
        "jurir_no": company_info.jurir_no,
        "corp_name_eng": company_info.corp_name_eng,
        "acc_mt": company_info.acc_mt,
        "dart_updated_at": datetime.now(UTC),
    }

    await update_corporation_with_dart(corp_id, dart_data)

    return {
        "corp_name": corp_name,
        "status": "SUCCESS",
        "corp_code": corp_code,
        "company_info": company_info.to_dict() if company_info else None,
        "shareholders_count": len(shareholders) if shareholders else 0,
        "financials_count": len(financials) if financials else 0,
        "executives_count": len(executives) if executives else 0,
    }


async def main():
    print("=" * 60)
    print("DART API → corp 테이블 업데이트 스크립트")
    print("=" * 60)

    # 1. DART corp code 목록 로드
    print("\n[Step 1] DART 기업 고유번호 목록 로드 중...")
    success = await load_corp_codes()
    if not success:
        print("❌ DART 기업 목록 로드 실패")
        return
    print("✅ DART 기업 목록 로드 완료")

    # 2. corp 테이블에서 기업 목록 조회
    print("\n[Step 2] corp 테이블에서 기업 목록 조회 중...")
    corporations = await get_all_corporations()
    print(f"✅ {len(corporations)}개 기업 조회됨")

    for corp in corporations:
        print(f"   - {corp['corp_name']} ({corp['corp_id']})")

    # 3. 각 기업에 대해 DART API 조회 및 업데이트
    print("\n[Step 3] DART API 조회 및 업데이트 시작...")

    results = []
    for corp in corporations:
        try:
            result = await process_corporation(corp)
            results.append(result)
        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            results.append({
                "corp_name": corp["corp_name"],
                "status": "ERROR",
                "error": str(e),
            })

    # 4. 결과 요약
    print("\n" + "=" * 60)
    print("결과 요약")
    print("=" * 60)

    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    not_found_count = sum(1 for r in results if r["status"] == "NOT_FOUND")
    error_count = sum(1 for r in results if r["status"] in ("ERROR", "NO_COMPANY_INFO"))

    print(f"✅ 성공: {success_count}개")
    print(f"❌ DART 미등록: {not_found_count}개")
    print(f"⚠️  오류: {error_count}개")

    print("\n상세 결과:")
    for r in results:
        status_emoji = "✅" if r["status"] == "SUCCESS" else "❌"
        corp_code = r.get("corp_code", "N/A")
        print(f"  {status_emoji} {r['corp_name']}: {r['status']} (corp_code: {corp_code})")

    print("\n완료!")


if __name__ == "__main__":
    asyncio.run(main())
