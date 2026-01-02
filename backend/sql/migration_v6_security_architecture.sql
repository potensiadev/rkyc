-- =====================================================
-- Migration v6: Security Architecture - External Intel Tables
-- External/Internal LLM 분리 아키텍처를 위한 스키마
-- =====================================================

-- =====================================================
-- 1. External Intelligence 적재 테이블
-- External LLM이 수집/분석한 공개 정보 저장
-- =====================================================

-- 1.1 외부 뉴스/이벤트 원본
CREATE TABLE IF NOT EXISTS rkyc_external_news (
    news_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 원본 정보
    source_type VARCHAR(20) NOT NULL,  -- NEWS, DART, POLICY, REPORT
    source_name VARCHAR(100),           -- 언론사/출처명
    original_url TEXT NOT NULL,
    url_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA256 for dedup

    -- 컨텐츠
    title VARCHAR(500) NOT NULL,
    content_raw TEXT,                   -- 원문 (크롤링)
    published_at TIMESTAMPTZ NOT NULL,

    -- 메타데이터
    language VARCHAR(10) DEFAULT 'ko',
    crawled_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_external_news_source_type
        CHECK (source_type IN ('NEWS', 'DART', 'POLICY', 'REPORT'))
);

COMMENT ON TABLE rkyc_external_news IS 'External LLM이 수집한 외부 뉴스/이벤트 원본 데이터';
COMMENT ON COLUMN rkyc_external_news.source_type IS 'NEWS=뉴스, DART=공시, POLICY=정책/규제, REPORT=산업리포트';
COMMENT ON COLUMN rkyc_external_news.url_hash IS 'original_url의 SHA256 해시 (중복 방지)';


