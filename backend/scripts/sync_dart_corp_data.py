#!/usr/bin/env python
"""
DART API Corp Data Sync Script

4개 시드 기업의 corp 테이블 데이터를 DART API에서 가져온 100% Fact 데이터로 업데이트합니다.

Usage:
    python scripts/sync_dart_corp_data.py
    python scripts/sync_dart_corp_data.py --dry-run  # 실제 DB 업데이트 없이 확인만
"""

import asyncio
import argparse
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


# 4개 시드 기업 (corp_id, corp_name)
SEED_CORPS = [
    ("8001-3719240", "엠케이전자"),
    ("8000-7647330", "동부건설"),
    ("4301-3456789", "삼성전자"),
    ("6701-4567890", "휴림로봇"),
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

    # pgbouncer 호환: statement_cache_size=0
    return await asyncpg.connect(
        db_url,
        ssl=ssl_context,
        statement_cache_size=0
    )


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
        return {"corp_code": corp_code}

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
    shareholders = await get_largest_shareholders(corp_code)
    if shareholders:
        result["largest_shareholders"] = [
            {
                "name": s.nm,
                "ratio_pct": s.trmend_posesn_stock_qota_rt,
                "relate": s.relate,
            }
            for s in shareholders[:5]  # 상위 5명만
        ]

    return result


async def update_corp_table(conn, corp_id: str, dart_data: dict, dry_run: bool = False):
    """corp 테이블 업데이트"""
    if not dart_data.get("dart_corp_code"):
        logger.warning(f"[DB] No DART data for {corp_id}, skipping update")
        return False

    # 업데이트할 필드들
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

    if dry_run:
        logger.info(f"[DRY-RUN] Would update {corp_id}:")
        for field, value in field_mapping.items():
            if value:
                logger.info(f"  {field}: {value}")
        return True

    try:
        await conn.execute(sql, *params)
        logger.info(f"[DB] Updated {corp_id} with DART data")
        return True
    except Exception as e:
        logger.error(f"[DB] Failed to update {corp_id}: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description='Sync corp data from DART API')
    parser.add_argument('--dry-run', action='store_true', help='Do not update DB, just show what would be updated')
    args = parser.parse_args()

    print("=" * 60)
    print("DART API Corp Data Sync")
    print("=" * 60)
    print(f"Mode: {'DRY-RUN (no DB changes)' if args.dry_run else 'LIVE (will update DB)'}")
    print(f"Companies: {len(SEED_CORPS)}")
    print("=" * 60)

    conn = await get_db_connection()

    results = []

    try:
        for corp_id, corp_name in SEED_CORPS:
            print(f"\n--- {corp_name} ({corp_id}) ---")

            # DART API에서 데이터 조회
            dart_data = await fetch_dart_company_info(corp_name)

            if dart_data:
                print(f"  DART Corp Code: {dart_data.get('dart_corp_code', 'N/A')}")
                print(f"  CEO: {dart_data.get('ceo_name', 'N/A')}")
                print(f"  Address: {dart_data.get('headquarters', 'N/A')[:50]}..." if dart_data.get('headquarters') else "  Address: N/A")
                print(f"  Established: {dart_data.get('established_date', 'N/A')}")
                print(f"  Homepage: {dart_data.get('homepage_url', 'N/A')}")

                if dart_data.get("largest_shareholders"):
                    print(f"  Shareholders:")
                    for sh in dart_data["largest_shareholders"][:3]:
                        print(f"    - {sh['name']}: {sh['ratio_pct']}%")

                # DB 업데이트
                success = await update_corp_table(conn, corp_id, dart_data, args.dry_run)
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

    finally:
        await conn.close()

    # 결과 요약
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    success_count = sum(1 for r in results if r["success"])
    print(f"Success: {success_count}/{len(SEED_CORPS)}")

    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"  {status} {r['corp_name']} ({r['corp_id']})")

    # CLAUDE.md 업데이트용 출력
    print("\n" + "=" * 60)
    print("SEED DATA FOR CLAUDE.md")
    print("=" * 60)
    print("```")
    print("| 기업명 | corp_id | industry_code | ceo_name | DART corp_code |")
    print("|-------|---------|---------------|----------|----------------|")
    for r in results:
        d = r.get("dart_data", {})
        print(f"| {r['corp_name']} | {r['corp_id']} | {d.get('industry_code', 'N/A')} | {d.get('ceo_name', 'N/A')} | {d.get('dart_corp_code', 'N/A')} |")
    print("```")


if __name__ == '__main__':
    asyncio.run(main())
