-- ============================================
-- rKYC Migration v13: DART Corp Master 확장 필드
-- Purpose: 법인등록번호, 영문명, 결산월 추가
-- Date: 2026-02-08
-- ============================================
--
-- 이 마이그레이션은 다음을 수행합니다:
-- 1. corp 테이블에 DART 관련 확장 컬럼 추가
--    - jurir_no: 법인등록번호 (13자리)
--    - corp_name_eng: 영문 회사명
--    - acc_mt: 결산월 (MM)
-- 2. DART API에서 가져온 실제 데이터로 6개 기업 정보 업데이트
--
-- 중요: 이 데이터는 원천 데이터로, 시연 시 삭제 대상이 아닙니다.
-- ============================================

BEGIN;

-- ============================================
-- Step 1: corp 테이블에 확장 컬럼 추가
-- ============================================

-- 법인등록번호 (13자리, 하이픈 포함 시 14자리)
ALTER TABLE corp ADD COLUMN IF NOT EXISTS jurir_no VARCHAR(20);

-- 영문 회사명
ALTER TABLE corp ADD COLUMN IF NOT EXISTS corp_name_eng TEXT;

-- 결산월 (MM 형식, 예: 12 = 12월 결산)
ALTER TABLE corp ADD COLUMN IF NOT EXISTS acc_mt VARCHAR(2);

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_corp_jurir_no ON corp(jurir_no);

COMMENT ON COLUMN corp.jurir_no IS '법인등록번호 (13자리) - DART 공시 기준';
COMMENT ON COLUMN corp.corp_name_eng IS '영문 회사명 - DART 공시 기준';
COMMENT ON COLUMN corp.acc_mt IS '결산월 (MM) - DART 공시 기준';

-- ============================================
-- Step 2: DART에서 가져온 실제 데이터로 업데이트
-- 데이터 출처: 금융감독원 DART OpenAPI (2026-02-08 조회)
-- ============================================

-- 엠케이전자 (8001-3719240)
UPDATE corp SET
    jurir_no = '134511-0006704',
    corp_name_eng = 'MK ELECTRON CO.,LTD.',
    acc_mt = '12',
    dart_updated_at = NOW()
WHERE corp_id = '8001-3719240';

-- 동부건설 (8000-7647330)
UPDATE corp SET
    jurir_no = '110111-0015411',
    corp_name_eng = 'Dongbu Construction Co.,Ltd.',
    acc_mt = '12',
    dart_updated_at = NOW()
WHERE corp_id = '8000-7647330';

-- 전북식품 (4028-1234567)
-- 비상장사는 영문명이 없을 수 있음
UPDATE corp SET
    jurir_no = '180111-0595621',
    corp_name_eng = NULL,
    acc_mt = '12',
    dart_updated_at = NOW()
WHERE corp_id = '4028-1234567';

-- 광주정밀기계 (6201-2345678)
UPDATE corp SET
    jurir_no = '180111-0541953',
    corp_name_eng = NULL,
    acc_mt = '12',
    dart_updated_at = NOW()
WHERE corp_id = '6201-2345678';

-- 삼성전자 (4301-3456789)
UPDATE corp SET
    jurir_no = '130111-0006246',
    corp_name_eng = 'SAMSUNG ELECTRONICS CO.,LTD.',
    acc_mt = '12',
    dart_updated_at = NOW()
WHERE corp_id = '4301-3456789';

-- 휴림로봇 (6701-4567890)
UPDATE corp SET
    jurir_no = '161511-0019003',
    corp_name_eng = 'HUROBOT CO.,LTD.',
    acc_mt = '12',
    dart_updated_at = NOW()
WHERE corp_id = '6701-4567890';

-- ============================================
-- Step 3: 확인 쿼리
-- ============================================

SELECT
    corp_id,
    corp_name,
    jurir_no,
    corp_name_eng,
    acc_mt,
    dart_updated_at
FROM corp
ORDER BY corp_id;

COMMIT;

-- ============================================
-- 실행 완료 메시지
-- ============================================
--
-- 실행 방법:
-- 1. Supabase SQL Editor에서 이 스크립트 전체 실행
--
-- 실행 후 확인:
-- - 6개 기업 모두 jurir_no, corp_name_eng, acc_mt 업데이트됨
-- - dart_updated_at에 현재 시각 기록
--
-- 중요: 이 데이터는 원천 데이터입니다.
-- reset_demo_data.sql 실행 시에도 삭제되지 않습니다.
-- ============================================
