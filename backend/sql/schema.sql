-- rKYC Database Schema
-- Supabase PostgreSQL (Tokyo ap-northeast-1)
-- Version: 1.0.0

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================
-- ENUM TYPES
-- ============================================

CREATE TYPE corporation_status AS ENUM ('active', 'watch', 'inactive');
CREATE TYPE signal_category AS ENUM ('financial', 'legal', 'reputational', 'operational', 'market');
CREATE TYPE signal_status AS ENUM ('new', 'reviewed', 'confirmed', 'dismissed');
CREATE TYPE job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
CREATE TYPE pipeline_step AS ENUM (
    'snapshot', 'doc_ingest', 'external', 'context',
    'signal', 'validation', 'index', 'insight'
);
CREATE TYPE user_role AS ENUM ('admin', 'analyst', 'viewer');

-- ============================================
-- CORE TABLES
-- ============================================

-- 기업 정보
CREATE TABLE corporations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    biz_no VARCHAR(12) UNIQUE NOT NULL,  -- 사업자등록번호 (XXX-XX-XXXXX)
    corp_name VARCHAR(200) NOT NULL,
    corp_name_en VARCHAR(200),
    status corporation_status DEFAULT 'active',
    industry VARCHAR(100),
    industry_code VARCHAR(10),
    employee_count INTEGER,
    established_date DATE,
    ceo_name VARCHAR(100),
    address TEXT,
    phone VARCHAR(20),
    website VARCHAR(255),
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- soft delete
);

-- 사용자 정보 (Supabase Auth 연동)
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100),
    role user_role DEFAULT 'viewer',
    department VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 사용자-기업 담당 할당
CREATE TABLE user_corporation_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    corporation_id UUID NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id),
    UNIQUE(user_id, corporation_id)
);

-- 시그널 (리스크 징후)
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    corporation_id UUID NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
    category signal_category NOT NULL,
    severity INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 5),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    evidence JSONB NOT NULL DEFAULT '[]',  -- [{url, source, title, date}]
    status signal_status DEFAULT 'new',
    source VARCHAR(100),  -- 시그널 출처 (llm, manual, import)
    analysis_job_id UUID,  -- 생성한 분석 작업 ID
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    dismissed_reason TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 시그널 감사 로그
CREATE TABLE signal_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,  -- status_change:new->reviewed
    old_value JSONB,
    new_value JSONB,
    reason TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 분석 작업
CREATE TABLE analysis_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    corporation_id UUID NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL DEFAULT 'full_analysis',
    status job_status DEFAULT 'pending',
    pipeline_step pipeline_step,
    priority INTEGER DEFAULT 0,  -- 높을수록 우선
    triggered_by UUID REFERENCES users(id),
    celery_task_id VARCHAR(255),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',  -- 단계별 결과 저장
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 재무 스냅샷
CREATE TABLE financial_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    corporation_id UUID NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,  -- NULL이면 연간
    revenue BIGINT,
    operating_profit BIGINT,
    net_income BIGINT,
    total_assets BIGINT,
    total_liabilities BIGINT,
    total_equity BIGINT,
    debt_ratio DECIMAL(10,4),
    current_ratio DECIMAL(10,4),
    roe DECIMAL(10,4),
    roa DECIMAL(10,4),
    source VARCHAR(100),  -- dart, manual, import
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(corporation_id, fiscal_year, fiscal_quarter)
);

