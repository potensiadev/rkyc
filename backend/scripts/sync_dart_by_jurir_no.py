#!/usr/bin/env python
"""
DART API Corp Data Sync by Jurir No (법인등록번호)

법인등록번호로 기업을 조회하고 DART API에서 데이터를 가져와 corp 테이블을 업데이트합니다.

Usage:
    python scripts/sync_dart_by_jurir_no.py
"""

import asyncio
import logging
import sys
import os
import ssl
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 대상 법인등록번호 목록
TARGET_JURIR_NOS = [
    "1101116384963",
    "1101111790834",
    "1101111531460",
    "1101110948997",
    "1101112035578",
]


async def get_db_connection():
    """DB 연결 생성"""
    import asyncpg

    db_url = os.getenv('DATABASE_URL', '')
    if '?' in db_url:
        db_url = db_url.split('?')[0]

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    return await asyncpg.connect(
        db_url,
        ssl=ssl_context,
        statement_cache_size=0
    )


async def get_corps_by_jurir_no(conn, jurir_nos: list) -> list:
    """법인등록번호로 기업 조회"""
    # corp_reg_no 또는 jurir_no 필드에서 검색
    rows = await conn.fetch("""
        SELECT corp_id, corp_name, corp_reg_no, jurir_no, biz_no, ceo_name
        FROM corp
        WHERE corp_reg_no = ANY($1) OR jurir_no = ANY($1)
    """, jurir_nos)

    return [dict(row) for row in rows]


async def fetch_dart_company_info(corp_name: str) -> dict:
    """DART API에서 기업 정보 조회"""
    from app.services.dart_api import (
        get_corp_code,
        get_company_info,
        get_largest_shareholders,
        load_corp_codes,
    )

    logger.info(f"[DART] Fetching data for {corp_name}...")

    # Corp code 로드
    await load_corp_codes()

    # Corp code 조회
    corp_code = await get_corp_code(corp_name=corp_name)
    if not corp_code:
        logger.warning(f"[DART] Could not find corp_code for {corp_name}")
        return {}

    logger.info(f"[DART] Found corp_code: {corp_code}")

    # 기업개황 조회
    company_info = await get_company_info(corp_code)
    if not company_info:
        logger.warning(f"[DART] Could not get company info for {corp_name}")
        return {"dart_corp_code": corp_code}

    result = {
        "dart_corp_code": corp_code,
        "corp_name": company_info.corp_name,
        "corp_name_eng": company_info.corp_name_eng,
        "ceo_name": company_info.ceo_name,
        "jurir_no": company_info.jurir_no,
        "biz_no": company_info.bizr_no,
        "headquarters": company_info.adres,
        "homepage_url": company_info.hm_url,
        "established_date": company_info.est_dt,
        "acc_mt": company_info.acc_mt,
        "corp_class": company_info.corp_cls,
        "industry_code": company_info.induty_code,
    }

    # 최대주주 조회
    try:
        shareholders = await get_largest_shareholders(corp_code)
        if shareholders:
            result["largest_shareholders"] = [
                {
                    "name": s.nm,
                    "ratio_pct": s.trmend_posesn_stock_qota_rt,
                    "relate": s.relate,
                }
                for s in shareholders[:5]
            ]
    except Exception as e:
        logger.warning(f"[DART] Failed to get shareholders: {e}")

    return result


async def update_corp_table(conn, corp_id: str, dart_data: dict) -> bool:
    """corp 테이블 업데이트"""
    if not dart_data.get("dart_corp_code"):
        logger.warning(f"[DB] No DART data for {corp_id}, skipping update")
        return False

    update_fields = []
    params = []
    param_idx = 1

    field_mapping = {
        "dart_corp_code": dart_data.get("dart_corp_code"),
        "corp_name": dart_data.get("corp_name"),
        "corp_name_eng": dart_data.get("corp_name_eng"),
        "ceo_name": dart_data.get("ceo_name"),
        "jurir_no": dart_data.get("jurir_no"),
        "biz_no": dart_data.get("biz_no"),
        "headquarters": dart_data.get("headquarters"),
        "homepage_url": dart_data.get("homepage_url"),
        "established_date": dart_data.get("established_date"),
        "acc_mt": dart_data.get("acc_mt"),
        "corp_class": dart_data.get("corp_class"),
        "dart_updated_at": datetime.now(timezone.utc),
    }

    for field, value in field_mapping.items():
        if value is not None:
            update_fields.append(f"{field} = ${param_idx}")
            params.append(value)
            param_idx += 1

    if not update_fields:
        logger.info(f"[DB] No fields to update for {corp_id}")
        return False

    params.append(corp_id)

    sql = f"""
        UPDATE corp SET
            {', '.join(update_fields)}
        WHERE corp_id = ${param_idx}
    """

    try:
        await conn.execute(sql, *params)
        logger.info(f"[DB] Updated {corp_id} with DART data")
        return True
    except Exception as e:
        logger.error(f"[DB] Failed to update {corp_id}: {e}")
        return False


