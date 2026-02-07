"""
P0 Hallucination Scanner Script
2026-02-08

직접 DB에서 시그널을 스캔하여 hallucination을 탐지합니다.
"""

import asyncio
import re
import ssl
from urllib.parse import urlparse, parse_qs

import asyncpg


async def main():
    # DB 연결 설정
    db_url = "postgresql://postgres.jvvhfylycswfedppmkld:aMgngVn1YKhb8iki@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

    # SSL 설정
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # 연결
    conn = await asyncpg.connect(
        db_url,
        ssl=ssl_context,
        statement_cache_size=0,  # pgbouncer 호환
    )

    print("=" * 70)
    print("P0 Hallucination Scanner")
    print("=" * 70)

    # 1. 모든 시그널 조회 (rkyc_signal_index 사용 - denormalized)
    signals = await conn.fetch("""
        SELECT si.signal_id, si.signal_type, si.event_type, si.title,
               si.summary_short as summary,
               si.corp_id, si.corp_name, si.impact_direction,
               si.impact_strength, si.confidence
        FROM rkyc_signal_index si
        ORDER BY si.created_at DESC
    """)

    print(f"\nScanning {len(signals)} signals...\n")

    # Hallucination 감지 패턴
    percentage_pattern = re.compile(r'[-+]?\d+(?:\.\d+)?%')

    hallucinated = []
    suspicious = []

    for signal in signals:
        title = signal['title'] or ""
        summary = signal['summary'] or ""
        text_to_check = f"{title} {summary}"
        percentages = percentage_pattern.findall(text_to_check)

        for pct in percentages:
            try:
                num_only = pct.replace("%", "").replace("+", "")
                num_value = float(num_only)

                # 극단적인 수치 (50% 이상) 탐지
                if abs(num_value) > 80:
                    hallucinated.append({
                        "id": str(signal['signal_id']),
                        "corp_name": signal['corp_name'],
                        "corp_id": signal['corp_id'],
                        "signal_type": signal['signal_type'],
                        "event_type": signal['event_type'],
                        "title": title,
                        "summary": summary[:100] + "..." if len(summary) > 100 else summary,
                        "percentage": pct,
                        "reason": f"극단적 수치: {pct}",
                    })
                    break
                elif abs(num_value) > 50:
                    # FINANCIAL_STATEMENT_UPDATE에서 영업이익 관련
                    if signal['event_type'] == "FINANCIAL_STATEMENT_UPDATE":
                        if "영업이익" in text_to_check or "순이익" in text_to_check:
                            hallucinated.append({
                                "id": str(signal['signal_id']),
                                "corp_name": signal['corp_name'],
                                "corp_id": signal['corp_id'],
                                "signal_type": signal['signal_type'],
                                "event_type": signal['event_type'],
                                "title": title,
                                "summary": summary[:100] + "..." if len(summary) > 100 else summary,
                                "percentage": pct,
                                "reason": f"재무제표 극단적 수치: {pct}",
                            })
                            break
                    else:
                        suspicious.append({
                            "id": str(signal['signal_id']),
                            "corp_name": signal['corp_name'],
                            "corp_id": signal['corp_id'],
                            "title": title,
                            "percentage": pct,
                        })

            except ValueError:
                continue

    # 결과 출력
    print("=" * 70)
    print(f"[HALLUCINATION] {len(hallucinated)}개 탐지")
    print("=" * 70)

    for i, h in enumerate(hallucinated, 1):
        print(f"\n[{i}] {h['corp_name']} ({h['corp_id']})")
        print(f"    Signal ID: {h['id']}")
        print(f"    Type: {h['signal_type']} / {h['event_type']}")
        print(f"    Title: {h['title']}")
        print(f"    Summary: {h['summary']}")
        print(f"    [!] Problem: {h['percentage']}")
        print(f"    Reason: {h['reason']}")

    if suspicious:
        print("\n" + "=" * 70)
        print(f"[SUSPICIOUS] (50-80%): {len(suspicious)}개")
        print("=" * 70)

        for i, s in enumerate(suspicious, 1):
            print(f"[{i}] {s['corp_name']}: {s['title']} ({s['percentage']})")

    # 통계
    print("\n" + "=" * 70)
    print("[STATS]")
    print("=" * 70)
    print(f"Total scanned: {len(signals)}")
    print(f"Hallucination: {len(hallucinated)}")
    print(f"Suspicious: {len(suspicious)}")
    print(f"OK: {len(signals) - len(hallucinated) - len(suspicious)}")

    print(f"\nAction needed: {len(hallucinated)}")

    await conn.close()

    return hallucinated


if __name__ == "__main__":
    asyncio.run(main())
