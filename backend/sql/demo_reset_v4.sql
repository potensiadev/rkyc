-- ============================================
-- rKYC Demo Data Reset Script (v4)
-- Purpose: 해커톤 시연을 위한 데이터 초기화
-- Date: 2026-02-08
-- Updated: 실제 존재하는 테이블만 포함 (v8 enrichment 제외)
-- ============================================
--
-- 시연 시나리오: 빈 화면 시작
-- - 모든 분석 결과 삭제
-- - 시연 중 분석 실행하여 시그널 생성 과정 시연
--
-- 보존 대상 (원천 데이터 - 절대 삭제 금지):
--   - corp (6개 기업 + DART 필드)
--   - rkyc_internal_snapshot (내부 스냅샷)
--   - rkyc_internal_snapshot_latest (최신 포인터)
--   - industry_master (업종 마스터)
--
-- 삭제 대상 (분석 결과 데이터):
--   - 시그널: rkyc_signal, rkyc_signal_index, rkyc_evidence, rkyc_signal_embedding
--   - 인사이트: rkyc_case_index
--   - 프로필: rkyc_corp_profile
--   - 작업: rkyc_job
--   - 외부 이벤트: rkyc_external_event, rkyc_external_event_target
--   - 외부 인텔 (v6): rkyc_external_news, rkyc_external_analysis,
--                     rkyc_industry_intel, rkyc_policy_tracker
--   - 컨텍스트: rkyc_unified_context
--   - 문서: rkyc_document, rkyc_document_page, rkyc_fact
--   - 대시보드: rkyc_dashboard_summary
--   - 감사 로그: rkyc_llm_audit_log
-- ============================================

-- Start transaction
BEGIN;

-- ============================================
-- Step 1: 시그널 관련 테이블 삭제 (FK 순서 중요)
-- ============================================

-- Signal embedding (FK: rkyc_signal)
TRUNCATE TABLE IF EXISTS rkyc_signal_embedding CASCADE;

-- Evidence (FK: rkyc_signal)
TRUNCATE TABLE IF EXISTS rkyc_evidence CASCADE;

-- Signal index (FK: rkyc_signal)
TRUNCATE TABLE IF EXISTS rkyc_signal_index CASCADE;

-- Signal (메인 테이블)
TRUNCATE TABLE IF EXISTS rkyc_signal CASCADE;

-- ============================================
-- Step 2: 인사이트 관련 테이블 삭제
-- ============================================

-- Case index (embedding 포함)
TRUNCATE TABLE IF EXISTS rkyc_case_index CASCADE;

-- ============================================
-- Step 3: Corp Profile 삭제
-- ============================================

TRUNCATE TABLE IF EXISTS rkyc_corp_profile CASCADE;

-- ============================================
-- Step 4: Job 삭제
-- ============================================

TRUNCATE TABLE IF EXISTS rkyc_job CASCADE;

-- ============================================
-- Step 5: External Event 삭제
-- ============================================

-- Event target mapping (FK: rkyc_external_event)
TRUNCATE TABLE IF EXISTS rkyc_external_event_target CASCADE;

-- External event
TRUNCATE TABLE IF EXISTS rkyc_external_event CASCADE;

-- ============================================
-- Step 6: External Intel 삭제 (v6 보안 아키텍처)
-- ============================================

TRUNCATE TABLE IF EXISTS rkyc_external_news CASCADE;
TRUNCATE TABLE IF EXISTS rkyc_external_analysis CASCADE;
TRUNCATE TABLE IF EXISTS rkyc_industry_intel CASCADE;
TRUNCATE TABLE IF EXISTS rkyc_policy_tracker CASCADE;

-- ============================================
-- Step 7: Context 삭제
-- ============================================

TRUNCATE TABLE IF EXISTS rkyc_unified_context CASCADE;

-- ============================================
-- Step 8: Document 관련 삭제 (FK 순서 중요)
-- ============================================

-- Fact (FK: rkyc_document)
TRUNCATE TABLE IF EXISTS rkyc_fact CASCADE;

-- Document page (FK: rkyc_document)
TRUNCATE TABLE IF EXISTS rkyc_document_page CASCADE;

-- Document
TRUNCATE TABLE IF EXISTS rkyc_document CASCADE;

-- ============================================
-- Step 9: Dashboard summary 삭제
-- ============================================

TRUNCATE TABLE IF EXISTS rkyc_dashboard_summary CASCADE;

-- ============================================
-- Step 10: LLM Audit Log 삭제 (v6)
-- ============================================

TRUNCATE TABLE IF EXISTS rkyc_llm_audit_log CASCADE;

COMMIT;

-- ============================================
-- Step 11: Verification (별도 쿼리로 실행)
-- ============================================

-- 삭제 확인 쿼리
SELECT 'rkyc_signal' AS table_name, COUNT(*) AS row_count FROM rkyc_signal
UNION ALL SELECT 'rkyc_signal_index', COUNT(*) FROM rkyc_signal_index
UNION ALL SELECT 'rkyc_evidence', COUNT(*) FROM rkyc_evidence
UNION ALL SELECT 'rkyc_case_index', COUNT(*) FROM rkyc_case_index
UNION ALL SELECT 'rkyc_corp_profile', COUNT(*) FROM rkyc_corp_profile
UNION ALL SELECT 'rkyc_job', COUNT(*) FROM rkyc_job
UNION ALL SELECT 'rkyc_external_event', COUNT(*) FROM rkyc_external_event
UNION ALL SELECT 'rkyc_unified_context', COUNT(*) FROM rkyc_unified_context
UNION ALL SELECT 'rkyc_document', COUNT(*) FROM rkyc_document
UNION ALL SELECT 'rkyc_dashboard_summary', COUNT(*) FROM rkyc_dashboard_summary;

-- 보존 확인 쿼리
SELECT 'corp (보존)' AS table_name, COUNT(*) AS row_count FROM corp
UNION ALL SELECT 'rkyc_internal_snapshot (보존)', COUNT(*) FROM rkyc_internal_snapshot
UNION ALL SELECT 'industry_master (보존)', COUNT(*) FROM industry_master;

-- ============================================
-- 완료 메시지
-- ============================================
--
-- 실행 후 확인:
-- - 모든 분석 결과 테이블 row_count = 0
-- - corp = 6개 기업 유지
-- - rkyc_internal_snapshot = 스냅샷 유지
-- - industry_master = 업종 마스터 유지
--
-- DART 필드는 corp 테이블에 보존됩니다:
-- - dart_corp_code, established_date, headquarters
-- - corp_class, homepage_url, dart_updated_at
-- - jurir_no, corp_name_eng, acc_mt
--
-- 시연 시작 후:
-- 1. Signal Inbox 페이지 → 빈 화면 확인
-- 2. Demo Panel에서 기업 선택 → "분석 실행" 클릭
-- 3. 시그널 생성 과정 관찰
-- ============================================
