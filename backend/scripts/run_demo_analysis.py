#!/usr/bin/env python
"""
Demo Analysis Runner - PRD v2.0 Hackathon Edition

6개 시드 기업에 대한 분석 직접 실행 (Celery 없이)

Usage:
    python scripts/run_demo_analysis.py --corp-id 8000-7647330
    python scripts/run_demo_analysis.py --all
"""

import asyncio
import argparse
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 6개 시드 기업
SEED_CORPS = [
    ("8001-3719240", "엠케이전자"),
    ("8000-7647330", "동부건설"),
    ("4028-1234567", "전북식품"),
    ("6201-2345678", "광주정밀기계"),
    ("4301-3456789", "삼성전자"),
    ("6701-4567890", "휴림로봇"),
]


async def get_db_connection():
    """DB 연결 생성"""
    import asyncpg
    import ssl

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


async def get_corp_data(conn, corp_id: str) -> dict:
    """기업 데이터 조회"""
    row = await conn.fetchrow("""
        SELECT corp_id, corp_name, industry_code, ceo_name, biz_no
        FROM corp WHERE corp_id = $1
    """, corp_id)

    if not row:
        return None

    return dict(row)


async def get_snapshot_data(conn, corp_id: str) -> dict:
    """최신 Snapshot 조회"""
    # 테이블 스키마에 맞게 수정
    try:
        row = await conn.fetchrow("""
            SELECT s.snapshot_json
            FROM rkyc_internal_snapshot s
            JOIN rkyc_internal_snapshot_latest l ON s.snapshot_id = l.snapshot_id
            WHERE l.corp_id = $1
        """, corp_id)

        if row and row['snapshot_json']:
            return row['snapshot_json']
    except Exception as e:
        logger.warning(f"Snapshot query failed: {e}")
    return {}


async def run_analysis(corp_id: str, corp_name: str) -> dict:
    """단일 기업 분석 실행"""
    from app.worker.pipelines.signal_extraction import SignalExtractionPipeline
    from app.worker.pipelines.hackathon_config import (
        ensure_minimum_signals,
        validate_demo_scenario,
        CORP_SENSITIVITY_CONFIG,
    )

    logger.info(f"Starting analysis for {corp_name} ({corp_id})")

    conn = await get_db_connection()

    try:
        # 기업 데이터 조회
        corp_data = await get_corp_data(conn, corp_id)
        if not corp_data:
            logger.error(f"Corporation not found: {corp_id}")
            return {"error": "Corporation not found"}

        # Snapshot 조회
        snapshot = await get_snapshot_data(conn, corp_id)

        # Context 구성
        corp_config = CORP_SENSITIVITY_CONFIG.get(corp_id, {})
        context = {
            'corp': {
                'corp_id': corp_id,
                'corp_name': corp_name,
                'industry_code': corp_data.get('industry_code', ''),
            },
            'corp_name': corp_name,
            'industry_name': corp_config.get('industry_name', ''),
            'snapshot': snapshot,
            'external_data': [],
        }

        logger.info(f"Context prepared for {corp_name}")

        # Signal Extraction Pipeline 실행
        pipeline = SignalExtractionPipeline()

        # 간단한 분석 실행 (외부 검색 없이)
        signals = await run_simple_extraction(context, corp_config)

        # 해커톤 모드: 최소 시그널 보장
        signals = ensure_minimum_signals(signals, corp_id, context)

        # 시연 시나리오 검증
        validation = validate_demo_scenario(corp_id, signals)

        logger.info(f"Analysis complete for {corp_name}: {len(signals)} signals")

        # DB에 시그널 저장
        saved_count = await save_signals(conn, corp_id, corp_name, signals)

        return {
            "corp_id": corp_id,
            "corp_name": corp_name,
            "signal_count": len(signals),
            "saved_count": saved_count,
            "validation": validation,
        }

    finally:
        await conn.close()


async def run_simple_extraction(context: dict, corp_config: dict) -> list:
    """간단한 시그널 추출 (LLM 없이 규칙 기반)"""
    from app.worker.pipelines.hackathon_config import (
        create_kyc_monitoring_signal,
        create_industry_monitoring_signal,
        create_policy_monitoring_signal,
        get_high_sensitivity_topics,
    )

    signals = []
    corp_id = context['corp']['corp_id']

    # 1. KYC 모니터링 시그널
    signals.append(create_kyc_monitoring_signal(corp_id, context))

    # 2. 업종 모니터링 시그널
    expected_types = corp_config.get('expected_signal_types', [])
    if 'INDUSTRY' in expected_types:
        signals.append(create_industry_monitoring_signal(corp_id, context))

    # 3. 정책 모니터링 시그널 (HIGH 민감도 토픽별)
    high_topics = get_high_sensitivity_topics(corp_id)
    for topic in high_topics[:2]:  # 최대 2개
        signals.append(create_policy_monitoring_signal(corp_id, topic, context))

    return signals


