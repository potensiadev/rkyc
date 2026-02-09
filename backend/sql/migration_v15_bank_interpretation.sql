-- ============================================================
-- Migration v15: Bank Interpretation Layer (MVP)
-- 은행 관점 시그널 재해석 컬럼 추가
-- ============================================================

-- 1. rkyc_signal 테이블에 은행 관점 해석 컬럼 추가
ALTER TABLE rkyc_signal ADD COLUMN IF NOT EXISTS bank_interpretation TEXT;
ALTER TABLE rkyc_signal ADD COLUMN IF NOT EXISTS portfolio_impact VARCHAR(10);
ALTER TABLE rkyc_signal ADD COLUMN IF NOT EXISTS recommended_action TEXT;
ALTER TABLE rkyc_signal ADD COLUMN IF NOT EXISTS action_priority VARCHAR(10);
ALTER TABLE rkyc_signal ADD COLUMN IF NOT EXISTS interpretation_generated_at TIMESTAMPTZ;

-- 2. Portfolio Impact ENUM 체크
-- HIGH: 포트폴리오 전체에 영향
-- MED: 해당 섹터/업종에 영향
-- LOW: 개별 기업에만 영향
ALTER TABLE rkyc_signal
ADD CONSTRAINT chk_portfolio_impact
CHECK (portfolio_impact IS NULL OR portfolio_impact IN ('HIGH', 'MED', 'LOW'));

-- 3. Action Priority ENUM 체크
-- URGENT: 즉시 검토 필요 (1일 이내)
-- NORMAL: 일반 검토 (1주 이내)
-- LOW: 모니터링 수준
ALTER TABLE rkyc_signal
ADD CONSTRAINT chk_action_priority
CHECK (action_priority IS NULL OR action_priority IN ('URGENT', 'NORMAL', 'LOW'));

-- 4. 인덱스 추가 (은행 관점 필터링용)
CREATE INDEX IF NOT EXISTS idx_signal_portfolio_impact
ON rkyc_signal(portfolio_impact)
WHERE portfolio_impact IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_signal_action_priority
ON rkyc_signal(action_priority)
WHERE action_priority IS NOT NULL;

-- 5. 코멘트 추가
COMMENT ON COLUMN rkyc_signal.bank_interpretation IS '은행 관점 재해석 텍스트 (당행 여신 기준)';
COMMENT ON COLUMN rkyc_signal.portfolio_impact IS '포트폴리오 영향도 (HIGH/MED/LOW)';
COMMENT ON COLUMN rkyc_signal.recommended_action IS '권고 조치 (검토 수준만)';
COMMENT ON COLUMN rkyc_signal.action_priority IS '조치 우선순위 (URGENT/NORMAL/LOW)';
COMMENT ON COLUMN rkyc_signal.interpretation_generated_at IS '재해석 생성 시각';
