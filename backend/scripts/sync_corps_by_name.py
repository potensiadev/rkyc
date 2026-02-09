#!/usr/bin/env python3
"""
기업명으로 DART API를 조회하여 corp 테이블에 동기화하는 스크립트

Usage:
    cd backend
    python -m scripts.sync_corps_by_name
"""

import asyncio
import sys
import os
import ssl

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from datetime import datetime, timezone

# DART API 모듈 임포트
from app.services.dart_api import (
    load_corp_codes,
    get_company_info_by_name,
    get_corp_code,
)

# 동기화할 기업명 목록
TARGET_CORP_NAMES = [
    "대한과학",
    "파이오링크",
    "팬엔터테인먼트",
    "이엘피",
    "크라우드웍스",
]

# Supabase Transaction Pooler 연결 문자열
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.jvvhfylycswfedppmkld:aMgngVn1YKhb8iki@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
)


async def upsert_corp(conn, corp_data: dict) -> bool:
    """
    corp 테이블에 기업 정보 UPSERT
    """
    # corp_id 생성 (신규 기업용)
    bizr_no = corp_data.get("bizr_no") or ""
    jurir_no = corp_data.get("jurir_no") or ""
    corp_code = corp_data.get("corp_code", "")

    if bizr_no:
        # 사업자번호 기반 ID: 9XXX-XXXXXXX
        corp_id = f"9{bizr_no[:3]}-{bizr_no[3:10]}"
    elif jurir_no:
        # 법인등록번호 기반 ID: J + 앞 10자리
        corp_id = f"J{jurir_no[:4]}-{jurir_no[4:11]}"
    else:
        # DART corp_code 기반 ID
        corp_id = f"D{corp_code[:4]}-{corp_code[4:]}"

    # 기존 데이터 확인 (corp_code 또는 jurir_no로)
    existing = await conn.fetchrow(
        "SELECT corp_id FROM corp WHERE dart_corp_code = $1 OR jurir_no = $2",
        corp_code, jurir_no
    )

    if existing:
        corp_id = existing["corp_id"]
        print(f"  [DB] Updating existing corp: {corp_id}")
    else:
        print(f"  [DB] Inserting new corp: {corp_id}")

    # industry_code 매핑 (DART induty_code → 표준 industry_code)
    induty_code = corp_data.get("induty_code") or ""
    industry_code = induty_code[:3] if induty_code else "Z99"  # 기본값

    # corp_class 매핑
    corp_cls = corp_data.get("corp_cls") or "E"

    # UPSERT 쿼리
    query = """
        INSERT INTO corp (
            corp_id, corp_name, corp_reg_no, biz_no, industry_code, ceo_name,
            dart_corp_code, established_date, headquarters, corp_class, homepage_url,
            jurir_no, corp_name_eng, acc_mt, dart_updated_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
        )
        ON CONFLICT (corp_id) DO UPDATE SET
            corp_name = EXCLUDED.corp_name,
            biz_no = EXCLUDED.biz_no,
            industry_code = EXCLUDED.industry_code,
            ceo_name = EXCLUDED.ceo_name,
            dart_corp_code = EXCLUDED.dart_corp_code,
            established_date = EXCLUDED.established_date,
            headquarters = EXCLUDED.headquarters,
            corp_class = EXCLUDED.corp_class,
            homepage_url = EXCLUDED.homepage_url,
            jurir_no = EXCLUDED.jurir_no,
            corp_name_eng = EXCLUDED.corp_name_eng,
            acc_mt = EXCLUDED.acc_mt,
            dart_updated_at = EXCLUDED.dart_updated_at,
            updated_at = NOW()
        RETURNING corp_id
    """

    try:
        result = await conn.fetchval(
            query,
            corp_id,
            corp_data.get("corp_name", "Unknown"),
            corp_data.get("jurir_no"),  # corp_reg_no = jurir_no
            corp_data.get("bizr_no"),
            industry_code,
            corp_data.get("ceo_name") or "Unknown",
            corp_data.get("corp_code"),
            corp_data.get("est_dt"),
            corp_data.get("adres"),
            corp_cls,
            corp_data.get("hm_url"),
            corp_data.get("jurir_no"),
            corp_data.get("corp_name_eng"),
            corp_data.get("acc_mt"),
            datetime.now(timezone.utc),
        )
        print(f"  [DB] Upserted: {result}")
        return True
    except Exception as e:
        print(f"  [DB] Error: {e}")
        return False


async def main():
    print("=" * 60)
    print("DART API → Corp 테이블 동기화 (기업명 기반)")
    print("=" * 60)
    print(f"Target corps: {TARGET_CORP_NAMES}")
    print()

    # 1. DART corp codes 로드
    print("[Step 1] DART corp codes 로드...")
    await load_corp_codes()
    print()

    # 2. 각 기업 정보 조회
    print("[Step 2] DART API에서 기업 정보 조회...")
    found_corps = {}
    not_found = []

    for corp_name in TARGET_CORP_NAMES:
        print(f"\n  조회 중: {corp_name}")
        try:
            info = await get_company_info_by_name(corp_name)
            if info:
                found_corps[corp_name] = info.to_dict()
                print(f"  [OK] Found: {info.corp_name} (jurir_no={info.jurir_no}, bizr_no={info.bizr_no})")
                print(f"    - CEO: {info.ceo_name}")
                print(f"    - 주소: {info.adres}")
                print(f"    - 업종: {info.induty_code}")
                print(f"    - 설립일: {info.est_dt}")
            else:
                not_found.append(corp_name)
                print(f"  [FAIL] Not found: {corp_name}")
        except Exception as e:
            not_found.append(corp_name)
            print(f"  [ERROR] {corp_name} - {e}")

    print(f"\n[Step 2 결과] 찾음: {len(found_corps)}개, 못찾음: {len(not_found)}개")
    if not_found:
        print(f"  못찾은 기업: {not_found}")

    if not found_corps:
        print("\n[ERROR] 조회된 기업이 없습니다!")
        return

    # 3. DB에 동기화
    print(f"\n[Step 3] Corp 테이블에 동기화...")

    # Supabase 연결 (SSL 필수)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(
        DATABASE_URL.replace("?sslmode=require", ""),
        ssl=ssl_context,
        statement_cache_size=0,  # pgbouncer 호환
    )

    try:
        success_count = 0
        for corp_name, corp_data in found_corps.items():
            print(f"\n  동기화 중: {corp_name}")
            if await upsert_corp(conn, corp_data):
                success_count += 1

        print(f"\n[Step 3 결과] 성공: {success_count}/{len(found_corps)}개")
    finally:
        await conn.close()

    # 4. 결과 확인
    print(f"\n[Step 4] 동기화 결과 확인...")
    conn = await asyncpg.connect(
        DATABASE_URL.replace("?sslmode=require", ""),
        ssl=ssl_context,
        statement_cache_size=0,
    )

    try:
        rows = await conn.fetch("""
            SELECT corp_id, corp_name, dart_corp_code, jurir_no, biz_no, ceo_name, industry_code
            FROM corp
            WHERE dart_updated_at >= NOW() - INTERVAL '1 hour'
            ORDER BY dart_updated_at DESC
        """)
        print(f"\n  최근 동기화된 기업 ({len(rows)}개):")
        for row in rows:
            print(f"    - {row['corp_id']}: {row['corp_name']} (CEO: {row['ceo_name']}, 업종: {row['industry_code']})")
    finally:
        await conn.close()

    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
