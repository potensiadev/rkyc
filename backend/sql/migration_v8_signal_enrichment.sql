-- ============================================
-- Migration v8: Signal Enrichment
-- Signal Detail 페이지에 표시할 풍부한 분석 데이터 저장
-- ============================================

-- 1. rkyc_signal 테이블에 분석 메타데이터 컬럼 추가
ALTER TABLE rkyc_signal ADD COLUMN IF NOT EXISTS analysis_reasoning TEXT;
ALTER TABLE rkyc_signal ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100);
ALTER TABLE rkyc_signal ADD COLUMN IF NOT EXISTS extraction_metadata JSONB;

COMMENT ON COLUMN rkyc_signal.analysis_reasoning IS 'LLM이 시그널을 추출한 근거/추론 과정';
COMMENT ON COLUMN rkyc_signal.llm_model IS '시그널 추출에 사용된 LLM 모델';
COMMENT ON COLUMN rkyc_signal.extraction_metadata IS '추출 관련 메타데이터 (token count, latency 등)';

-- 2. 유사 케이스 테이블 (Signal별 유사 과거 케이스)
CREATE TABLE IF NOT EXISTS rkyc_signal_similar_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id) ON DELETE CASCADE,
    similar_signal_id UUID REFERENCES rkyc_signal(signal_id),
    similar_case_id UUID,  -- rkyc_case_index 참조
    similarity_score DECIMAL(4, 3) NOT NULL,  -- 0.000 ~ 1.000
    corp_id VARCHAR(20),
    corp_name VARCHAR(200),
    industry_code VARCHAR(10),
    signal_type VARCHAR(20),
    event_type VARCHAR(50),
    summary TEXT,
    outcome TEXT,  -- 과거 케이스의 결과 (있는 경우)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_similar_cases_signal_id ON rkyc_signal_similar_cases(signal_id);
CREATE INDEX IF NOT EXISTS idx_similar_cases_score ON rkyc_signal_similar_cases(similarity_score DESC);

COMMENT ON TABLE rkyc_signal_similar_cases IS '시그널별 유사 과거 케이스 (pgvector 검색 결과 저장)';

-- 3. 다중 소스 검증 결과 테이블
CREATE TABLE IF NOT EXISTS rkyc_signal_verification (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id) ON DELETE CASCADE,
    verification_type VARCHAR(50) NOT NULL,  -- 'SOURCE_CHECK', 'CROSS_REFERENCE', 'FACT_VALIDATION'
    source_name VARCHAR(100),  -- Perplexity, Gemini, News, DART 등
    source_url TEXT,
    verification_status VARCHAR(20) NOT NULL,  -- 'VERIFIED', 'PARTIAL', 'UNVERIFIED', 'CONFLICTING'
    confidence_contribution DECIMAL(3, 2),  -- 신뢰도 기여도 0.00 ~ 1.00
    details JSONB,  -- 검증 상세 내용
    verified_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_verification_signal_id ON rkyc_signal_verification(signal_id);

COMMENT ON TABLE rkyc_signal_verification IS '시그널 다중 소스 검증 결과';

-- 4. 영향도 분석 테이블
CREATE TABLE IF NOT EXISTS rkyc_signal_impact_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id) ON DELETE CASCADE,
    analysis_type VARCHAR(50) NOT NULL,  -- 'FINANCIAL', 'CREDIT', 'OPERATIONAL', 'REGULATORY'
    metric_name VARCHAR(100) NOT NULL,
    current_value DECIMAL(20, 4),
    projected_impact DECIMAL(20, 4),
    impact_direction VARCHAR(20),  -- 'INCREASE', 'DECREASE', 'STABLE'
    impact_percentage DECIMAL(6, 2),
    industry_avg DECIMAL(20, 4),
    industry_percentile INTEGER,  -- 1-100
    reasoning TEXT,
    data_source VARCHAR(100),
    analyzed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_impact_signal_id ON rkyc_signal_impact_analysis(signal_id);

COMMENT ON TABLE rkyc_signal_impact_analysis IS '시그널 영향도 분석 결과';

-- 5. 관련 시그널 연결 테이블
CREATE TABLE IF NOT EXISTS rkyc_signal_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id) ON DELETE CASCADE,
    related_signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL,  -- 'SAME_CORP', 'SAME_INDUSTRY', 'CAUSAL', 'TEMPORAL'
    relation_strength DECIMAL(3, 2),  -- 0.00 ~ 1.00
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(signal_id, related_signal_id)
);

CREATE INDEX IF NOT EXISTS idx_relations_signal_id ON rkyc_signal_relations(signal_id);
CREATE INDEX IF NOT EXISTS idx_relations_related_id ON rkyc_signal_relations(related_signal_id);

COMMENT ON TABLE rkyc_signal_relations IS '시그널 간 관계 정보';

-- 6. 인사이트 저장 테이블 (Job별 생성된 최종 인사이트)
CREATE TABLE IF NOT EXISTS rkyc_insight (
    insight_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id),
    job_id UUID REFERENCES rkyc_job(job_id),
    insight_type VARCHAR(50) NOT NULL,  -- 'EXECUTIVE_BRIEFING', 'RISK_SUMMARY', 'OPPORTUNITY_SUMMARY'
    content TEXT NOT NULL,
    signal_count INTEGER NOT NULL,
    risk_count INTEGER DEFAULT 0,
    opportunity_count INTEGER DEFAULT 0,
    high_priority_count INTEGER DEFAULT 0,
    similar_cases_referenced INTEGER DEFAULT 0,
    llm_model VARCHAR(100),
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insight_corp_id ON rkyc_insight(corp_id);
CREATE INDEX IF NOT EXISTS idx_insight_job_id ON rkyc_insight(job_id);

COMMENT ON TABLE rkyc_insight IS '생성된 인사이트/브리핑 저장';

-- 7. Evidence 테이블에 메타데이터 확장
ALTER TABLE rkyc_evidence ADD COLUMN IF NOT EXISTS source_credibility VARCHAR(20);  -- 'OFFICIAL', 'MAJOR_MEDIA', 'MINOR_MEDIA', 'UNKNOWN'
ALTER TABLE rkyc_evidence ADD COLUMN IF NOT EXISTS verification_status VARCHAR(20);  -- 'VERIFIED', 'UNVERIFIED'
ALTER TABLE rkyc_evidence ADD COLUMN IF NOT EXISTS retrieved_at TIMESTAMPTZ;

COMMENT ON COLUMN rkyc_evidence.source_credibility IS '소스 신뢰도 등급';
COMMENT ON COLUMN rkyc_evidence.verification_status IS '검증 상태';

-- 검증용 카운트
SELECT 'Migration v8 completed' AS status,
       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'rkyc_signal' AND column_name = 'analysis_reasoning') AS signal_reasoning_added,
       (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'rkyc_signal_similar_cases') AS similar_cases_table,
       (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'rkyc_signal_verification') AS verification_table,
       (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'rkyc_signal_impact_analysis') AS impact_table,
       (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'rkyc_signal_relations') AS relations_table,
       (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'rkyc_insight') AS insight_table;