async def save_signals(conn, corp_id: str, corp_name: str, signals: list) -> int:
    """시그널을 DB에 저장"""
    import hashlib
    from datetime import datetime

    saved = 0

    for signal in signals:
        # event_signature 생성
        sig_content = f"{corp_id}:{signal['event_type']}:{signal['title']}"
        event_signature = hashlib.sha256(sig_content.encode()).hexdigest()

        # 중복 확인
        exists = await conn.fetchval("""
            SELECT 1 FROM rkyc_signal WHERE event_signature = $1
        """, event_signature)

        if exists:
            logger.info(f"Signal already exists: {signal['title'][:30]}...")
            continue

        try:
            # title을 summary 앞에 추가
            full_summary = f"[{signal['title']}] {signal['summary']}"

            # rkyc_signal에 저장 (title 없음, summary에 합침)
            signal_id = await conn.fetchval("""
                INSERT INTO rkyc_signal (
                    corp_id, signal_type, event_type,
                    impact_direction, impact_strength, confidence,
                    summary, event_signature, snapshot_version,
                    created_at, signal_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 1, $9, 'NEW')
                RETURNING signal_id
            """,
                corp_id,
                signal['signal_type'],
                signal['event_type'],
                signal['impact_direction'],
                signal['impact_strength'],
                signal['confidence'],
                full_summary,
                event_signature,
                datetime.utcnow(),
            )

            # rkyc_signal_index에도 저장
            summary_short = signal['summary'][:200] if len(signal['summary']) > 200 else signal['summary']
            await conn.execute("""
                INSERT INTO rkyc_signal_index (
                    signal_id, corp_id, corp_name, industry_code,
                    signal_type, event_type,
                    impact_direction, impact_strength, confidence,
                    title, summary_short, evidence_count, detected_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
                signal_id,
                corp_id,
                corp_name,
                signal.get('industry_code', ''),
                signal['signal_type'],
                signal['event_type'],
                signal['impact_direction'],
                signal['impact_strength'],
                signal['confidence'],
                signal['title'],
                summary_short,
                len(signal.get('evidence', [])),
                datetime.utcnow(),
            )

            # Evidence 저장
            for ev in signal.get('evidence', []):
                await conn.execute("""
                    INSERT INTO rkyc_evidence (
                        signal_id, evidence_type, ref_type, ref_value, snippet
                    ) VALUES ($1, $2, $3, $4, $5)
                """,
                    signal_id,
                    ev.get('evidence_type', 'EXTERNAL'),
                    ev.get('ref_type', 'URL'),
                    ev.get('ref_value', ''),
                    ev.get('snippet', ''),
                )

            saved += 1
            logger.info(f"Saved signal: {signal['title'][:40]}...")

        except Exception as e:
            logger.error(f"Failed to save signal: {e}")

    return saved


async def run_all():
    """모든 시드 기업 분석"""
    results = []

    for corp_id, corp_name in SEED_CORPS:
        try:
            result = await run_analysis(corp_id, corp_name)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to analyze {corp_name}: {e}")
            results.append({
                "corp_id": corp_id,
                "corp_name": corp_name,
                "error": str(e),
            })

    return results


async def main():
    parser = argparse.ArgumentParser(description='Demo Analysis Runner')
    parser.add_argument('--corp-id', help='Specific corp_id to analyze')
    parser.add_argument('--all', action='store_true', help='Analyze all seed corps')
    args = parser.parse_args()

    if args.all:
        print("=== Running Analysis for All Seed Corps ===")
        results = await run_all()

        print("\n=== Results ===")
        for r in results:
            if 'error' in r:
                print(f"[FAIL] {r['corp_name']}: {r['error']}")
            else:
                status = "[OK]" if r['validation']['passed'] else "[WARN]"
                print(f"{status} {r['corp_name']}: {r['signal_count']} signals (saved: {r['saved_count']})")

    elif args.corp_id:
        # 특정 기업 찾기
        corp_name = None
        for cid, cname in SEED_CORPS:
            if cid == args.corp_id:
                corp_name = cname
                break

        if not corp_name:
            print(f"Unknown corp_id: {args.corp_id}")
            print(f"Available: {[c[0] for c in SEED_CORPS]}")
            sys.exit(1)

        result = await run_analysis(args.corp_id, corp_name)
        print(f"\n=== Result for {corp_name} ===")
        print(f"Signals: {result.get('signal_count', 0)}")
        print(f"Saved: {result.get('saved_count', 0)}")
        print(f"Validation: {result.get('validation', {})}")

    else:
        parser.print_help()


if __name__ == '__main__':
    asyncio.run(main())
