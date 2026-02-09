#!/usr/bin/env python3
"""
신규 등록 기업의 Internal Snapshot 생성 스크립트
"""

import asyncio
import sys
import os
import ssl
import json
import hashlib
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.jvvhfylycswfedppmkld:aMgngVn1YKhb8iki@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
)

async def get_corps_without_snapshot(conn) -> list:
    """Snapshot이 없는 기업 목록 조회"""
    rows = await conn.fetch("""
        SELECT c.corp_id, c.corp_name, c.industry_code, c.ceo_name, c.biz_no
        FROM corp c
        LEFT JOIN rkyc_internal_snapshot_latest l ON c.corp_id = l.corp_id
        WHERE l.corp_id IS NULL
    """)
    return [dict(row) for row in rows]


async def get_banking_data(conn, corp_id: str) -> dict | None:
    """Banking Data 조회"""
    row = await conn.fetchrow("""
        SELECT loan_exposure, deposit_trend, collateral_detail, trade_finance, financial_statements
        FROM rkyc_banking_data
        WHERE corp_id = $1
    """, corp_id)
    return dict(row) if row else None


def build_snapshot_json(corp: dict, banking_data: dict | None) -> dict:
    """PRD 7장 기준 Snapshot JSON 생성"""
    
    snapshot = {
        "schema_version": "v1.0",
        "corp": {
            "corp_id": corp["corp_id"],
            "corp_name": corp["corp_name"],
            "industry_code": corp.get("industry_code") or "Z99",
            "kyc_status": {
                "is_kyc_completed": True,
                "last_kyc_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "internal_risk_grade": "MED"
            }
        },
        "credit": {
            "has_loan": False,
            "loan_summary": {
                "total_exposure_krw": 0,
                "overdue_flag": False,
                "risk_grade_internal": "MED"
            }
        },
        "collateral": {
            "has_collateral": False,
            "collateral_summary": {
                "total_value_krw": 0,
                "ltv_ratio": 0
            }
        },
        "derived_hints": {
            "export_ratio_pct": 0,
            "key_materials": [],
            "overseas_operations": []
        }
    }
    
    if banking_data:
        loan = banking_data.get("loan_exposure") or {}
        if isinstance(loan, str):
            loan = json.loads(loan)
        
        total_exposure = loan.get("total_exposure_krw", 0)
        if total_exposure and total_exposure > 0:
            snapshot["credit"]["has_loan"] = True
            snapshot["credit"]["loan_summary"]["total_exposure_krw"] = total_exposure
            
            risk_indicators = loan.get("risk_indicators", {})
            snapshot["credit"]["loan_summary"]["overdue_flag"] = risk_indicators.get("overdue_flag", False)
            snapshot["credit"]["loan_summary"]["risk_grade_internal"] = risk_indicators.get("internal_grade", "MED")
        
        collateral = banking_data.get("collateral_detail") or {}
        if isinstance(collateral, str):
            collateral = json.loads(collateral)
        
        total_collateral = collateral.get("total_collateral_value", 0)
        if total_collateral and total_collateral > 0:
            snapshot["collateral"]["has_collateral"] = True
            snapshot["collateral"]["collateral_summary"]["total_value_krw"] = total_collateral
            snapshot["collateral"]["collateral_summary"]["ltv_ratio"] = collateral.get("avg_ltv", 0)
        
        trade = banking_data.get("trade_finance") or {}
        if isinstance(trade, str):
            trade = json.loads(trade)
        
        fx_exposure = trade.get("fx_exposure", {})
        if fx_exposure:
            snapshot["derived_hints"]["export_ratio_pct"] = fx_exposure.get("hedge_ratio", 0)
    
    return snapshot


async def cleanup_orphan_snapshots(conn, corp_ids: list):
    """Latest에 없는 Snapshot 삭제"""
    for corp_id in corp_ids:
        # 기존 snapshot 삭제 (latest에 연결되지 않은)
        await conn.execute("""
            DELETE FROM rkyc_internal_snapshot 
            WHERE corp_id = $1 
            AND snapshot_id NOT IN (
                SELECT snapshot_id FROM rkyc_internal_snapshot_latest WHERE corp_id = $1
            )
        """, corp_id)
        print(f"  [CLEANUP] Orphan snapshots removed for {corp_id}")


async def create_snapshot(conn, corp_id: str, snapshot_json: dict) -> str:
    """Snapshot 생성 및 Latest 포인터 업데이트"""
    
    snapshot_id = str(uuid4())
    
    # 기존 max version 조회
    max_version = await conn.fetchval("""
        SELECT COALESCE(MAX(snapshot_version), 0) FROM rkyc_internal_snapshot WHERE corp_id = $1
    """, corp_id)
    snapshot_version = max_version + 1
    
    snapshot_str = json.dumps(snapshot_json, ensure_ascii=False, sort_keys=True)
    snapshot_hash = hashlib.sha256(snapshot_str.encode()).hexdigest()
    
    # Snapshot 삽입
    await conn.execute("""
        INSERT INTO rkyc_internal_snapshot (snapshot_id, corp_id, snapshot_version, snapshot_json, snapshot_hash)
        VALUES ($1, $2, $3, $4, $5)
    """, snapshot_id, corp_id, snapshot_version, snapshot_str, snapshot_hash)
    
    # Latest 포인터 업데이트
    await conn.execute("""
        INSERT INTO rkyc_internal_snapshot_latest (corp_id, snapshot_id, snapshot_version, snapshot_hash)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (corp_id) DO UPDATE SET 
            snapshot_id = EXCLUDED.snapshot_id,
            snapshot_version = EXCLUDED.snapshot_version,
            snapshot_hash = EXCLUDED.snapshot_hash
    """, corp_id, snapshot_id, snapshot_version, snapshot_hash)
    
    return snapshot_id


async def main():
    print("=" * 60)
    print("Internal Snapshot Generation (New Companies)")
    print("=" * 60)
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    conn = await asyncpg.connect(
        DATABASE_URL.replace("?sslmode=require", ""),
        ssl=ssl_context,
        statement_cache_size=0,
    )
    
    try:
        corps = await get_corps_without_snapshot(conn)
        print(f"\n[Step 1] Companies without snapshot: {len(corps)}")
        
        if not corps:
            print("  All companies have snapshots.")
            return
        
        for corp in corps:
            print(f"  - {corp['corp_id']}: {corp['corp_name']}")
        
        # 고아 Snapshot 정리
        print(f"\n[Step 1.5] Cleaning up orphan snapshots...")
        corp_ids = [c["corp_id"] for c in corps]
        await cleanup_orphan_snapshots(conn, corp_ids)
        
        print(f"\n[Step 2] Creating snapshots...")
        
        success_count = 0
        for corp in corps:
            corp_id = corp["corp_id"]
            corp_name = corp["corp_name"]
            
            banking_data = await get_banking_data(conn, corp_id)
            snapshot_json = build_snapshot_json(corp, banking_data)
            snapshot_id = await create_snapshot(conn, corp_id, snapshot_json)
            
            print(f"  [OK] {corp_name}: {snapshot_id[:8]}...")
            success_count += 1
        
        print(f"\n[Result] {success_count}/{len(corps)} snapshots created")
        
    finally:
        await conn.close()
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
