"""Verify Harim data insertion"""
import asyncio
import ssl
import asyncpg
import json

DATABASE_URL = "postgresql://postgres.jvvhfylycswfedppmkld:aMgngVn1YKhb8iki@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

async def main():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(DATABASE_URL, ssl=ssl_context, statement_cache_size=0)

    try:
        # Corp table
        print("=== CORP TABLE ===")
        corp = await conn.fetchrow("SELECT * FROM corp WHERE corp_id = '4038-161113'")
        if corp:
            print(f"Corp Name: {corp['corp_name']}")
            print(f"CEO: {corp['ceo_name']}")
            print(f"DART Code: {corp['dart_corp_code']}")
            print(f"Industry: {corp['industry_code']}")
            print(f"Corp Class: {corp['corp_class']}")

        # Banking data
        print("\n=== BANKING DATA ===")
        bd = await conn.fetchrow("""
            SELECT corp_id, data_date, loan_exposure, risk_alerts, opportunity_signals
            FROM rkyc_banking_data
            WHERE corp_id = '4038-161113'
        """)
        if bd:
            loan = json.loads(bd['loan_exposure'])
            print(f"Total Exposure: {loan['total_exposure_krw']:,} KRW")
            print(f"Internal Grade: {loan['risk_indicators']['internal_grade']}")

            print("\nRisk Alerts:")
            alerts = json.loads(bd['risk_alerts'])
            for a in alerts:
                print(f"  [{a['severity']}] {a['title']}")

            print("\nOpportunity Signals:")
            opps = json.loads(bd['opportunity_signals'])
            for o in opps:
                print(f"  - {o}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
