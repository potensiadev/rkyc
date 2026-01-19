-- ============================================
-- Migration v8: Corp Data Sync
-- 이미지 데이터 기준으로 기업 정보 동기화
-- 실행일: 2026-01-19
-- ============================================

-- 변경 내용:
-- | corp_id | 변경 전 corp_name | 변경 후 corp_name | 변경 전 biz_no | 변경 후 biz_no | 변경 전 ceo_name | 변경 후 ceo_name |
-- |---------|-------------------|-------------------|----------------|----------------|------------------|------------------|
-- | 4301-3456789 | 익산바이오텍 | 삼성전자 | 567-89-01234 | 124-81-00998 | 박바이오 | 전영현 |
-- | 6201-2345678 | 광주정밀기계 | 광주정밀기계 | 456-78-90123 | 415-02-96323 | 최광수 | 강성우 |
-- | 4028-1234567 | 전북식품 | 전북식품 | 345-67-89012 | 418-01-55362 | 이정민 | 강동구 |
-- | 6701-4567890 | 나주태양에너지 | 휴림로봇 | 678-90-12345 | 109-81-60401 | 송태양 | 김봉관 |
-- | 8000-7647330 | 동부건설 | 동부건설 | 234-56-78901 | 824-87-03495 | 박동호 | 윤진오 |
-- | 8001-3719240 | 엠케이전자 | 엠케이전자 | 123-45-67890 | 135-81-06406 | 김명규 | 현기진 |

BEGIN;

-- ============================================
-- 1. corp 테이블 업데이트
-- ============================================

-- 4301-3456789: 익산바이오텍 → 삼성전자
UPDATE corp SET
    corp_name = '삼성전자',
    biz_no = '124-81-00998',
    ceo_name = '전영현',
    updated_at = NOW()
WHERE corp_id = '4301-3456789';

-- 6201-2345678: 광주정밀기계 (이름 유지, biz_no/ceo 변경)
UPDATE corp SET
    biz_no = '415-02-96323',
    ceo_name = '강성우',
    updated_at = NOW()
WHERE corp_id = '6201-2345678';

-- 4028-1234567: 전북식품 (이름 유지, biz_no/ceo 변경)
UPDATE corp SET
    biz_no = '418-01-55362',
    ceo_name = '강동구',
    updated_at = NOW()
WHERE corp_id = '4028-1234567';

-- 6701-4567890: 나주태양에너지 → 휴림로봇
UPDATE corp SET
    corp_name = '휴림로봇',
    biz_no = '109-81-60401',
    ceo_name = '김봉관',
    updated_at = NOW()
WHERE corp_id = '6701-4567890';

-- 8000-7647330: 동부건설 (이름 유지, biz_no/ceo 변경)
UPDATE corp SET
    biz_no = '824-87-03495',
    ceo_name = '윤진오',
    updated_at = NOW()
WHERE corp_id = '8000-7647330';

-- 8001-3719240: 엠케이전자 (이름 유지, biz_no/ceo 변경)
UPDATE corp SET
    biz_no = '135-81-06406',
    ceo_name = '현기진',
    updated_at = NOW()
WHERE corp_id = '8001-3719240';

-- ============================================
-- 2. rkyc_signal_index 테이블 업데이트 (denormalized corp_name)
-- ============================================

UPDATE rkyc_signal_index SET
    corp_name = '삼성전자',
    last_updated_at = NOW()
WHERE corp_id = '4301-3456789';

UPDATE rkyc_signal_index SET
    corp_name = '휴림로봇',
    last_updated_at = NOW()
WHERE corp_id = '6701-4567890';

-- ============================================
-- 3. rkyc_internal_snapshot 테이블 업데이트 (snapshot_json 내 기업 정보)
-- ============================================

-- 4301-3456789: 삼성전자
UPDATE rkyc_internal_snapshot SET
    snapshot_json = jsonb_set(
        jsonb_set(
            jsonb_set(
                snapshot_json,
                '{corp,corp_name}',
                '"삼성전자"'
            ),
            '{corp,biz_no}',
            '"124-81-00998"'
        ),
        '{corp,ceo_name}',
        '"전영현"'
    )
WHERE corp_id = '4301-3456789';

-- 6201-2345678: 광주정밀기계
UPDATE rkyc_internal_snapshot SET
    snapshot_json = jsonb_set(
        jsonb_set(
            snapshot_json,
            '{corp,biz_no}',
            '"415-02-96323"'
        ),
        '{corp,ceo_name}',
        '"강성우"'
    )
