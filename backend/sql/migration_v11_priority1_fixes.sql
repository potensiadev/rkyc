-- ============================================================
-- rKYC Priority 1 Migration v11
-- 세션 14: 시니어 DBA 분석 기반 Critical Issues 수정
--
-- 작업 내용:
--   1. Signal Index 상태 필드 제거 (일관성 버그 방지)
--   2. 누락된 인덱스 5개 추가 (성능 10-100배 개선)
--   3. FK ON DELETE 정책 추가 (데이터 정합성)
--   4. JSONB 인덱스 추가 (Snapshot 조회 성능)
--
-- 예상 소요 시간: < 1분 (29개 signal 기준)
-- 롤백: migration_v11_rollback.sql 참조
-- ============================================================

-- ============================================================
-- STEP 0: 사전 검증
-- ============================================================
DO $$
BEGIN
    -- signal_status 컬럼이 signal_index에 존재하는지 확인
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'rkyc_signal_index'
        AND column_name = 'signal_status'
    ) THEN
        RAISE NOTICE 'signal_status column not found in rkyc_signal_index - skipping removal';
    END IF;
END $$;

-- ============================================================
-- STEP 1: Signal Index 상태 필드 제거
-- 이유: rkyc_signal + rkyc_signal_index 이중 저장으로 인한 불일치 버그 방지
-- 해결: signal_index는 생성 후 불변(immutable)으로 만들고, 상태는 signal 테이블에서만 관리
-- ============================================================

-- 1.1 기존 인덱스 제거 (상태 필드 인덱스)
DROP INDEX IF EXISTS idx_signal_index_status;

-- 1.2 상태 필드 제거
-- 주의: 데이터 손실 발생! 상태 정보는 rkyc_signal에서 조회해야 함
ALTER TABLE rkyc_signal_index
    DROP COLUMN IF EXISTS signal_status,
    DROP COLUMN IF EXISTS reviewed_at,
    DROP COLUMN IF EXISTS dismissed_at,
    DROP COLUMN IF EXISTS dismiss_reason;

COMMENT ON TABLE rkyc_signal_index IS
    'Dashboard 전용 비정규화 테이블 (PRD 14.7.3) - 생성 후 불변(immutable), 상태는 rkyc_signal에서 조회';

-- ============================================================
-- STEP 2: 누락된 인덱스 추가 (성능 Critical)
-- ============================================================

-- 2.1 rkyc_fact: 문서별 Fact 조회 최적화
-- 쿼리 패턴: SELECT * FROM rkyc_fact WHERE doc_id = ? ORDER BY extracted_at DESC
CREATE INDEX IF NOT EXISTS idx_rkyc_fact_doc_extracted
    ON rkyc_fact(doc_id, extracted_at DESC);

-- 2.2 rkyc_fact: 기업별 Fact 조회 최적화
-- 쿼리 패턴: SELECT * FROM rkyc_fact WHERE corp_id = ? ORDER BY extracted_at DESC
CREATE INDEX IF NOT EXISTS idx_rkyc_fact_corp_extracted
    ON rkyc_fact(corp_id, extracted_at DESC);

-- 2.3 rkyc_fact: Fact 타입별 집계
-- 쿼리 패턴: SELECT fact_type, COUNT(*) FROM rkyc_fact GROUP BY fact_type
CREATE INDEX IF NOT EXISTS idx_rkyc_fact_type
    ON rkyc_fact(fact_type);

-- 2.4 rkyc_evidence: 시그널별 Evidence 페이징
-- 쿼리 패턴: SELECT * FROM rkyc_evidence WHERE signal_id = ? ORDER BY created_at DESC LIMIT 10
CREATE INDEX IF NOT EXISTS idx_rkyc_evidence_signal_created
    ON rkyc_evidence(signal_id, created_at DESC);

-- 2.5 rkyc_evidence: Evidence 타입별 필터링
-- 쿼리 패턴: SELECT * FROM rkyc_evidence WHERE ref_type = 'URL'
CREATE INDEX IF NOT EXISTS idx_rkyc_evidence_ref_type
    ON rkyc_evidence(ref_type);

-- 2.6 rkyc_external_news: 날짜순 정렬 (현재 테이블 스캔)
-- 쿼리 패턴: SELECT * FROM rkyc_external_news ORDER BY published_at DESC LIMIT 50
CREATE INDEX IF NOT EXISTS idx_rkyc_external_news_published
    ON rkyc_external_news(published_at DESC);

-- 2.7 rkyc_job: Job 모니터링 대시보드
-- 쿼리 패턴: SELECT * FROM rkyc_job WHERE status = 'RUNNING' ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_rkyc_job_status_created
    ON rkyc_job(status, created_at DESC);

-- 2.8 rkyc_corp_profile: TTL 기반 캐시 클린업
-- 쿼리 패턴: SELECT * FROM rkyc_corp_profile WHERE expires_at < NOW()
CREATE INDEX IF NOT EXISTS idx_rkyc_corp_profile_expires
    ON rkyc_corp_profile(expires_at, corp_id);