-- 비재무 스냅샷
CREATE TABLE non_financial_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    corporation_id UUID NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    employee_count INTEGER,
    credit_rating VARCHAR(10),
    credit_agency VARCHAR(50),
    legal_issues_count INTEGER DEFAULT 0,
    news_sentiment_score DECIMAL(5,4),  -- -1 to 1
    esg_score DECIMAL(5,2),
    patent_count INTEGER,
    certification_count INTEGER,
    source VARCHAR(100),
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인사이트 메모리 (벡터 저장소)
CREATE TABLE insight_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    corporation_id UUID NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_type VARCHAR(50),  -- signal, insight, summary
    embedding VECTOR(1536),  -- text-embedding-3-small
    signal_id UUID REFERENCES signals(id),
    analysis_job_id UUID REFERENCES analysis_jobs(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 제출 문서
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    corporation_id UUID NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,  -- financial_statement, audit_report, etc
    title VARCHAR(500) NOT NULL,
    file_path VARCHAR(500),  -- Supabase Storage path
    file_size INTEGER,
    mime_type VARCHAR(100),
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,
    ocr_status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    ocr_text TEXT,
    uploaded_by UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- LLM 호출 로그
CREATE TABLE llm_call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_job_id UUID REFERENCES analysis_jobs(id),
    provider VARCHAR(50) NOT NULL,  -- anthropic, openai, perplexity, google
    model VARCHAR(100) NOT NULL,
    pipeline_step pipeline_step,
    input_tokens INTEGER,
    output_tokens INTEGER,
    latency_ms INTEGER,
    cost_usd DECIMAL(10,6),
    status VARCHAR(20),  -- success, error, fallback
    error_message TEXT,
    request_metadata JSONB,
    response_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

-- corporations
CREATE INDEX idx_corps_biz_no ON corporations(biz_no);
CREATE INDEX idx_corps_status ON corporations(status);
CREATE INDEX idx_corps_name_trgm ON corporations USING gin(corp_name gin_trgm_ops);
CREATE INDEX idx_corps_deleted ON corporations(deleted_at) WHERE deleted_at IS NULL;

-- signals
CREATE INDEX idx_signals_corp_id ON signals(corporation_id);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_category ON signals(category);
CREATE INDEX idx_signals_severity ON signals(severity DESC);
CREATE INDEX idx_signals_created ON signals(created_at DESC);
CREATE INDEX idx_signals_corp_status ON signals(corporation_id, status);

-- analysis_jobs
CREATE INDEX idx_jobs_corp_id ON analysis_jobs(corporation_id);
CREATE INDEX idx_jobs_status ON analysis_jobs(status);
CREATE INDEX idx_jobs_celery ON analysis_jobs(celery_task_id);
CREATE INDEX idx_jobs_created ON analysis_jobs(created_at DESC);

-- insight_memories (vector search)
CREATE INDEX idx_memories_corp_id ON insight_memories(corporation_id);
CREATE INDEX idx_memories_embedding ON insight_memories
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- documents
CREATE INDEX idx_docs_corp_id ON documents(corporation_id);
CREATE INDEX idx_docs_type ON documents(document_type);

-- llm_call_logs
CREATE INDEX idx_llm_logs_job_id ON llm_call_logs(analysis_job_id);
CREATE INDEX idx_llm_logs_created ON llm_call_logs(created_at DESC);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Updated at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_corporations_updated_at
    BEFORE UPDATE ON corporations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_signals_updated_at
    BEFORE UPDATE ON signals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analysis_jobs_updated_at
    BEFORE UPDATE ON analysis_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Vector similarity search function
CREATE OR REPLACE FUNCTION search_similar_insights(
    query_embedding VECTOR(1536),
    target_corp_id UUID,
    match_count INTEGER DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    content_type VARCHAR(50),
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        im.id,
        im.content,
        im.content_type,
        1 - (im.embedding <=> query_embedding) AS similarity
    FROM insight_memories im
    WHERE im.corporation_id = target_corp_id
    ORDER BY im.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

-- Enable RLS
ALTER TABLE corporations ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policies (기본: 할당된 기업만 접근)
CREATE POLICY "Users can view assigned corporations"
ON corporations FOR SELECT
USING (
    auth.uid() IN (
        SELECT user_id FROM user_corporation_assignments
        WHERE corporation_id = corporations.id
    )
    OR
    EXISTS (
        SELECT 1 FROM users
        WHERE id = auth.uid() AND role = 'admin'
    )
);

CREATE POLICY "Users can view signals of assigned corporations"
ON signals FOR SELECT
USING (
    corporation_id IN (
        SELECT corporation_id FROM user_corporation_assignments
        WHERE user_id = auth.uid()
    )
    OR
    EXISTS (
        SELECT 1 FROM users
        WHERE id = auth.uid() AND role = 'admin'
    )
);

CREATE POLICY "Analysts can update signals"
ON signals FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = auth.uid() AND role IN ('admin', 'analyst')
    )
);

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE corporations IS '기업 정보 테이블';
COMMENT ON COLUMN corporations.biz_no IS '사업자등록번호 (10자리, XXX-XX-XXXXX)';
COMMENT ON COLUMN corporations.status IS '기업 상태: active(정상), watch(관심), inactive(비활성)';

COMMENT ON TABLE signals IS '리스크 시그널 테이블';
COMMENT ON COLUMN signals.category IS '시그널 카테고리: financial, legal, reputational, operational, market';
COMMENT ON COLUMN signals.severity IS '심각도 (1:info ~ 5:critical)';
COMMENT ON COLUMN signals.evidence IS 'JSON 배열: [{url, source, title, date}]';
COMMENT ON COLUMN signals.status IS '상태: new → reviewed → confirmed/dismissed';

COMMENT ON TABLE analysis_jobs IS '분석 작업 테이블';
COMMENT ON COLUMN analysis_jobs.pipeline_step IS '현재 파이프라인 단계';
COMMENT ON COLUMN analysis_jobs.metadata IS '단계별 중간 결과 저장';

COMMENT ON TABLE insight_memories IS '인사이트 메모리 (벡터 저장소)';
COMMENT ON COLUMN insight_memories.embedding IS 'text-embedding-3-small (1536차원)';

-- ============================================
-- INITIAL DATA (System)
-- ============================================

-- 시스템 사용자 (Worker용)
INSERT INTO users (id, email, name, role, is_active)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'system@rkyc.local',
    'System',
    'admin',
    true
) ON CONFLICT (id) DO NOTHING;
