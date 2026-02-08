-- ============================================
-- rKYC Demo Data Reset Script (Safe Version)
-- Purpose: 해커톤 시연을 위한 데이터 초기화
-- Date: 2026-02-08
-- Note: Supabase SQL Editor에서 바로 실행 가능
-- ============================================
--
-- 시연 시나리오: 빈 화면 시작
-- 보존: corp, rkyc_internal_snapshot, industry_master
-- 삭제: 모든 분석 결과 데이터
-- ============================================

-- Step 1: 시그널 관련 (FK 순서)
DELETE FROM rkyc_signal_embedding;
DELETE FROM rkyc_evidence;
DELETE FROM rkyc_signal_index;
DELETE FROM rkyc_signal;

-- Step 2: 인사이트
DELETE FROM rkyc_case_index;

-- Step 3: Corp Profile
DELETE FROM rkyc_corp_profile;

-- Step 4: Job
DELETE FROM rkyc_job;

-- Step 5: External Event
DELETE FROM rkyc_external_event_target;
DELETE FROM rkyc_external_event;

-- Step 6: Context
DELETE FROM rkyc_unified_context;

-- Step 7: Document
DELETE FROM rkyc_fact;
DELETE FROM rkyc_document_page;
DELETE FROM rkyc_document;

-- Step 8: Dashboard
DELETE FROM rkyc_dashboard_summary;