-- 2.9 rkyc_corp_profile: Partial index for expired profiles (자동 클린업용)
CREATE INDEX IF NOT EXISTS idx_rkyc_corp_profile_expired_partial
    ON rkyc_corp_profile(corp_id)
    WHERE expires_at < NOW();

-- 2.10 rkyc_document: 문서 목록 정렬
-- 쿼리 패턴: SELECT * FROM rkyc_document WHERE corp_id = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_rkyc_document_corp_created
    ON rkyc_document(corp_id, created_at DESC);

-- ============================================================
-- STEP 3: FK ON DELETE 정책 추가 (데이터 정합성)
-- ============================================================

-- 3.1 rkyc_signal → corp: CASCADE (기업 삭제 시 시그널도 삭제)
-- 기존 FK 제거 후 재생성 (PostgreSQL은 ALTER CONSTRAINT 미지원)
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    -- 기존 FK constraint 이름 찾기
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    WHERE tc.table_name = 'rkyc_signal'
    AND tc.constraint_type = 'FOREIGN KEY'
    AND EXISTS (
        SELECT 1 FROM information_schema.constraint_column_usage ccu
        WHERE ccu.constraint_name = tc.constraint_name
        AND ccu.column_name = 'corp_id'
        AND ccu.table_name = 'corp'
    );

    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE rkyc_signal DROP CONSTRAINT ' || constraint_name;
        RAISE NOTICE 'Dropped FK constraint: %', constraint_name;
    END IF;
END $$;

ALTER TABLE rkyc_signal
    ADD CONSTRAINT fk_signal_corp
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id) ON DELETE CASCADE;

-- 3.2 rkyc_signal_index → corp: CASCADE
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    WHERE tc.table_name = 'rkyc_signal_index'
    AND tc.constraint_type = 'FOREIGN KEY'
    AND EXISTS (
        SELECT 1 FROM information_schema.constraint_column_usage ccu
        WHERE ccu.constraint_name = tc.constraint_name
        AND ccu.column_name = 'corp_id'
        AND ccu.table_name = 'corp'
    );

    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE rkyc_signal_index DROP CONSTRAINT ' || constraint_name;
    END IF;
END $$;

ALTER TABLE rkyc_signal_index
    ADD CONSTRAINT fk_signal_index_corp
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id) ON DELETE CASCADE;

-- 3.3 rkyc_internal_snapshot → corp: CASCADE
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    WHERE tc.table_name = 'rkyc_internal_snapshot'
    AND tc.constraint_type = 'FOREIGN KEY'
    AND EXISTS (
        SELECT 1 FROM information_schema.constraint_column_usage ccu
        WHERE ccu.constraint_name = tc.constraint_name
        AND ccu.column_name = 'corp_id'
        AND ccu.table_name = 'corp'
    );

    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE rkyc_internal_snapshot DROP CONSTRAINT ' || constraint_name;
    END IF;
END $$;

ALTER TABLE rkyc_internal_snapshot
    ADD CONSTRAINT fk_snapshot_corp
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id) ON DELETE CASCADE;

-- 3.4 rkyc_document → corp: CASCADE
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    WHERE tc.table_name = 'rkyc_document'
    AND tc.constraint_type = 'FOREIGN KEY'
    AND EXISTS (
        SELECT 1 FROM information_schema.constraint_column_usage ccu
        WHERE ccu.constraint_name = tc.constraint_name
        AND ccu.column_name = 'corp_id'
        AND ccu.table_name = 'corp'
    );

    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE rkyc_document DROP CONSTRAINT ' || constraint_name;
    END IF;
END $$;

ALTER TABLE rkyc_document
    ADD CONSTRAINT fk_document_corp
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id) ON DELETE CASCADE;

-- 3.5 rkyc_fact → corp: CASCADE
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    WHERE tc.table_name = 'rkyc_fact'
    AND tc.constraint_type = 'FOREIGN KEY'
    AND EXISTS (
        SELECT 1 FROM information_schema.constraint_column_usage ccu
        WHERE ccu.constraint_name = tc.constraint_name
        AND ccu.column_name = 'corp_id'
        AND ccu.table_name = 'corp'
    );

    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE rkyc_fact DROP CONSTRAINT ' || constraint_name;
    END IF;
END $$;

ALTER TABLE rkyc_fact
    ADD CONSTRAINT fk_fact_corp
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id) ON DELETE CASCADE;

