-- ============================================
-- Migration v10: Fix Industry Code Mapping
-- 사업자등록증 기준 industry_code 수정
-- ============================================

-- 1. industry_master에 새로운 업종 코드 추가
INSERT INTO industry_master (industry_code, industry_name, industry_group, is_sensitive, tags) VALUES
('G47', '소매업', 'WHOLESALE', FALSE, ARRAY['retail', 'consumer', 'distribution'])
ON CONFLICT (industry_code) DO NOTHING;

-- 2. corp 테이블 industry_code 수정 (사업자등록증 기준)

-- 삼성전자: C21 (의약품 제조업) → C26 (전자부품 제조업)
-- 사업자등록증: 전자, 전기, 통신기계기구외
UPDATE corp SET
    industry_code = 'C26',
    updated_at = NOW()
WHERE corp_id = '4301-3456789' AND industry_code = 'C21';

-- 전북식품: C10 (식품 제조업) → G47 (소매업)
-- 사업자등록증: 기타 식료품 소매업 (도매 및 소매업)
UPDATE corp SET
    industry_code = 'G47',
    updated_at = NOW()
WHERE corp_id = '4028-1234567' AND industry_code = 'C10';

-- 휴림로봇: D35 (전기/가스 공급업) → C29 (기계장비 제조업)
-- 사업자등록증: 산업용 로봇 제조업
UPDATE corp SET
    industry_code = 'C29',
    updated_at = NOW()
WHERE corp_id = '6701-4567890' AND industry_code = 'D35';

-- 3. rkyc_signal_index도 동기화 (denormalized 테이블)
UPDATE rkyc_signal_index SET
    industry_code = 'C26'
WHERE corp_id = '4301-3456789';

UPDATE rkyc_signal_index SET
    industry_code = 'G47'
WHERE corp_id = '4028-1234567';

UPDATE rkyc_signal_index SET
    industry_code = 'C29'
WHERE corp_id = '6701-4567890';

-- 4. 검증 쿼리
SELECT
    c.corp_id,
    c.corp_name,
    c.industry_code,
    im.industry_name,
    c.biz_type,
    c.biz_item
FROM corp c
LEFT JOIN industry_master im ON c.industry_code = im.industry_code
ORDER BY c.corp_id;

-- 5. industry_master 전체 목록
SELECT * FROM industry_master ORDER BY industry_code;
