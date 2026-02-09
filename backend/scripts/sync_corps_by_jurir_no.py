#!/usr/bin/env python3
"""
법인등록번호(jurir_no)로 DART API를 조회하여 corp 테이블에 동기화하는 스크립트

Usage:
    cd backend
    python -m scripts.sync_corps_by_jurir_no
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
    get_company_info,
    _corp_code_cache,
    _corp_code_by_name,
    DART_API_KEY,
    DART_BASE_URL,
)
import httpx

# 동기화할 법인등록번호 목록
TARGET_JURIR_NOS = [
    "1101116384963",
    "1101111790834",
    "1101111531460",
    "1101110948997",
    "1101112035578",
]

# Supabase Transaction Pooler 연결 문자열
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.zzubjstqkuxigfqostpu:!Rkyc240101@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"
)


async def find_corp_by_jurir_no(jurir_no: str) -> dict | None:
    """
    법인등록번호로 DART 기업 정보 조회

    DART API는 corp_code로 조회해야 하므로:
    1. 모든 corp_code 목록을 순회
    2. 각 corp_code에 대해 company.json 호출
    3. jurir_no가 일치하면 반환

    이 방식은 비효율적이므로, 실제로는 corpCode.xml에서
    직접 검색하거나 캐시를 활용해야 함.
    """
    # 캐시된 corp_code 목록이 없으면 로드
    if not _corp_code_cache:
        print(f"[DART] Loading corp codes...")
        await load_corp_codes()
        print(f"[DART] Loaded {len(_corp_code_cache)} corp codes")

    # 모든 corp_code에 대해 순회하며 jurir_no 매칭
    # 너무 많으면 시간이 오래 걸리므로 batch로 처리
    corp_codes = [k for k in _corp_code_cache.keys() if not k.startswith("stock:")]

    print(f"[DART] Searching for jurir_no={jurir_no} in {len(corp_codes)} corps...")

    # 배치로 처리 (rate limit 고려)
    batch_size = 10
    found = None

    for i in range(0, len(corp_codes), batch_size):
        batch = corp_codes[i:i + batch_size]
        tasks = [get_company_info(corp_code) for corp_code in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for corp_code, result in zip(batch, results):
            if isinstance(result, Exception):
                continue
            if result and result.jurir_no == jurir_no:
                print(f"[DART] Found! corp_code={corp_code}, corp_name={result.corp_name}")
                return result.to_dict()

        # 진행상황 출력
        if (i + batch_size) % 100 == 0:
            print(f"[DART] Searched {i + batch_size}/{len(corp_codes)}...")

    return None


async def search_corp_by_jurir_no_fast(jurir_no: str) -> dict | None:
    """
    법인등록번호로 DART 기업 정보를 빠르게 조회하는 방법

    DART의 공시검색 API를 활용하여 법인등록번호로 검색 시도
    """
    # 캐시된 corp_code 목록에서 검색
    if not _corp_code_cache:
        print(f"[DART] Loading corp codes...")
        await load_corp_codes()

    # 일반적으로 법인등록번호 앞 6자리는 등기소 코드
    # 110111 = 서울중앙지방법원
    # 모든 입력이 110111로 시작하므로 서울 소재 기업일 가능성 높음

    # corpCode.xml은 기업명/종목코드만 포함하므로
    # company.json API로 각 기업의 jurir_no를 조회해야 함

    # 효율적인 방법: 최근 공시 기업 중심으로 검색
    # 여기서는 모든 기업을 순회하는 대신 랜덤 샘플링

    corp_codes = [k for k in _corp_code_cache.keys() if not k.startswith("stock:")]

    # 상장사 우선 검색 (주로 법인등록번호 공개됨)
    stock_corp_codes = [k.replace("stock:", "") for k in _corp_code_cache.keys() if k.startswith("stock:")]

    print(f"[DART] Searching jurir_no={jurir_no} in {len(stock_corp_codes)} listed companies first...")

    # 상장사 먼저 검색
    for i, corp_code in enumerate(stock_corp_codes):
        try:
            info = await get_company_info(corp_code)
            if info and info.jurir_no == jurir_no:
                print(f"[DART] Found! corp_code={corp_code}, corp_name={info.corp_name}")
                return info.to_dict()
        except Exception as e:
            pass

        if (i + 1) % 50 == 0:
            print(f"[DART] Searched {i + 1}/{len(stock_corp_codes)} listed companies...")
            await asyncio.sleep(0.5)  # Rate limit 방지

    print(f"[DART] Not found in listed companies. Searching all corps...")

    # 전체 검색 (시간 오래 걸림)
    for i, corp_code in enumerate(corp_codes):
        try:
            info = await get_company_info(corp_code)
            if info and info.jurir_no == jurir_no:
                print(f"[DART] Found! corp_code={corp_code}, corp_name={info.corp_name}")
                return info.to_dict()
        except Exception as e:
            pass

        if (i + 1) % 100 == 0:
            print(f"[DART] Searched {i + 1}/{len(corp_codes)} corps...")
            await asyncio.sleep(0.5)  # Rate limit 방지

        # 최대 1000개까지만 검색 (시간 제한)
        if i >= 1000:
            print(f"[DART] Reached search limit. jurir_no={jurir_no} not found.")
            break

    return None


async def search_all_jurir_nos(jurir_nos: list[str]) -> dict[str, dict]:
    """
    여러 법인등록번호를 한 번에 검색
    효율적으로 검색하기 위해 한 번의 순회로 모든 jurir_no 체크
    """
    if not _corp_code_cache:
        print(f"[DART] Loading corp codes...")
        await load_corp_codes()

    corp_codes = [k for k in _corp_code_cache.keys() if not k.startswith("stock:")]
    target_set = set(jurir_nos)
    found = {}

    print(f"[DART] Searching for {len(target_set)} jurir_nos in {len(corp_codes)} corps...")

    for i, corp_code in enumerate(corp_codes):
        if len(found) == len(target_set):
            print(f"[DART] All {len(target_set)} corps found!")
            break

        try:
            info = await get_company_info(corp_code)
            if info and info.jurir_no in target_set:
                print(f"[DART] Found! jurir_no={info.jurir_no}, corp_name={info.corp_name}")
                found[info.jurir_no] = info.to_dict()
        except Exception as e:
            pass

        if (i + 1) % 100 == 0:
            print(f"[DART] Searched {i + 1}/{len(corp_codes)} corps, found {len(found)}/{len(target_set)}...")
            await asyncio.sleep(0.3)  # Rate limit 방지

    return found


async def upsert_corp(conn, corp_data: dict) -> bool:
    """
    corp 테이블에 기업 정보 UPSERT
    """
    # corp_id 생성 (신규 기업용)
    # 기존 형식: 8001-3719240 (7자리-7자리)
    # 여기서는 bizr_no 기반으로 생성
    bizr_no = corp_data.get("bizr_no") or ""
    if bizr_no:
        corp_id = f"9{bizr_no[:3]}-{bizr_no[3:]}"
    else:
        # bizr_no 없으면 corp_code 기반
        corp_code = corp_data.get("corp_code", "")
        corp_id = f"D{corp_code}"

    # 기존 데이터 확인 (jurir_no로)
    existing = await conn.fetchrow(
        "SELECT corp_id FROM corp WHERE jurir_no = $1",
        corp_data.get("jurir_no")
    )

    if existing:
        corp_id = existing["corp_id"]
        print(f"[DB] Updating existing corp: {corp_id}")
    else:
        print(f"[DB] Inserting new corp: {corp_id}")

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
            corp_data.get("ceo_name", "Unknown"),
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
        print(f"[DB] Upserted corp: {result}")
        return True
    except Exception as e:
        print(f"[DB] Error upserting corp: {e}")
        return False


async def main():
    print("=" * 60)
    print("DART API → Corp 테이블 동기화")
    print("=" * 60)
    print(f"Target jurir_nos: {TARGET_JURIR_NOS}")
    print()

    # 1. DART API에서 기업 정보 조회
    print("[Step 1] DART API에서 기업 정보 조회...")
    found_corps = await search_all_jurir_nos(TARGET_JURIR_NOS)

    if not found_corps:
        print("[ERROR] No corps found in DART!")
        return

    print(f"\n[Step 1 Result] Found {len(found_corps)} corps:")
    for jurir_no, corp_data in found_corps.items():
        print(f"  - {corp_data.get('corp_name')} (jurir_no={jurir_no})")

    # 찾지 못한 jurir_no 출력
    not_found = set(TARGET_JURIR_NOS) - set(found_corps.keys())
    if not_found:
        print(f"\n[WARNING] Not found in DART: {not_found}")

    # 2. DB에 동기화
    print(f"\n[Step 2] Corp 테이블에 동기화...")

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
        for jurir_no, corp_data in found_corps.items():
            if await upsert_corp(conn, corp_data):
                success_count += 1

        print(f"\n[Step 2 Result] Successfully synced {success_count}/{len(found_corps)} corps")
    finally:
        await conn.close()

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
