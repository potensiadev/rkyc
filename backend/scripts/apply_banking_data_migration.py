"""
Apply Banking Data Migration (v15) and Seed Data to Supabase

Usage:
    python scripts/apply_banking_data_migration.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg


async def apply_migration():
    """Apply migration and seed data"""

    # Database URL from environment or default
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres.jvvhfylycswfedppmkld:aMgngVn1YKhb8iki@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"
    )

    # Parse and prepare connection
    if "?" in database_url:
        database_url = database_url.split("?")[0]

    print("Connecting to Supabase...")

    try:
        conn = await asyncpg.connect(
            database_url,
            ssl="require",
            statement_cache_size=0  # pgbouncer compatibility
        )
        print("Connected successfully!")

        # Step 0: Drop existing table if exists (clean slate)
        print("\n0. Dropping existing table if exists...")
        await conn.execute("DROP VIEW IF EXISTS rkyc_banking_data_latest CASCADE")
        await conn.execute("DROP TABLE IF EXISTS rkyc_banking_data CASCADE")
        print("   Old table dropped!")

        # Step 1: Create table
        print("\n1. Creating rkyc_banking_data table...")
        await conn.execute("""
            CREATE TABLE rkyc_banking_data (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id) ON DELETE CASCADE,
                data_date DATE NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                loan_exposure JSONB,
                deposit_trend JSONB,
                card_usage JSONB,
                collateral_detail JSONB,
                trade_finance JSONB,
                financial_statements JSONB,
                risk_alerts JSONB DEFAULT '[]'::jsonb,
                opportunity_signals JSONB DEFAULT '[]'::jsonb,
                UNIQUE(corp_id, data_date)
            )
        """)
        print("   Table created!")

        # Step 2: Create indexes
        print("\n2. Creating indexes...")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_banking_data_corp ON rkyc_banking_data(corp_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_banking_data_date ON rkyc_banking_data(data_date DESC)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_banking_data_corp_date ON rkyc_banking_data(corp_id, data_date DESC)")
        print("   Indexes created!")

        # Step 3: Create GIN indexes
        print("\n3. Creating GIN indexes...")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_banking_data_risk_alerts ON rkyc_banking_data USING GIN (risk_alerts)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_banking_data_loan ON rkyc_banking_data USING GIN (loan_exposure)")
        print("   GIN indexes created!")

        # Step 4: Create view
        print("\n4. Creating latest data view...")
        await conn.execute("""
            CREATE OR REPLACE VIEW rkyc_banking_data_latest AS
            SELECT DISTINCT ON (corp_id) *
            FROM rkyc_banking_data
            ORDER BY corp_id, data_date DESC
        """)
        print("   View created!")

        # Step 5: Check existing corp_ids
        print("\n5. Checking existing corp_ids in corp table...")
        existing_corps = await conn.fetch("SELECT corp_id, corp_name FROM corp ORDER BY corp_name")
        print(f"   Found {len(existing_corps)} companies:")
        corp_ids = []
        for row in existing_corps:
            corp_name = row['corp_name'][:25] if row['corp_name'] else 'Unknown'
            print(f"      - {row['corp_id']}: {corp_name}")
            corp_ids.append(row['corp_id'])

        # Step 6: Apply seed data only for existing corps
        print("\n6. Applying seed data for existing companies...")
        seed_path = Path(__file__).parent.parent / "sql" / "seed_banking_data.sql"
        with open(seed_path, "r", encoding="utf-8") as f:
            seed_sql = f.read()

        # Split by INSERT INTO statements and execute only for existing corp_ids
        import re
        insert_statements = re.split(r'(?=-- \d+\.)', seed_sql)

        success_count = 0
        for stmt in insert_statements:
            if 'INSERT INTO rkyc_banking_data' in stmt:
                # Extract corp_id from the statement
                match = re.search(r"'(\d{4}-\d{7})'", stmt)
                if match:
                    corp_id = match.group(1)
                    if corp_id in corp_ids:
                        try:
                            await conn.execute(stmt)
                            print(f"      Inserted data for {corp_id}")
                            success_count += 1
                        except Exception as e:
                            print(f"      Failed for {corp_id}: {e}")
                    else:
                        print(f"      Skipped {corp_id} (not in corp table)")

        print(f"   Seed data applied for {success_count} companies!")

        # Verify
        print("\n6. Verifying data...")
        count = await conn.fetchval("SELECT COUNT(*) FROM rkyc_banking_data")
        print(f"   Total records in rkyc_banking_data: {count}")

        # List companies with banking data
        rows = await conn.fetch("""
            SELECT bd.corp_id, c.corp_name, bd.data_date,
                   jsonb_array_length(bd.risk_alerts) as risk_count,
                   jsonb_array_length(bd.opportunity_signals) as opp_count
            FROM rkyc_banking_data bd
            JOIN corp c ON c.corp_id = bd.corp_id
            ORDER BY c.corp_name
        """)

        print("\n   Companies with Banking Data:")
        print("   " + "-" * 70)
        for row in rows:
            corp_name = row['corp_name'][:20] if row['corp_name'] else 'Unknown'
            print(f"   {corp_name:<20} | {row['corp_id']:<15} | "
                  f"Risks: {row['risk_count']} | Opps: {row['opp_count']}")

        await conn.close()
        print("\n[OK] Migration and seed completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(apply_migration())
