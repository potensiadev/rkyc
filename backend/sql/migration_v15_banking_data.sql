-- ============================================================
-- rKYC Migration v15: Internal Banking Data
-- PRD: Internal Banking Data Integration v1.1
--
-- 은행 내부 거래 데이터 테이블 생성
-- - 여신/수신/카드/담보/무역금융/재무제표
-- - 리스크 시그널 및 영업 기회 자동 탐지 지원
-- ============================================================

-- 1. rkyc_banking_data 테이블 생성
CREATE TABLE IF NOT EXISTS rkyc_banking_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id) ON DELETE CASCADE,

    -- 메타데이터
    data_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- JSON 데이터 블록
    loan_exposure JSONB,           -- 여신 현황
    deposit_trend JSONB,           -- 수신 추이
    card_usage JSONB,              -- 법인카드
    collateral_detail JSONB,       -- 담보 상세
    trade_finance JSONB,           -- 무역금융
    financial_statements JSONB,    -- 재무제표 (DART 연동)

    -- 자동 생성된 시그널
    risk_alerts JSONB DEFAULT '[]'::jsonb,           -- 리스크 알림
    opportunity_signals JSONB DEFAULT '[]'::jsonb,   -- 영업 기회

    -- 유니크 제약
    UNIQUE(corp_id, data_date)
);

-- 2. 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_banking_data_corp ON rkyc_banking_data(corp_id);
CREATE INDEX IF NOT EXISTS idx_banking_data_date ON rkyc_banking_data(data_date DESC);
CREATE INDEX IF NOT EXISTS idx_banking_data_corp_date ON rkyc_banking_data(corp_id, data_date DESC);

-- 3. GIN 인덱스 (JSONB 검색용)
CREATE INDEX IF NOT EXISTS idx_banking_data_risk_alerts ON rkyc_banking_data USING GIN (risk_alerts);
CREATE INDEX IF NOT EXISTS idx_banking_data_loan ON rkyc_banking_data USING GIN (loan_exposure);

-- 4. 최신 데이터 조회용 뷰
CREATE OR REPLACE VIEW rkyc_banking_data_latest AS
SELECT DISTINCT ON (corp_id) *
FROM rkyc_banking_data
ORDER BY corp_id, data_date DESC;

-- 5. 검증
DO $$
BEGIN
    RAISE NOTICE 'Migration v15 완료: rkyc_banking_data 테이블 생성됨';
END $$;
