-- Migration v16: Fix corp_name to DART official names
-- Problem: corp_name has "(주)" suffix which causes DART API matching issues
-- Solution: Update to DART official names (without legal suffixes)

-- 엠케이전자(주) → 엠케이전자
UPDATE corp
SET corp_name = '엠케이전자',
    updated_at = NOW()
WHERE corp_id = '8001-3719240';

-- 동부건설(주) → 동부건설
UPDATE corp
SET corp_name = '동부건설',
    updated_at = NOW()
WHERE corp_id = '8000-7647330';

-- 삼성전자(주) → 삼성전자
UPDATE corp
SET corp_name = '삼성전자',
    updated_at = NOW()
WHERE corp_id = '4301-3456789';

-- 휴림로봇(주) → 휴림로봇
UPDATE corp
SET corp_name = '휴림로봇',
    updated_at = NOW()
WHERE corp_id = '6701-4567890';

-- Verify the changes
SELECT corp_id, corp_name, dart_corp_code FROM corp ORDER BY corp_id;
