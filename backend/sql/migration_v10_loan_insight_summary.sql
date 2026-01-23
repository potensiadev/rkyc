-- Migration v10: Loan Insight Executive Summary 확장
-- executive_summary + key_opportunities 컬럼 추가

-- ============================================================
-- 1. 새 컬럼 추가
-- ============================================================

-- Executive Summary: 사업개요 + 비즈니스모델 + 핵심 시그널 요약 (2-3문장)
ALTER TABLE rkyc_loan_insight
ADD COLUMN IF NOT EXISTS executive_summary TEXT;

-- Key Opportunities: 기회 시그널 기반 기회 요인 리스트
ALTER TABLE rkyc_loan_insight
ADD COLUMN IF NOT EXISTS key_opportunities JSONB NOT NULL DEFAULT '[]'::jsonb;

-- ============================================================
-- 2. 코멘트 추가
-- ============================================================

COMMENT ON COLUMN rkyc_loan_insight.executive_summary IS '사업개요 + 비즈니스모델 + 핵심 리스크/기회 요약 (2-3문장). CorporateDetailPage Executive Summary 섹션에 표시.';
COMMENT ON COLUMN rkyc_loan_insight.key_opportunities IS '기회 시그널 기반 기회 요인 리스트. key_risks와 대칭.';

-- ============================================================
-- 3. 기존 데이터 마이그레이션 (기존 narrative를 executive_summary로 복사)
-- ============================================================

UPDATE rkyc_loan_insight
SET executive_summary = narrative
WHERE executive_summary IS NULL;
