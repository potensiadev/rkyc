"""
소규모 기업 5개 완전 추가 스크립트

1. corp 테이블에 기업 추가
2. DART API로 기업 정보 조회 및 업데이트
3. DART 재무제표 기반 Internal Snapshot 생성
"""
import asyncio
import sys
import os
import uuid
import hashlib
import json
from datetime import datetime, UTC

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine
from app.services.dart_api import (
    load_corp_codes,
    get_corp_code,
    get_company_info,
    get_financial_statements,
    get_largest_shareholders,
    get_executives,
)


# 추가할 5개 소규모 기업
NEW_CORPS = [
    {
        "corp_id": "9001-0000001",
        "corp_name": "크라우드웍스",
        "industry_code": "J62",  # 소프트웨어 개발
    },
    {
        "corp_id": "9001-0000002",
        "corp_name": "이엘피",
        "industry_code": "C26",  # 전자부품
    },
    {
        "corp_id": "9001-0000003",
        "corp_name": "팬엔터테인먼트",
        "industry_code": "R90",  # 엔터테인먼트
    },
    {
        "corp_id": "9001-0000004",
        "corp_name": "대한과학",
        "industry_code": "C27",  # 의료/과학기기
    },
    {
        "corp_id": "9001-0000005",
        "corp_name": "파이오링크",
        "industry_code": "J62",  # IT/보안
    },
]


def generate_internal_snapshot(
    corp_id: str,
    corp_name: str,
    financials: list,
    shareholders: list,
    company_info: dict,
) -> dict:
    """
    DART 재무제표 기반 Internal Snapshot 생성 (PRD 7장 스키마)

    은행 내부 데이터는 재무제표 기반으로 합리적으로 추정
    """
    # 최신 재무데이터
    latest_fin = financials[0] if financials else None

    # 매출, 자산, 부채 추출
    revenue = latest_fin.revenue if latest_fin else 0
    total_assets = latest_fin.total_assets if latest_fin else 0
    total_liabilities = latest_fin.total_liabilities if latest_fin else 0
    total_equity = latest_fin.total_equity if latest_fin else 0
    debt_ratio = latest_fin.debt_ratio if latest_fin else 0

    # 여신 노출액 추정 (총부채의 10-30% 수준으로 가정)
    estimated_loan = int(total_liabilities * 0.15) if total_liabilities else 50000000  # 5천만원 기본

    # 내부등급 추정 (부채비율 기반)
    if debt_ratio and debt_ratio < 100:
        risk_grade = "LOW"
    elif debt_ratio and debt_ratio < 200:
        risk_grade = "MED"
    else:
        risk_grade = "HIGH"

    # 주주 정보 변환
    shareholder_list = []
    for sh in shareholders[:5]:  # 상위 5명
        shareholder_list.append({
            "name": sh.nm,
            "ratio_pct": sh.trmend_posesn_stock_qota_rt,
            "source": "DART",
        })

    snapshot = {
        "schema_version": "v1.0",
        "corp": {
            "corp_id": corp_id,
            "corp_name": corp_name,
            "kyc_status": {
                "is_kyc_completed": True,
                "last_kyc_updated": datetime.now(UTC).strftime("%Y-%m-%d"),
                "internal_risk_grade": risk_grade,
            },
        },
        "credit": {
            "has_loan": True,
            "loan_summary": {
                "total_exposure_krw": estimated_loan,
                "overdue_flag": False,
                "overdue_days": 0,
                "risk_grade_internal": risk_grade,
            },
        },
        "collateral": {
            "has_collateral": estimated_loan > 100000000,  # 1억 이상이면 담보 있음
            "collateral_summary": {
                "total_value_krw": int(estimated_loan * 1.2) if estimated_loan > 100000000 else 0,
                "collateral_type": "부동산" if estimated_loan > 500000000 else "예금",
            } if estimated_loan > 100000000 else None,
        },
        "financial": {
            "source": "DART",
            "fiscal_year": latest_fin.bsns_year if latest_fin else "2024",
            "revenue_krw": revenue,
            "operating_profit_krw": latest_fin.operating_profit if latest_fin else None,
            "net_income_krw": latest_fin.net_income if latest_fin else None,
            "total_assets_krw": total_assets,
            "total_liabilities_krw": total_liabilities,
            "total_equity_krw": total_equity,
            "debt_ratio_pct": debt_ratio,
        },
        "shareholders": shareholder_list,
        "derived_hints": {
            "is_sme": revenue < 100000000000 if revenue else True,  # 1000억 미만 중소기업
            "export_ratio_hint": "LOW",  # 소규모 기업 기본값
            "industry_sensitivity": "MED",
        },
        "metadata": {
            "created_at": datetime.now(UTC).isoformat(),
            "data_source": "DART_API",
            "is_demo": True,
        },
    }

    return snapshot


