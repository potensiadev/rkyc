-- ============================================================
-- Update total deposit to 20억 for all companies
-- 모든 기업 수신잔액 20억원으로 통일
-- ============================================================

-- deposit_trend.current_balance를 2,000,000,000원 (20억)으로 업데이트
UPDATE rkyc_banking_data
SET
    deposit_trend = jsonb_set(
        deposit_trend,
        '{current_balance}',
        '2000000000'::jsonb
    ),
    updated_at = NOW();

-- 검증: 업데이트 결과 확인
SELECT
    bd.corp_id,
    c.corp_name,
    (bd.deposit_trend->>'current_balance')::bigint / 100000000.0 AS deposit_억원,
    bd.updated_at
FROM rkyc_banking_data bd
JOIN corp c ON bd.corp_id = c.corp_id
ORDER BY c.corp_name;
