-- ============================================================
-- rKYC Signal Status Migration v3
-- Session 5: Signal 상태 관리 컬럼 추가
-- ============================================================

-- 1. Signal Status ENUM 생성
-- NEW: 신규 시그널 (기본값)
-- REVIEWED: 검토 완료
-- DISMISSED: 기각됨
CREATE TYPE signal_status_enum AS ENUM ('NEW', 'REVIEWED', 'DISMISSED');

-- 2. rkyc_signal 테이블에 상태 관리 컬럼 추가
ALTER TABLE rkyc_signal
ADD COLUMN signal_status signal_status_enum DEFAULT 'NEW',
ADD COLUMN reviewed_at TIMESTAMPTZ,
ADD COLUMN dismissed_at TIMESTAMPTZ,
ADD COLUMN dismiss_reason TEXT;

-- 기존 데이터 NEW로 설정
UPDATE rkyc_signal SET signal_status = 'NEW' WHERE signal_status IS NULL;

-- 3. rkyc_signal_index 테이블에 상태 관리 컬럼 추가 (Denormalized)
ALTER TABLE rkyc_signal_index
ADD COLUMN signal_status signal_status_enum DEFAULT 'NEW',
ADD COLUMN reviewed_at TIMESTAMPTZ,
ADD COLUMN dismissed_at TIMESTAMPTZ,
ADD COLUMN dismiss_reason TEXT;

-- 기존 데이터 NEW로 설정
UPDATE rkyc_signal_index SET signal_status = 'NEW' WHERE signal_status IS NULL;

-- 4. 인덱스 추가 (필터링 성능 향상)
CREATE INDEX idx_signal_status ON rkyc_signal(signal_status);
CREATE INDEX idx_signal_index_status ON rkyc_signal_index(signal_status);

-- 5. 검증 쿼리
SELECT
    'rkyc_signal' as table_name,
    COUNT(*) as total,
    COUNT(CASE WHEN signal_status = 'NEW' THEN 1 END) as new_count
FROM rkyc_signal
UNION ALL
SELECT
    'rkyc_signal_index' as table_name,
    COUNT(*) as total,
    COUNT(CASE WHEN signal_status = 'NEW' THEN 1 END) as new_count
FROM rkyc_signal_index;
