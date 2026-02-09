-- ============================================================
-- rKYC Migration v14: Signal 트리거 수정
-- 문제: update_signal_updated_at 트리거가 updated_at 컬럼을 찾지만
--       실제 테이블에는 last_updated_at 컬럼만 존재
-- 해결: 트리거 삭제 (수동 업데이트로 전환)
-- ============================================================

-- 1. rkyc_signal 테이블의 트리거 삭제
DROP TRIGGER IF EXISTS update_signal_updated_at ON rkyc_signal;

-- 2. rkyc_signal_index 테이블의 트리거도 삭제 (동일 문제)
DROP TRIGGER IF EXISTS update_signal_index_updated_at ON rkyc_signal_index;

-- 3. 검증
DO $$
BEGIN
    RAISE NOTICE 'Migration v14 완료: signal 관련 트리거 삭제됨';
END $$;