-- 1.2 External LLM 분석 결과
CREATE TABLE IF NOT EXISTS rkyc_external_analysis (
    analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    news_id UUID NOT NULL REFERENCES rkyc_external_news(news_id) ON DELETE CASCADE,

    -- LLM 분석 결과
    summary_ko TEXT NOT NULL,           -- 한글 요약 (200자 이내)
    summary_en TEXT,                    -- 영문 요약 (옵션)

    -- 분류/태깅 (LLM이 추출)
    industry_codes VARCHAR(10)[],       -- 관련 업종코드 배열
    keywords TEXT[],                    -- 핵심 키워드
    entities JSONB,                     -- 추출된 엔티티 (기업명, 인물 등)

    -- 이벤트 분류
    event_category VARCHAR(50),         -- INDUSTRY_SHOCK, POLICY_CHANGE, MARKET_TREND 등
    sentiment VARCHAR(20),              -- POSITIVE, NEGATIVE, NEUTRAL
    impact_level VARCHAR(10),           -- HIGH, MED, LOW

    -- LLM 메타데이터
    llm_provider VARCHAR(20) NOT NULL,  -- ANTHROPIC, OPENAI, PERPLEXITY
    llm_model VARCHAR(50) NOT NULL,     -- claude-sonnet-4, gpt-4o 등
    confidence DECIMAL(3,2),            -- 0.00 ~ 1.00

    -- 시그널 생성 여부
    is_signal_candidate BOOLEAN DEFAULT FALSE,
    signal_type_hint VARCHAR(20),       -- INDUSTRY, ENVIRONMENT

    analyzed_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_external_analysis_sentiment
        CHECK (sentiment IS NULL OR sentiment IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL')),
    CONSTRAINT chk_external_analysis_impact
        CHECK (impact_level IS NULL OR impact_level IN ('HIGH', 'MED', 'LOW')),
    CONSTRAINT chk_external_analysis_signal_type
        CHECK (signal_type_hint IS NULL OR signal_type_hint IN ('INDUSTRY', 'ENVIRONMENT'))
);

COMMENT ON TABLE rkyc_external_analysis IS 'External LLM이 분석한 외부 뉴스/이벤트 결과';
COMMENT ON COLUMN rkyc_external_analysis.is_signal_candidate IS 'TRUE면 Signal 생성 후보';
COMMENT ON COLUMN rkyc_external_analysis.signal_type_hint IS 'INDUSTRY 또는 ENVIRONMENT 시그널 타입 힌트';


-- 1.3 업종별 외부 인텔리전스 집계
CREATE TABLE IF NOT EXISTS rkyc_industry_intel (
    intel_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry_code VARCHAR(10) NOT NULL,

    -- 집계 기간
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- 집계 통계
    news_count INTEGER DEFAULT 0,
    positive_ratio DECIMAL(3,2),        -- 0.00 ~ 1.00
    negative_ratio DECIMAL(3,2),        -- 0.00 ~ 1.00

    -- LLM 생성 요약
    period_summary TEXT,                -- "이번 주 반도체 업종은..."
    key_events JSONB,                   -- 주요 이벤트 목록
    risk_factors JSONB,                 -- 식별된 리스크 요인
    opportunity_factors JSONB,          -- 식별된 기회 요인

    -- 메타데이터
    llm_model VARCHAR(50),
    generated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(industry_code, period_start, period_end)
);

COMMENT ON TABLE rkyc_industry_intel IS '업종별 주간/월간 외부 인텔리전스 집계';
COMMENT ON COLUMN rkyc_industry_intel.period_summary IS 'LLM이 생성한 기간별 업종 요약';


-- 1.4 정책/규제 변화 추적
CREATE TABLE IF NOT EXISTS rkyc_policy_tracker (
    policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 정책 정보
    policy_name VARCHAR(200) NOT NULL,
    policy_type VARCHAR(50),            -- REGULATION, GUIDELINE, LAW, ANNOUNCEMENT
    issuing_body VARCHAR(100),          -- 금융위, 금감원, 한국은행 등

    -- 영향 범위
    affected_industries VARCHAR(10)[],  -- 영향받는 업종 코드 배열
    effective_date DATE,

    -- LLM 분석
    summary TEXT,
    impact_analysis TEXT,               -- 영향도 분석
    action_required TEXT,               -- 필요 조치 사항

    -- 원본 참조
    source_url TEXT,
    source_document_path TEXT,
    news_id UUID REFERENCES rkyc_external_news(news_id),  -- 원본 뉴스 연결

    -- 메타데이터
    analyzed_by VARCHAR(50),            -- LLM 모델
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_policy_type
        CHECK (policy_type IS NULL OR policy_type IN ('REGULATION', 'GUIDELINE', 'LAW', 'ANNOUNCEMENT'))
);

COMMENT ON TABLE rkyc_policy_tracker IS '정책/규제 변화 추적 및 영향도 분석';
COMMENT ON COLUMN rkyc_policy_tracker.affected_industries IS '영향받는 업종 코드 배열 (예: {C26, C29})';


-- =====================================================
-- 2. LLM 호출 감사 로그 (Security Audit)
-- =====================================================

CREATE TABLE IF NOT EXISTS rkyc_llm_audit_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 호출 정보
    llm_type VARCHAR(20) NOT NULL,      -- EXTERNAL, INTERNAL
    llm_provider VARCHAR(20) NOT NULL,  -- ANTHROPIC, OPENAI, AZURE, ONPREM
    llm_model VARCHAR(50) NOT NULL,

    -- 요청/응답 (민감정보 제외)
    operation_type VARCHAR(50) NOT NULL, -- SIGNAL_EXTRACT, DOC_INGEST, INSIGHT, EXTERNAL_SEARCH 등
    input_token_count INTEGER,
    output_token_count INTEGER,

    -- 데이터 분류
    data_classification VARCHAR(20) NOT NULL,  -- PUBLIC, INTERNAL, SEMI_PUBLIC
    contains_pii BOOLEAN DEFAULT FALSE,

    -- 컨텍스트
    corp_id VARCHAR(20),
    job_id UUID,

    -- 결과
    success BOOLEAN NOT NULL,
    error_type VARCHAR(50),
    response_time_ms INTEGER,

    -- 메타데이터
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT chk_llm_type CHECK (llm_type IN ('EXTERNAL', 'INTERNAL')),
    CONSTRAINT chk_data_classification CHECK (data_classification IN ('PUBLIC', 'INTERNAL', 'SEMI_PUBLIC'))
);

COMMENT ON TABLE rkyc_llm_audit_log IS 'LLM 호출 감사 로그 (보안 추적용)';
COMMENT ON COLUMN rkyc_llm_audit_log.llm_type IS 'EXTERNAL=외부 공개 데이터용, INTERNAL=내부 민감 데이터용';
COMMENT ON COLUMN rkyc_llm_audit_log.data_classification IS 'PUBLIC=공개, INTERNAL=내부, SEMI_PUBLIC=준공개';


-- =====================================================
-- 3. 인덱스
-- =====================================================