async def main():
    print("=" * 60)
    print("DART API Corp Data Sync by Jurir No")
    print("=" * 60)
    print(f"Target Jurir Nos: {len(TARGET_JURIR_NOS)}")
    print("=" * 60)

    conn = await get_db_connection()

    try:
        # 1. 법인등록번호로 기업 조회
        print("\n[Step 1] Finding corporations by jurir_no...")
        corps = await get_corps_by_jurir_no(conn, TARGET_JURIR_NOS)

        if not corps:
            print("No corporations found with the given jurir_nos")
            print("Searching all corps in database...")

            # 모든 기업 조회
            all_corps = await conn.fetch("""
                SELECT corp_id, corp_name, corp_reg_no, jurir_no, biz_no
                FROM corp
                ORDER BY corp_id
            """)
            print(f"\nAll corporations in database ({len(all_corps)}):")
            for row in all_corps:
                print(f"  - {row['corp_name']} ({row['corp_id']})")
                print(f"    corp_reg_no: {row['corp_reg_no']}, jurir_no: {row['jurir_no']}")
            return

        print(f"Found {len(corps)} corporations:")
        for corp in corps:
            print(f"  - {corp['corp_name']} ({corp['corp_id']})")

        # 2. DART API로 데이터 조회 및 업데이트
        print("\n[Step 2] Fetching DART data and updating...")

        results = []
        for corp in corps:
            corp_id = corp['corp_id']
            corp_name = corp['corp_name']

            print(f"\n--- {corp_name} ({corp_id}) ---")

            dart_data = await fetch_dart_company_info(corp_name)

            if dart_data:
                print(f"  DART Corp Code: {dart_data.get('dart_corp_code', 'N/A')}")
                print(f"  CEO: {dart_data.get('ceo_name', 'N/A')}")
                print(f"  Address: {dart_data.get('headquarters', 'N/A')[:50]}..." if dart_data.get('headquarters') else "  Address: N/A")
                print(f"  Established: {dart_data.get('established_date', 'N/A')}")
                print(f"  Jurir No: {dart_data.get('jurir_no', 'N/A')}")

                if dart_data.get("largest_shareholders"):
                    print(f"  Shareholders:")
                    for sh in dart_data["largest_shareholders"][:3]:
                        print(f"    - {sh['name']}: {sh['ratio_pct']}%")

                success = await update_corp_table(conn, corp_id, dart_data)
                results.append({
                    "corp_id": corp_id,
                    "corp_name": corp_name,
                    "success": success,
                    "dart_data": dart_data,
                })
            else:
                print(f"  [FAILED] Could not fetch DART data")
                results.append({
                    "corp_id": corp_id,
                    "corp_name": corp_name,
                    "success": False,
                    "dart_data": {},
                })

        # 결과 요약
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        success_count = sum(1 for r in results if r["success"])
        print(f"Success: {success_count}/{len(results)}")

        for r in results:
            status = "[OK]" if r["success"] else "[FAIL]"
            print(f"  {status} {r['corp_name']} ({r['corp_id']})")

        # CLAUDE.md 업데이트용 출력
        if results:
            print("\n" + "=" * 60)
            print("SEED DATA FOR CLAUDE.md")
            print("=" * 60)
            for r in results:
                if r["success"]:
                    d = r.get("dart_data", {})
                    print(f"\n**{r['corp_name']}** `{r['corp_id']}`")
                    print(f"- DART 고유번호: {d.get('dart_corp_code', 'N/A')}")
                    print(f"- 영문명: {d.get('corp_name_eng', 'N/A')}")
                    print(f"- 대표이사: {d.get('ceo_name', 'N/A')}")
                    print(f"- 법인등록번호: {d.get('jurir_no', 'N/A')}")
                    print(f"- 사업자등록번호: {d.get('biz_no', 'N/A')}")
                    print(f"- 본사: {d.get('headquarters', 'N/A')}")
                    print(f"- 홈페이지: {d.get('homepage_url', 'N/A')}")
                    print(f"- 설립일: {d.get('established_date', 'N/A')}")
                    print(f"- 결산월: {d.get('acc_mt', 'N/A')}월")
                    print(f"- 법인구분: {d.get('corp_class', 'N/A')}")

    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