async def add_corp_to_db(corp: dict, dart_info: dict, financials: list, shareholders: list):
    """corp 테이블에 기업 추가 및 DART 정보 업데이트"""

    async with engine.begin() as conn:
        # 1. corp 테이블에 추가
        await conn.execute(text("""
            INSERT INTO corp (
                corp_id, corp_reg_no, corp_name, biz_no, industry_code, ceo_name,
                dart_corp_code, established_date, headquarters, corp_class,
                homepage_url, jurir_no, corp_name_eng, acc_mt, dart_updated_at
            ) VALUES (
                :corp_id, :corp_reg_no, :corp_name, :biz_no, :industry_code, :ceo_name,
                :dart_corp_code, :established_date, :headquarters, :corp_class,
                :homepage_url, :jurir_no, :corp_name_eng, :acc_mt, :dart_updated_at
            )
            ON CONFLICT (corp_id) DO UPDATE SET
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
        """), {
            "corp_id": corp["corp_id"],
            "corp_reg_no": dart_info.get("jurir_no", f"REG-{corp['corp_id']}"),
            "corp_name": dart_info.get("corp_name", corp["corp_name"]),
            "biz_no": dart_info.get("bizr_no", f"BIZ-{corp['corp_id'][-6:]}"),
            "industry_code": corp["industry_code"],
            "ceo_name": dart_info.get("ceo_name", "대표이사"),
            "dart_corp_code": dart_info.get("corp_code"),
            "established_date": dart_info.get("est_dt"),
            "headquarters": dart_info.get("adres"),
            "corp_class": dart_info.get("corp_cls"),
            "homepage_url": dart_info.get("hm_url"),
            "jurir_no": dart_info.get("jurir_no"),
            "corp_name_eng": dart_info.get("corp_name_eng"),
            "acc_mt": dart_info.get("acc_mt"),
            "dart_updated_at": datetime.now(UTC),
        })

        print(f"    [OK] corp 테이블 추가/업데이트")


async def add_internal_snapshot(corp_id: str, snapshot: dict):
    """Internal Snapshot 추가"""

    snapshot_json = json.dumps(snapshot, ensure_ascii=False, default=str)
    snapshot_hash = hashlib.sha256(snapshot_json.encode()).hexdigest()
    snapshot_id = str(uuid.uuid4())

    async with engine.begin() as conn:
        # 기존 스냅샷 버전 확인
        result = await conn.execute(text("""
            SELECT COALESCE(MAX(snapshot_version), 0) as max_version
            FROM rkyc_internal_snapshot
            WHERE corp_id = :corp_id
        """), {"corp_id": corp_id})
        row = result.fetchone()
        new_version = (row[0] if row else 0) + 1

        # 스냅샷 추가 (CAST 사용 - asyncpg 호환)
        await conn.execute(text("""
            INSERT INTO rkyc_internal_snapshot (
                snapshot_id, corp_id, snapshot_version, snapshot_json, snapshot_hash
            ) VALUES (
                :snapshot_id, :corp_id, :snapshot_version, CAST(:snapshot_json AS jsonb), :snapshot_hash
            )
        """), {
            "snapshot_id": snapshot_id,
            "corp_id": corp_id,
            "snapshot_version": new_version,
            "snapshot_json": snapshot_json,
            "snapshot_hash": snapshot_hash,
        })

        # 최신 포인터 업데이트
        await conn.execute(text("""
            INSERT INTO rkyc_internal_snapshot_latest (
                corp_id, snapshot_id, snapshot_version, snapshot_hash
            ) VALUES (
                :corp_id, :snapshot_id, :snapshot_version, :snapshot_hash
            )
            ON CONFLICT (corp_id) DO UPDATE SET
                snapshot_id = EXCLUDED.snapshot_id,
                snapshot_version = EXCLUDED.snapshot_version,
                snapshot_hash = EXCLUDED.snapshot_hash,
                updated_at = NOW()
        """), {
            "corp_id": corp_id,
            "snapshot_id": snapshot_id,
            "snapshot_version": new_version,
            "snapshot_hash": snapshot_hash,
        })

        print(f"    [OK] Internal Snapshot v{new_version} 생성")