-- External News 인덱스
CREATE INDEX IF NOT EXISTS idx_external_news_published
    ON rkyc_external_news(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_external_news_source
    ON rkyc_external_news(source_type);
CREATE INDEX IF NOT EXISTS idx_external_news_crawled
    ON rkyc_external_news(crawled_at DESC);

-- External Analysis 인덱스
CREATE INDEX IF NOT EXISTS idx_external_analysis_industry
    ON rkyc_external_analysis USING GIN(industry_codes);
CREATE INDEX IF NOT EXISTS idx_external_analysis_signal_candidate
    ON rkyc_external_analysis(is_signal_candidate)
    WHERE is_signal_candidate = TRUE;
CREATE INDEX IF NOT EXISTS idx_external_analysis_analyzed
    ON rkyc_external_analysis(analyzed_at DESC);
CREATE INDEX IF NOT EXISTS idx_external_analysis_event_category
    ON rkyc_external_analysis(event_category);

-- Industry Intel 인덱스
CREATE INDEX IF NOT EXISTS idx_industry_intel_code_period
    ON rkyc_industry_intel(industry_code, period_end DESC);

-- Policy Tracker 인덱스
CREATE INDEX IF NOT EXISTS idx_policy_tracker_industries
    ON rkyc_policy_tracker USING GIN(affected_industries);
CREATE INDEX IF NOT EXISTS idx_policy_tracker_effective
    ON rkyc_policy_tracker(effective_date DESC);
CREATE INDEX IF NOT EXISTS idx_policy_tracker_type
    ON rkyc_policy_tracker(policy_type);

-- LLM Audit Log 인덱스
CREATE INDEX IF NOT EXISTS idx_llm_audit_created
    ON rkyc_llm_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_audit_type
    ON rkyc_llm_audit_log(llm_type);
CREATE INDEX IF NOT EXISTS idx_llm_audit_corp
    ON rkyc_llm_audit_log(corp_id)
    WHERE corp_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_llm_audit_job
    ON rkyc_llm_audit_log(job_id)
    WHERE job_id IS NOT NULL;


-- =====================================================
-- 4. 헬퍼 함수
-- =====================================================

-- 4.1 URL 해시 생성 함수
CREATE OR REPLACE FUNCTION generate_url_hash(url TEXT)
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN encode(sha256(url::bytea), 'hex');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION generate_url_hash IS 'URL의 SHA256 해시 생성';


-- 4.2 업종별 시그널 후보 조회 함수
CREATE OR REPLACE FUNCTION get_signal_candidates_by_industry(
    p_industry_code VARCHAR(10),
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    analysis_id UUID,
    news_id UUID,
    title VARCHAR(500),
    summary_ko TEXT,
    event_category VARCHAR(50),
    impact_level VARCHAR(10),
    signal_type_hint VARCHAR(20),
    published_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ea.analysis_id,
        ea.news_id,
        en.title,
        ea.summary_ko,
        ea.event_category,
        ea.impact_level,
        ea.signal_type_hint,
        en.published_at
    FROM rkyc_external_analysis ea
    JOIN rkyc_external_news en ON ea.news_id = en.news_id
    WHERE ea.is_signal_candidate = TRUE
      AND p_industry_code = ANY(ea.industry_codes)
    ORDER BY en.published_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_signal_candidates_by_industry IS '업종별 시그널 후보 조회';


-- 4.3 최근 정책 변화 조회 함수
CREATE OR REPLACE FUNCTION get_recent_policy_changes(
    p_industry_code VARCHAR(10),
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    policy_id UUID,
    policy_name VARCHAR(200),
    policy_type VARCHAR(50),
    issuing_body VARCHAR(100),
    effective_date DATE,
    summary TEXT,
    impact_analysis TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pt.policy_id,
        pt.policy_name,
        pt.policy_type,
        pt.issuing_body,
        pt.effective_date,
        pt.summary,
        pt.impact_analysis
    FROM rkyc_policy_tracker pt
    WHERE p_industry_code = ANY(pt.affected_industries)
      AND pt.created_at >= NOW() - (p_days || ' days')::INTERVAL
    ORDER BY pt.created_at DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_recent_policy_changes IS '최근 정책/규제 변화 조회';


-- =====================================================
-- 5. 검증 쿼리
-- =====================================================

-- 테이블 생성 확인
SELECT 'rkyc_external_news' AS table_name, COUNT(*) AS row_count FROM rkyc_external_news
UNION ALL
SELECT 'rkyc_external_analysis', COUNT(*) FROM rkyc_external_analysis
UNION ALL
SELECT 'rkyc_industry_intel', COUNT(*) FROM rkyc_industry_intel
UNION ALL
SELECT 'rkyc_policy_tracker', COUNT(*) FROM rkyc_policy_tracker
UNION ALL
SELECT 'rkyc_llm_audit_log', COUNT(*) FROM rkyc_llm_audit_log;