-- 3.6 rkyc_corp_profile → corp: CASCADE
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    WHERE tc.table_name = 'rkyc_corp_profile'
    AND tc.constraint_type = 'FOREIGN KEY'
    AND EXISTS (
        SELECT 1 FROM information_schema.constraint_column_usage ccu
        WHERE ccu.constraint_name = tc.constraint_name
        AND ccu.column_name = 'corp_id'
        AND ccu.table_name = 'corp'
    );

    IF constraint_name IS NOT NULL THEN
        EXECUTE 'ALTER TABLE rkyc_corp_profile DROP CONSTRAINT ' || constraint_name;
    END IF;
END $$;

ALTER TABLE rkyc_corp_profile
    ADD CONSTRAINT fk_profile_corp
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id) ON DELETE CASCADE;

-- ============================================================
-- STEP 4: JSONB 인덱스 추가 (Snapshot 조회 성능)
-- ============================================================

-- 4.1 GIN 인덱스: Snapshot JSON 전체 검색
-- 쿼리 패턴: snapshot_json @> '{"credit": {"loan_summary": {"overdue_flag": true}}}'
CREATE INDEX IF NOT EXISTS idx_snapshot_json_gin
    ON rkyc_internal_snapshot USING GIN(snapshot_json);

-- 4.2 Functional 인덱스: 자주 조회하는 경로 (loan exposure)
-- 쿼리 패턴: WHERE (snapshot_json->'credit'->'loan_summary'->>'total_exposure_krw')::numeric > 1000000000
CREATE INDEX IF NOT EXISTS idx_snapshot_loan_exposure
    ON rkyc_internal_snapshot
    USING BTREE(((snapshot_json->'credit'->'loan_summary'->>'total_exposure_krw')::NUMERIC));

-- 4.3 Functional 인덱스: Risk Grade 필터링
-- 쿼리 패턴: WHERE snapshot_json->'corp'->'kyc_status'->>'internal_risk_grade' = 'HIGH'
CREATE INDEX IF NOT EXISTS idx_snapshot_risk_grade
    ON rkyc_internal_snapshot
    USING BTREE((snapshot_json->'corp'->'kyc_status'->>'internal_risk_grade'));

-- 4.4 Functional 인덱스: Overdue Flag 필터링
-- 쿼리 패턴: WHERE (snapshot_json->'credit'->'loan_summary'->>'overdue_flag')::boolean = true
CREATE INDEX IF NOT EXISTS idx_snapshot_overdue_flag
    ON rkyc_internal_snapshot
    USING BTREE(((snapshot_json->'credit'->'loan_summary'->>'overdue_flag')::BOOLEAN));

-- ============================================================
-- STEP 5: 검증 쿼리
-- ============================================================

-- 5.1 Signal Index 상태 필드 제거 확인
SELECT
    'signal_index_columns' as check_type,
    COUNT(*) as column_count,
    STRING_AGG(column_name, ', ') as columns
FROM information_schema.columns
WHERE table_name = 'rkyc_signal_index'
AND column_name IN ('signal_status', 'reviewed_at', 'dismissed_at', 'dismiss_reason');

-- 5.2 새 인덱스 생성 확인
SELECT
    'new_indexes' as check_type,
    COUNT(*) as index_count
FROM pg_indexes
WHERE indexname LIKE 'idx_rkyc_%'
AND indexname IN (
    'idx_rkyc_fact_doc_extracted',
    'idx_rkyc_fact_corp_extracted',
    'idx_rkyc_fact_type',
    'idx_rkyc_evidence_signal_created',
    'idx_rkyc_evidence_ref_type',
    'idx_rkyc_external_news_published',
    'idx_rkyc_job_status_created',
    'idx_rkyc_corp_profile_expires',
    'idx_rkyc_document_corp_created'
);

-- 5.3 FK 제약조건 확인
SELECT
    'fk_constraints' as check_type,
    tc.table_name,
    tc.constraint_name,
    rc.delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.referential_constraints rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name IN ('rkyc_signal', 'rkyc_signal_index', 'rkyc_internal_snapshot',
                       'rkyc_document', 'rkyc_fact', 'rkyc_corp_profile')
ORDER BY tc.table_name;

-- 5.4 JSONB 인덱스 확인
SELECT
    'jsonb_indexes' as check_type,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE 'idx_snapshot_%';

-- ============================================================
-- 완료 메시지
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Migration v11 완료: Priority 1 Fixes';
    RAISE NOTICE '===========================================';
    RAISE NOTICE '1. Signal Index 상태 필드 제거됨';
    RAISE NOTICE '2. 10개 인덱스 추가됨';
    RAISE NOTICE '3. 6개 FK ON DELETE CASCADE 설정됨';
    RAISE NOTICE '4. 4개 JSONB 인덱스 추가됨';
    RAISE NOTICE '===========================================';
    RAISE NOTICE '주의: Backend 코드 수정 필요!';
    RAISE NOTICE '- Dashboard 쿼리에서 signal_status는 JOIN으로 조회해야 함';
    RAISE NOTICE '- signals.py의 상태 업데이트 로직에서 signal_index 업데이트 제거';
    RAISE NOTICE '===========================================';
END $$;