async def process_corp(corp: dict):
    """단일 기업 처리"""

    print(f"\n{'='*60}")
    print(f"기업: {corp['corp_name']} ({corp['corp_id']})")
    print(f"{'='*60}")

    # 1. DART corp_code 조회
    print("  [1] DART 고유번호 조회...")
    corp_code = await get_corp_code(corp_name=corp["corp_name"])

    if not corp_code:
        print(f"    [ERR] DART에서 찾을 수 없음")
        return False

    print(f"    [OK] DART 코드: {corp_code}")

    # 2. 기업개황 조회
    print("  [2] 기업개황 조회...")
    company_info = await get_company_info(corp_code)

    if not company_info:
        print(f"    [ERR] 기업개황 조회 실패")
        return False

    dart_info = {
        "corp_code": corp_code,
        "corp_name": company_info.corp_name,
        "corp_name_eng": company_info.corp_name_eng,
        "ceo_name": company_info.ceo_name,
        "corp_cls": company_info.corp_cls,
        "jurir_no": company_info.jurir_no,
        "bizr_no": company_info.bizr_no,
        "adres": company_info.adres,
        "hm_url": company_info.hm_url,
        "est_dt": company_info.est_dt,
        "acc_mt": company_info.acc_mt,
    }

    print(f"    - 정식명칭: {company_info.corp_name}")
    print(f"    - 대표이사: {company_info.ceo_name}")
    print(f"    - 법인구분: {company_info.corp_cls}")

    # 3. 재무제표 조회
    print("  [3] 재무제표 조회...")
    financials = await get_financial_statements(corp_code)

    if financials:
        latest = financials[0]
        revenue_str = f"{latest.revenue/100000000:.0f}억" if latest.revenue else "N/A"
        print(f"    - {latest.bsns_year}년 매출: {revenue_str}")
    else:
        print(f"    - 재무제표 없음")

    # 4. 최대주주 조회
    print("  [4] 최대주주 조회...")
    shareholders = await get_largest_shareholders(corp_code)

    if shareholders:
        print(f"    - 주주 수: {len(shareholders)}명")
        for sh in shareholders[:3]:
            print(f"      - {sh.nm}: {sh.trmend_posesn_stock_qota_rt}%")
    else:
        shareholders = []
        print(f"    - 주주 정보 없음")

    # 5. corp 테이블 추가
    print("  [5] DB 저장...")
    await add_corp_to_db(corp, dart_info, financials, shareholders)

    # 6. Internal Snapshot 생성
    print("  [6] Internal Snapshot 생성...")
    snapshot = generate_internal_snapshot(
        corp_id=corp["corp_id"],
        corp_name=company_info.corp_name,
        financials=financials,
        shareholders=shareholders,
        company_info=dart_info,
    )
    await add_internal_snapshot(corp["corp_id"], snapshot)

    return True


async def main():
    print("=" * 70)
    print("소규모 기업 5개 완전 추가")
    print("- DART 데이터 기반 corp 테이블 추가")
    print("- DART 재무제표 기반 Internal Snapshot 생성")
    print("=" * 70)

    # 1. DART 코드 로드
    print("\n[Step 1] DART 기업 목록 로드...")
    await load_corp_codes()
    print("완료")

    # 2. 각 기업 처리
    print(f"\n[Step 2] {len(NEW_CORPS)}개 기업 추가...")

    success_count = 0
    for corp in NEW_CORPS:
        try:
            if await process_corp(corp):
                success_count += 1
        except Exception as e:
            print(f"    [ERR] 처리 실패: {e}")

    # 3. 결과 확인
    print("\n" + "=" * 70)
    print("결과 요약")
    print("=" * 70)
    print(f"성공: {success_count}/{len(NEW_CORPS)}")

    # 4. 최종 corp 테이블 확인
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT c.corp_id, c.corp_name, c.dart_corp_code, c.ceo_name,
                   l.snapshot_version
            FROM corp c
            LEFT JOIN rkyc_internal_snapshot_latest l ON c.corp_id = l.corp_id
            ORDER BY c.corp_name
        """))
        rows = result.fetchall()

        print(f"\n현재 등록된 기업 ({len(rows)}개):")
        print("-" * 70)
        for row in rows:
            dart_status = "O" if row[2] else "X"
            snap_status = f"v{row[4]}" if row[4] else "없음"
            print(f"  [{dart_status}] {row[1]} ({row[0]})")
            print(f"      대표: {row[3] or 'N/A'} | Snapshot: {snap_status}")
        print("-" * 70)

    print("\n완료!")


if __name__ == "__main__":
    asyncio.run(main())
