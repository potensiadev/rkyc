-- ============================================
-- rKYC Migration v12: DART 기반 Corp 마스터 데이터 확장
-- Purpose: DART 공시 기반 100% Fact 데이터로 기업 마스터 업데이트
-- Date: 2026-02-08
-- ============================================
--
-- 이 마이그레이션은 다음을 수행합니다:
-- 1. corp 테이블에 DART 관련 컬럼 추가
-- 2. DART API에서 가져온 실제 데이터로 6개 기업 정보 업데이트
--
-- 중요: 이 데이터는 원천 데이터로, 시연 시 삭제 대상이 아닙니다.
-- ============================================

BEGIN;

-- ============================================
-- Step 1: corp 테이블에 DART 관련 컬럼 추가
-- ============================================

-- DART 고유번호 (8자리)
ALTER TABLE corp ADD COLUMN IF NOT EXISTS dart_corp_code VARCHAR(8);

-- 설립일 (YYYYMMDD 형식)
ALTER TABLE corp ADD COLUMN IF NOT EXISTS established_date VARCHAR(8);

-- 본사 주소
ALTER TABLE corp ADD COLUMN IF NOT EXISTS headquarters TEXT;

-- 법인 구분 (Y:유가, K:코스닥, N:코넥스, E:기타)
ALTER TABLE corp ADD COLUMN IF NOT EXISTS corp_class VARCHAR(1);

-- 홈페이지 URL
ALTER TABLE corp ADD COLUMN IF NOT EXISTS homepage_url TEXT;

-- DART 데이터 최종 갱신일
ALTER TABLE corp ADD COLUMN IF NOT EXISTS dart_updated_at TIMESTAMPTZ;

-- 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_corp_dart_code ON corp(dart_corp_code);

COMMENT ON COLUMN corp.dart_corp_code IS 'DART 고유번호 (8자리) - 금융감독원 전자공시시스템';
COMMENT ON COLUMN corp.established_date IS '설립일 (YYYYMMDD) - DART 공시 기준';
COMMENT ON COLUMN corp.headquarters IS '본사 주소 - DART 공시 기준';
COMMENT ON COLUMN corp.corp_class IS '법인 구분 (Y:유가, K:코스닥, N:코넥스, E:기타)';
COMMENT ON COLUMN corp.homepage_url IS '회사 홈페이지 URL';
COMMENT ON COLUMN corp.dart_updated_at IS 'DART 데이터 최종 갱신 시각';

-- ============================================
-- Step 2: DART에서 가져온 실제 데이터로 업데이트
-- 데이터 출처: 금융감독원 DART OpenAPI (2026-02-08 조회)
-- ============================================

-- 엠케이전자 (8001-3719240)
UPDATE corp SET
    ceo_name = '현기진',
    biz_no = '135-81-06406',
    dart_corp_code = '00121686',
    established_date = '19821216',
    headquarters = '경기도 화성시 처인구 이동면 덕성산단6로 405 엠케이전자',
    corp_class = 'K',  -- 코스닥
    dart_updated_at = NOW()
WHERE corp_id = '8001-3719240';

-- 동부건설 (8000-7647330)
UPDATE corp SET
    ceo_name = '윤진오',
    biz_no = '201-81-45685',
    dart_corp_code = '00115612',
    established_date = '19690124',
    headquarters = '서울특별시 강동구 올림픽로 137 자이타워 타워동',
    corp_class = 'Y',  -- 유가증권
    dart_updated_at = NOW()
WHERE corp_id = '8000-7647330';

-- 전북식품 (4028-1234567)
UPDATE corp SET
    ceo_name = '유치권',
    biz_no = '515-86-01179',
    dart_corp_code = '01582343',
    established_date = '20180401',
    headquarters = '대구광역시 달서구 월배로 289 (상인동) 신한빌딩 3층',
    corp_class = 'E',  -- 기타
    dart_updated_at = NOW()
WHERE corp_id = '4028-1234567';

-- 광주정밀기계 (6201-2345678)
UPDATE corp SET
    ceo_name = '강성우',
    biz_no = '565-87-00847',
    dart_corp_code = '01329717',
    established_date = '20170728',
    headquarters = '대구광역시 달서구 성서로 32 (갈산동, 성서하이테크밸리)',
    corp_class = 'E',  -- 기타
    dart_updated_at = NOW()
WHERE corp_id = '6201-2345678';

-- 삼성전자 (4301-3456789)
UPDATE corp SET
    ceo_name = '전영현, 한종희',
    biz_no = '124-81-00998',
    dart_corp_code = '00126380',
    established_date = '19690113',
    headquarters = '경기도 수원시 영통구 삼성로 129 (매탄동)',
    corp_class = 'Y',  -- 유가증권
    dart_updated_at = NOW()
WHERE corp_id = '4301-3456789';

-- 휴림로봇 (6701-4567890)
UPDATE corp SET
    ceo_name = '김봉관',
    biz_no = '109-81-60401',
    dart_corp_code = '00540429',
    established_date = '19981129',
    headquarters = '충청남도 천안시 동남구 병천면 충절로 4번길 27',
    corp_class = 'K',  -- 코스닥
    dart_updated_at = NOW()
WHERE corp_id = '6701-4567890';

-- ============================================
-- Step 3: 확인 쿼리
-- ============================================

SELECT
    corp_id,
    corp_name,
    ceo_name,
    dart_corp_code,
    established_date,
    corp_class,
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
-- - 6개 기업 모두 dart_corp_code, established_date 등 업데이트됨
-- - dart_updated_at에 현재 시각 기록
--
-- 중요: 이 데이터는 원천 데이터입니다.
-- reset_demo_data.sql 실행 시에도 삭제되지 않습니다.
-- ============================================
