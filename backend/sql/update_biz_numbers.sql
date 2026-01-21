-- 사업자등록번호(biz_no) 및 법인등록번호(corp_reg_no) 업데이트
-- 실행일: 2026-01-21

-- 삼성전자
UPDATE corp SET
    biz_no = '124-81-00998',
    corp_reg_no = '124-81-00998'
WHERE corp_id = '4301-3456789';

-- 휴림로봇
UPDATE corp SET
    biz_no = '109-81-60401'
WHERE corp_id = '6701-4567890';

-- 전북식품
UPDATE corp SET
    biz_no = '418-01-55362'
WHERE corp_id = '4028-1234567';

-- 동부건설
UPDATE corp SET
    biz_no = '201-81-45685'
WHERE corp_id = '8000-7647330';

-- 엠케이전자
UPDATE corp SET
    biz_no = '135-81-06406'
WHERE corp_id = '8001-3719240';

-- 광주정밀기계
UPDATE corp SET
    biz_no = '409-16-79710'
WHERE corp_id = '6201-2345678';

-- 업데이트 확인
SELECT corp_id, corp_name, biz_no, corp_reg_no
FROM corp
ORDER BY corp_name;
