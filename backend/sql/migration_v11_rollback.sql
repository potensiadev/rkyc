-- ============================================================
-- rKYC Priority 1 Migration v11 - ROLLBACK
-- 주의: 이 스크립트는 마이그레이션을 되돌립니다.
-- ============================================================

-- ============================================================
-- STEP 1: Signal Index 상태 필드 복원
-- 주의: 데이터는 복원되지 않음! rkyc_signal에서 SYNC 필요
-- ============================================================

ALTER TABLE rkyc_signal_index
    ADD COLUMN IF NOT EXISTS signal_status signal_status_enum DEFAULT 'NEW',
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS dismissed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS dismiss_reason TEXT;

-- rkyc_signal에서 상태 동기화
UPDATE rkyc_signal_index si
SET
    signal_status = s.signal_status,
    reviewed_at = s.reviewed_at,
    dismissed_at = s.dismissed_at,
    dismiss_reason = s.dismiss_reason
FROM rkyc_signal s
WHERE si.signal_id = s.signal_id;

-- 상태 인덱스 복원
CREATE INDEX IF NOT EXISTS idx_signal_index_status ON rkyc_signal_index(signal_status);

-- ============================================================
-- STEP 2: 추가된 인덱스 제거
-- ============================================================

DROP INDEX IF EXISTS idx_rkyc_fact_doc_extracted;
DROP INDEX IF EXISTS idx_rkyc_fact_corp_extracted;
DROP INDEX IF EXISTS idx_rkyc_fact_type;
DROP INDEX IF EXISTS idx_rkyc_evidence_signal_created;
DROP INDEX IF EXISTS idx_rkyc_evidence_ref_type;
DROP INDEX IF EXISTS idx_rkyc_external_news_published;
DROP INDEX IF EXISTS idx_rkyc_job_status_created;
DROP INDEX IF EXISTS idx_rkyc_corp_profile_expires;
DROP INDEX IF EXISTS idx_rkyc_corp_profile_expired_partial;
DROP INDEX IF EXISTS idx_rkyc_document_corp_created;

-- ============================================================
-- STEP 3: FK 제약조건 복원 (ON DELETE CASCADE 제거)
-- 주의: 원래 제약조건 이름이 다를 수 있음
-- ============================================================

-- 3.1 rkyc_signal
ALTER TABLE rkyc_signal DROP CONSTRAINT IF EXISTS fk_signal_corp;
ALTER TABLE rkyc_signal
    ADD CONSTRAINT rkyc_signal_corp_id_fkey
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id);

-- 3.2 rkyc_signal_index
ALTER TABLE rkyc_signal_index DROP CONSTRAINT IF EXISTS fk_signal_index_corp;
ALTER TABLE rkyc_signal_index
    ADD CONSTRAINT rkyc_signal_index_corp_id_fkey
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id);

-- 3.3 rkyc_internal_snapshot
ALTER TABLE rkyc_internal_snapshot DROP CONSTRAINT IF EXISTS fk_snapshot_corp;
ALTER TABLE rkyc_internal_snapshot
    ADD CONSTRAINT rkyc_internal_snapshot_corp_id_fkey
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id);

-- 3.4 rkyc_document
ALTER TABLE rkyc_document DROP CONSTRAINT IF EXISTS fk_document_corp;
ALTER TABLE rkyc_document
    ADD CONSTRAINT rkyc_document_corp_id_fkey
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id);

-- 3.5 rkyc_fact
ALTER TABLE rkyc_fact DROP CONSTRAINT IF EXISTS fk_fact_corp;
ALTER TABLE rkyc_fact
    ADD CONSTRAINT rkyc_fact_corp_id_fkey
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id);

-- 3.6 rkyc_corp_profile
ALTER TABLE rkyc_corp_profile DROP CONSTRAINT IF EXISTS fk_profile_corp;
ALTER TABLE rkyc_corp_profile
    ADD CONSTRAINT rkyc_corp_profile_corp_id_fkey
    FOREIGN KEY (corp_id) REFERENCES corp(corp_id);

-- ============================================================
-- STEP 4: JSONB 인덱스 제거
-- ============================================================

DROP INDEX IF EXISTS idx_snapshot_json_gin;
DROP INDEX IF EXISTS idx_snapshot_loan_exposure;
DROP INDEX IF EXISTS idx_snapshot_risk_grade;
DROP INDEX IF EXISTS idx_snapshot_overdue_flag;

-- ============================================================
-- 완료
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE 'Rollback v11 완료';
    RAISE NOTICE '주의: Backend 코드도 원래대로 복원해야 합니다!';
END $$;
