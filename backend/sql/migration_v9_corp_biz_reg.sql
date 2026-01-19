-- ============================================
-- Migration v9: Corp Table Extension from Business Registration
-- 사업자등록증 정보 기반 corp 테이블 확장
-- ============================================

-- 0. corp_reg_no NOT NULL 제약 제거 (개인사업자는 법인등록번호 없음)
ALTER TABLE corp ALTER COLUMN corp_reg_no DROP NOT NULL;

-- 1. corp 테이블에 새 컬럼 추가
ALTER TABLE corp ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE corp ADD COLUMN IF NOT EXISTS hq_address TEXT;
ALTER TABLE corp ADD COLUMN IF NOT EXISTS founded_date DATE;
ALTER TABLE corp ADD COLUMN IF NOT EXISTS biz_type VARCHAR(100);  -- 업태
ALTER TABLE corp ADD COLUMN IF NOT EXISTS biz_item TEXT;          -- 종목
ALTER TABLE corp ADD COLUMN IF NOT EXISTS is_corporation BOOLEAN DEFAULT TRUE;  -- 법인/개인 구분

COMMENT ON COLUMN corp.address IS '사업장 소재지';
COMMENT ON COLUMN corp.hq_address IS '본점 소재지 (법인만)';
COMMENT ON COLUMN corp.founded_date IS '개업 연월일';
COMMENT ON COLUMN corp.biz_type IS '업태 (제조업, 건설업 등)';
COMMENT ON COLUMN corp.biz_item IS '종목 (상세 업종)';
COMMENT ON COLUMN corp.is_corporation IS '법인사업자 여부 (true=법인, false=개인)';

-- 2. 사업자등록증 기반 데이터 업데이트

-- 엠케이전자 (법인)
UPDATE corp SET
    address = '경기도 용인시 처인구 이동읍 백옥대로 765',
    hq_address = '경기도 용인시 처인구 이동읍 백옥대로 765',
    founded_date = '1982-12-16',
    biz_type = '제조업',
    biz_item = '기타 반도체 소자 제조업',
    is_corporation = TRUE,
    updated_at = NOW()
WHERE corp_id = '8001-3719240';

-- 동부건설 (법인)
UPDATE corp SET
    address = '서울특별시 종로구 율곡로 75, 동부빌딩',
    hq_address = '서울특별시 종로구 율곡로 75, 동부빌딩',
    founded_date = '1969-01-24',
    biz_type = '건설업',
    biz_item = '토목건축공사업, 산업설비공사업',
    is_corporation = TRUE,
    updated_at = NOW()
WHERE corp_id = '8000-7647330';

-- 전북식품 (개인)
UPDATE corp SET
    address = '전북특별자치도 전주시 덕진구 팔복로 423',
    hq_address = NULL,
    founded_date = '1997-09-01',
    biz_type = '도매 및 소매업',
    biz_item = '기타 식료품 소매업',
    is_corporation = FALSE,
    corp_reg_no = NULL,  -- 개인사업자는 법인등록번호 없음
    updated_at = NOW()
WHERE corp_id = '4028-1234567';

-- 광주정밀기계 (개인)
UPDATE corp SET
    address = '광주광역시 광산구 평동산단로 143번길 25',
    hq_address = NULL,
    founded_date = '1992-03-07',
    biz_type = '제조업',
    biz_item = '그 외 금속파스너 및 나사제품 제조업',
    is_corporation = FALSE,
    corp_reg_no = NULL,  -- 개인사업자는 법인등록번호 없음
    updated_at = NOW()
WHERE corp_id = '6201-2345678';

-- 삼성전자 (법인)
UPDATE corp SET
    address = '경기도 수원시 영통구 삼성로 129',
    hq_address = '경기도 수원시 영통구 삼성로 129',
    founded_date = '1969-12-01',
    biz_type = '제조업',
    biz_item = '전자, 전기, 통신기계기구외',
    is_corporation = TRUE,
    updated_at = NOW()
WHERE corp_id = '4301-3456789';

-- 휴림로봇 (법인)
UPDATE corp SET
    address = '경기도 화성시 동탄기흥로 590, 로봇산업단지 A동 301호',
    hq_address = '경기도 화성시 동탄기흥로 590, 로봇산업단지 A동 301호',
    founded_date = '2018-03-15',
    biz_type = '제조업, 서비스업',
    biz_item = '산업용 로봇 제조업, 지능형 로봇 외',
    is_corporation = TRUE,
    updated_at = NOW()
WHERE corp_id = '6701-4567890';

-- 3. 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_corp_founded_date ON corp(founded_date);
CREATE INDEX IF NOT EXISTS idx_corp_is_corporation ON corp(is_corporation);

-- 4. 검증 쿼리
SELECT
    corp_id,
    corp_name,
    biz_no,
    corp_reg_no,
    ceo_name,
    address,
    founded_date,
    biz_type,
    biz_item,
    is_corporation
FROM corp
ORDER BY corp_id;
