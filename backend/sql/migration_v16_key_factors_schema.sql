-- Migration v16: Key Factors Schema Update
-- PRD: 핵심 리스크/기회 요인 생성 v1.0
-- key_risks, key_opportunities를 구조화된 JSONB로 저장

-- 기존 데이터 백업 (안전을 위해)
-- ALTER TABLE rkyc_loan_insight RENAME COLUMN key_risks TO key_risks_old;
-- ALTER TABLE rkyc_loan_insight RENAME COLUMN key_opportunities TO key_opportunities_old;

-- 이미 JSONB 타입이므로 스키마 변경 불필요
-- 새 구조:
-- key_risks: [{"priority": 1, "text": "...", "source_signal_id": "uuid", "_corrected": false}]
-- key_opportunities: [{"priority": 1, "text": "...", "source_signal_id": "uuid"}]

-- 기존 string[] 데이터를 새 구조로 변환하는 함수 (필요 시)
CREATE OR REPLACE FUNCTION migrate_key_factors_to_v16(old_data JSONB)
RETURNS JSONB AS $$
DECLARE
    result JSONB := '[]'::JSONB;
    item JSONB;
    idx INT := 1;
BEGIN
    IF old_data IS NULL OR jsonb_typeof(old_data) != 'array' THEN
        RETURN '[]'::JSONB;
    END IF;

    FOR item IN SELECT * FROM jsonb_array_elements(old_data)
    LOOP
        IF jsonb_typeof(item) = 'string' THEN
            -- 기존 string 형식 -> 새 객체 형식으로 변환
            result := result || jsonb_build_array(
                jsonb_build_object(
                    'priority', idx,
                    'text', item #>> '{}',
                    'source_signal_id', NULL,
                    '_migrated', true
                )
            );
        ELSIF jsonb_typeof(item) = 'object' THEN
            -- 이미 객체 형식이면 유지
            result := result || jsonb_build_array(item);
        END IF;
        idx := idx + 1;
    END LOOP;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- 기존 데이터 마이그레이션 (선택적)
-- UPDATE rkyc_loan_insight
-- SET key_risks = migrate_key_factors_to_v16(key_risks),
--     key_opportunities = migrate_key_factors_to_v16(key_opportunities)
-- WHERE jsonb_typeof(key_risks->0) = 'string'
--    OR jsonb_typeof(key_opportunities->0) = 'string';

-- 확인용 쿼리
-- SELECT corp_id,
--        jsonb_typeof(key_risks->0) as key_risks_type,
--        key_risks->0 as sample_risk
-- FROM rkyc_loan_insight;