WHERE corp_id = '6201-2345678';

-- 4028-1234567: 전북식품
UPDATE rkyc_internal_snapshot SET
    snapshot_json = jsonb_set(
        jsonb_set(
            snapshot_json,
            '{corp,biz_no}',
            '"418-01-55362"'
        ),
        '{corp,ceo_name}',
        '"강동구"'
    )
WHERE corp_id = '4028-1234567';

-- 6701-4567890: 휴림로봇
UPDATE rkyc_internal_snapshot SET
    snapshot_json = jsonb_set(
        jsonb_set(
            jsonb_set(
                snapshot_json,
                '{corp,corp_name}',
                '"휴림로봇"'
            ),
            '{corp,biz_no}',
            '"109-81-60401"'
        ),
        '{corp,ceo_name}',
        '"김봉관"'
    )
WHERE corp_id = '6701-4567890';

-- 8000-7647330: 동부건설
UPDATE rkyc_internal_snapshot SET
    snapshot_json = jsonb_set(
        jsonb_set(
            snapshot_json,
            '{corp,biz_no}',
            '"824-87-03495"'
        ),
        '{corp,ceo_name}',
        '"윤진오"'
    )
WHERE corp_id = '8000-7647330';

-- 8001-3719240: 엠케이전자
UPDATE rkyc_internal_snapshot SET
    snapshot_json = jsonb_set(
        jsonb_set(
            snapshot_json,
            '{corp,biz_no}',
            '"135-81-06406"'
        ),
        '{corp,ceo_name}',
        '"현기진"'
    )
WHERE corp_id = '8001-3719240';

-- ============================================
-- 4. rkyc_corp_profile 테이블 업데이트 (존재하는 경우)
-- ============================================

UPDATE rkyc_corp_profile SET
    updated_at = NOW()
WHERE corp_id IN ('4301-3456789', '6201-2345678', '4028-1234567', '6701-4567890', '8000-7647330', '8001-3719240');

-- ============================================
-- 5. rkyc_dashboard_summary 업데이트
-- ============================================

UPDATE rkyc_dashboard_summary SET
    top_signals = '[
      {"corp_name": "동부건설", "event_type": "OVERDUE_FLAG_ON", "impact": "RISK/HIGH"},
      {"corp_name": "동부건설", "event_type": "INDUSTRY_SHOCK", "impact": "RISK/HIGH"},
      {"corp_name": "삼성전자", "event_type": "POLICY_REGULATION_CHANGE", "impact": "RISK/HIGH"}
    ]'::jsonb,
    generated_at = NOW();

COMMIT;

-- ============================================
-- 검증 쿼리 (데이터 애널리스트용)
-- ============================================

-- 1. corp 테이블 검증
-- SELECT corp_id, corp_name, biz_no, ceo_name, industry_code FROM corp ORDER BY corp_id;

-- 2. rkyc_signal_index corp_name 검증
-- SELECT DISTINCT corp_id, corp_name FROM rkyc_signal_index ORDER BY corp_id;

-- 3. rkyc_internal_snapshot JSON 내 기업정보 검증
-- SELECT
--     corp_id,
--     snapshot_json->'corp'->>'corp_name' as json_corp_name,
--     snapshot_json->'corp'->>'biz_no' as json_biz_no,
--     snapshot_json->'corp'->>'ceo_name' as json_ceo_name
-- FROM rkyc_internal_snapshot
-- ORDER BY corp_id;

-- 4. 전체 데이터 일관성 검증
-- SELECT
--     c.corp_id,
--     c.corp_name as corp_table_name,
--     si.corp_name as signal_index_name,
--     s.snapshot_json->'corp'->>'corp_name' as snapshot_json_name,
--     CASE
--         WHEN c.corp_name = si.corp_name AND c.corp_name = s.snapshot_json->'corp'->>'corp_name' THEN 'OK'
--         ELSE 'MISMATCH'
--     END as consistency_check
-- FROM corp c
-- LEFT JOIN (SELECT DISTINCT corp_id, corp_name FROM rkyc_signal_index) si ON c.corp_id = si.corp_id
-- LEFT JOIN rkyc_internal_snapshot s ON c.corp_id = s.corp_id
-- ORDER BY c.corp_id;
