-- ============================================
-- rKYC Demo Data Reset Script
-- Purpose: 해커톤 시연을 위한 데이터 초기화
-- Date: 2026-02-08
-- ============================================
--
-- 보존 대상 (기업 마스터 데이터):
--   - corp (6개 기업)
--   - rkyc_internal_snapshot (내부 스냅샷)
--   - rkyc_internal_snapshot_latest (최신 포인터)
--   - industry_master (업종 마스터)
--
-- 삭제 대상 (분석 결과 데이터):
--   - rkyc_signal, rkyc_signal_index, rkyc_evidence
--   - rkyc_signal_embedding, rkyc_case_index
--   - rkyc_corp_profile
--   - rkyc_loan_insight (AI 분석 결과 - Executive Summary, 리스크/기회 요인 등)
--   - rkyc_job
--   - rkyc_external_event, rkyc_external_event_target
--   - rkyc_unified_context
--   - rkyc_document, rkyc_document_page, rkyc_fact
--   - rkyc_dashboard_summary
-- ============================================

-- Start transaction
BEGIN;

-- ============================================
-- Step 1: 시그널 관련 테이블 삭제 (FK 순서 중요)
-- ============================================

-- Signal embedding (FK: rkyc_signal)
TRUNCATE TABLE rkyc_signal_embedding CASCADE;

-- Evidence (FK: rkyc_signal)
TRUNCATE TABLE rkyc_evidence CASCADE;

-- Signal index (FK: rkyc_signal)
TRUNCATE TABLE rkyc_signal_index CASCADE;

-- Signal (메인 테이블)
TRUNCATE TABLE rkyc_signal CASCADE;

-- Case index (embedding 포함)
TRUNCATE TABLE rkyc_case_index CASCADE;

-- ============================================
-- Step 2: Corp Profile 삭제
-- ============================================

TRUNCATE TABLE rkyc_corp_profile CASCADE;

-- ============================================
-- Step 2-1: Loan Insight 삭제 (AI 분석 결과)
-- ============================================
-- Executive Summary, 핵심 리스크/기회 요인, 심사역 체크리스트 등

TRUNCATE TABLE rkyc_loan_insight CASCADE;

-- ============================================
-- Step 3: Job 삭제
-- ============================================

TRUNCATE TABLE rkyc_job CASCADE;

-- ============================================
-- Step 4: External Event 삭제
-- ============================================

-- Event target mapping (FK: rkyc_external_event)
TRUNCATE TABLE rkyc_external_event_target CASCADE;

-- External event
TRUNCATE TABLE rkyc_external_event CASCADE;

-- ============================================
-- Step 5: Context 삭제
-- ============================================

TRUNCATE TABLE rkyc_unified_context CASCADE;

-- ============================================
-- Step 6: Document 관련 삭제 (FK 순서 중요)
-- ============================================

-- Fact (FK: rkyc_document)
TRUNCATE TABLE rkyc_fact CASCADE;

-- Document page (FK: rkyc_document)
TRUNCATE TABLE rkyc_document_page CASCADE;

-- Document
TRUNCATE TABLE rkyc_document CASCADE;

-- ============================================
-- Step 7: Dashboard summary 삭제
-- ============================================

TRUNCATE TABLE rkyc_dashboard_summary CASCADE;

-- ============================================
-- Step 8: Verification
-- ============================================

-- 삭제 확인 쿼리
SELECT 'rkyc_signal' AS table_name, COUNT(*) AS row_count FROM rkyc_signal
UNION ALL
SELECT 'rkyc_signal_index', COUNT(*) FROM rkyc_signal_index
UNION ALL
SELECT 'rkyc_evidence', COUNT(*) FROM rkyc_evidence
UNION ALL
SELECT 'rkyc_signal_embedding', COUNT(*) FROM rkyc_signal_embedding
UNION ALL
SELECT 'rkyc_case_index', COUNT(*) FROM rkyc_case_index
UNION ALL
SELECT 'rkyc_corp_profile', COUNT(*) FROM rkyc_corp_profile
UNION ALL
SELECT 'rkyc_job', COUNT(*) FROM rkyc_job
UNION ALL
SELECT 'rkyc_external_event', COUNT(*) FROM rkyc_external_event
UNION ALL
SELECT 'rkyc_unified_context', COUNT(*) FROM rkyc_unified_context
UNION ALL
SELECT 'rkyc_document', COUNT(*) FROM rkyc_document
UNION ALL
SELECT 'rkyc_fact', COUNT(*) FROM rkyc_fact
UNION ALL
SELECT 'rkyc_loan_insight', COUNT(*) FROM rkyc_loan_insight;

-- 보존 확인 쿼리
SELECT 'corp (보존)' AS table_name, COUNT(*) AS row_count FROM corp
UNION ALL
SELECT 'rkyc_internal_snapshot (보존)', COUNT(*) FROM rkyc_internal_snapshot
UNION ALL
SELECT 'industry_master (보존)', COUNT(*) FROM industry_master;

-- Commit transaction
COMMIT;

-- ============================================
-- 실행 완료 메시지
-- ============================================
--
-- 실행 방법:
-- 1. Supabase SQL Editor에서 이 스크립트 전체 실행
-- 2. 또는 psql: psql -f reset_demo_data.sql
--
-- 실행 후 확인:
-- - 모든 분석 결과 테이블: 0 rows
-- - corp: 6 rows (보존됨)
-- - rkyc_internal_snapshot: 6 rows (보존됨)
-- ============================================
