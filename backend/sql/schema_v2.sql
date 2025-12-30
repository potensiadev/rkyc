-- ============================================
-- rKYC Database Schema v2.0
-- PRD 14장 기준 재설계
-- Supabase PostgreSQL (Tokyo ap-northeast-1)
-- ============================================

-- ============================================
-- ENUM TYPES (PRD 9장, 10장 기준)
-- ============================================

-- 14.3 Document Types
CREATE TYPE doc_type_enum AS ENUM ('BIZ_REG', 'REGISTRY', 'SHAREHOLDERS', 'AOI', 'FIN_STATEMENT');
CREATE TYPE ingest_status_enum AS ENUM ('PENDING', 'RUNNING', 'DONE', 'FAILED');

-- 14.4 Confidence Level
CREATE TYPE confidence_level AS ENUM ('HIGH', 'MED', 'LOW');

-- 14.5 External Event Types
CREATE TYPE source_type_enum AS ENUM ('NEWS', 'DISCLOSURE', 'POLICY', 'REPORT');
CREATE TYPE external_event_type_enum AS ENUM ('INDUSTRY_SHOCK', 'POLICY_REGULATION_CHANGE');
CREATE TYPE match_basis_enum AS ENUM ('INDUSTRY_CODE', 'INDUSTRY_GROUP', 'MANUAL_SEED');

-- 14.7 Signal Types (PRD 9장: 10종 고정)
CREATE TYPE event_type_enum AS ENUM (
    'KYC_REFRESH',
    'INTERNAL_RISK_GRADE_CHANGE',
    'OVERDUE_FLAG_ON',
    'LOAN_EXPOSURE_CHANGE',
    'COLLATERAL_CHANGE',
    'OWNERSHIP_CHANGE',
    'GOVERNANCE_CHANGE',
    'FINANCIAL_STATEMENT_UPDATE',
    'INDUSTRY_SHOCK',
    'POLICY_REGULATION_CHANGE'
);

-- PRD: signal_type 3종 고정
CREATE TYPE signal_type_enum AS ENUM ('DIRECT', 'INDUSTRY', 'ENVIRONMENT');
CREATE TYPE impact_direction_enum AS ENUM ('RISK', 'OPPORTUNITY', 'NEUTRAL');
CREATE TYPE impact_strength_enum AS ENUM ('HIGH', 'MED', 'LOW');

-- 14.7.2 Evidence Types
CREATE TYPE evidence_type_enum AS ENUM ('INTERNAL_FIELD', 'DOC', 'EXTERNAL');
CREATE TYPE ref_type_enum AS ENUM ('SNAPSHOT_KEYPATH', 'DOC_PAGE', 'URL');

-- 14.9 Job Types
CREATE TYPE job_type_enum AS ENUM ('ANALYZE', 'EXTERNAL_COLLECT');
CREATE TYPE job_status_enum AS ENUM ('QUEUED', 'RUNNING', 'DONE', 'FAILED');
CREATE TYPE progress_step_enum AS ENUM (
    'SNAPSHOT', 'DOC_INGEST', 'EXTERNAL', 'UNIFIED_CONTEXT', 'SIGNAL', 'INDEX'
);

-- Industry Group
CREATE TYPE industry_group_enum AS ENUM ('MANUFACTURING', 'CONSTRUCTION', 'WHOLESALE', 'OTHER');

-- ============================================
-- 14.1 Core Master
-- ============================================

-- 14.1.1 corp (기업 마스터)
CREATE TABLE corp (
    corp_id VARCHAR(20) PRIMARY KEY,          -- 고객번호 (예: '8001-3719240')
    corp_reg_no VARCHAR(20) NOT NULL,         -- 법인번호
    corp_name VARCHAR(200) NOT NULL,
    biz_no VARCHAR(12),                       -- 사업자등록번호 (가라 허용)
    industry_code VARCHAR(10) NOT NULL,       -- 업종코드 (예: 'C26')
    ceo_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE corp IS '기업 마스터 테이블 (PRD 14.1.1)';
COMMENT ON COLUMN corp.corp_id IS '고객번호 (PK) - 예: 8001-3719240';
COMMENT ON COLUMN corp.corp_reg_no IS '법인번호';
COMMENT ON COLUMN corp.biz_no IS '사업자등록번호 (가라 허용)';

-- 14.1.2 industry_master (업종 마스터)
CREATE TABLE industry_master (
    industry_code VARCHAR(10) PRIMARY KEY,
    industry_name VARCHAR(100) NOT NULL,
    industry_group industry_group_enum NOT NULL,
    is_sensitive BOOLEAN DEFAULT FALSE,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE industry_master IS '업종 마스터 테이블 (PRD 14.1.2)';

-- ============================================
-- 14.2 Internal Snapshot (Main) - 핵심!
-- ============================================

-- 14.2.1 rkyc_internal_snapshot
CREATE TABLE rkyc_internal_snapshot (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id),
    snapshot_version INTEGER NOT NULL,        -- 버전 증가
    snapshot_json JSONB NOT NULL,             -- 7장 스키마 준수
    snapshot_hash VARCHAR(64) NOT NULL,       -- sha256(snapshot_json)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(corp_id, snapshot_version)
);

COMMENT ON TABLE rkyc_internal_snapshot IS 'Internal Snapshot 버전 관리 (PRD 14.2.1, 7장)';
COMMENT ON COLUMN rkyc_internal_snapshot.snapshot_json IS 'PRD 7장 스키마 준수 JSON';
COMMENT ON COLUMN rkyc_internal_snapshot.snapshot_hash IS 'sha256(snapshot_json) - 변경 감지용';

-- 14.2.2 rkyc_internal_snapshot_latest (최신 포인터)
CREATE TABLE rkyc_internal_snapshot_latest (
    corp_id VARCHAR(20) PRIMARY KEY REFERENCES corp(corp_id),
    snapshot_id UUID NOT NULL REFERENCES rkyc_internal_snapshot(snapshot_id),
    snapshot_version INTEGER NOT NULL,
    snapshot_hash VARCHAR(64) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE rkyc_internal_snapshot_latest IS '최신 Snapshot 포인터 (PRD 14.2.2)';

-- ============================================
-- 14.3 Documents (Sub)
-- ============================================

-- 14.3.1 rkyc_document
CREATE TABLE rkyc_document (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id),
    doc_type doc_type_enum NOT NULL,
    storage_provider VARCHAR(20) DEFAULT 'FILESYS',
    storage_path TEXT,
    file_hash VARCHAR(64),                    -- 변경 감지용
    page_count INTEGER,
    captured_at TIMESTAMPTZ,
    ingest_status ingest_status_enum DEFAULT 'PENDING',
    last_ingested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE rkyc_document IS '제출 문서 메타데이터 (PRD 14.3.1)';

-- 14.3.2 rkyc_document_page
CREATE TABLE rkyc_document_page (
    page_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL REFERENCES rkyc_document(doc_id),
    page_no INTEGER NOT NULL,                 -- 1-based
    image_path TEXT,
    width INTEGER,
    height INTEGER,
    UNIQUE(doc_id, page_no)
);

COMMENT ON TABLE rkyc_document_page IS '문서 페이지별 메타데이터 (PRD 14.3.2)';

-- ============================================
-- 14.4 Doc Facts (Extractor Output)
-- ============================================

-- 14.4.1 rkyc_fact
CREATE TABLE rkyc_fact (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id),
    doc_id UUID NOT NULL REFERENCES rkyc_document(doc_id),
    doc_type doc_type_enum NOT NULL,
    fact_type VARCHAR(50) NOT NULL,           -- SHAREHOLDER, OFFICER, CAPITAL, etc.
    field_key VARCHAR(100) NOT NULL,
    field_value_text TEXT,
    field_value_num NUMERIC,
    field_value_json JSONB,
    confidence confidence_level NOT NULL,
    evidence_snippet TEXT,                    -- <= 400자
    evidence_page_no INTEGER,
    evidence_bbox JSONB,
    extracted_by VARCHAR(100),                -- model/version
    extracted_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE rkyc_fact IS '문서 추출 팩트 (PRD 14.4.1)';
COMMENT ON COLUMN rkyc_fact.fact_type IS 'SHAREHOLDER, OFFICER, CAPITAL 등';
COMMENT ON COLUMN rkyc_fact.evidence_snippet IS '근거 스니펫 (최대 400자)';

-- ============================================
-- 14.5 External Events
-- ============================================

-- 14.5.1 rkyc_external_event
CREATE TABLE rkyc_external_event (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type source_type_enum NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    url TEXT NOT NULL,
    url_hash VARCHAR(64) NOT NULL,            -- sha256(url)
    publisher VARCHAR(100),
    published_at TIMESTAMPTZ NOT NULL,
    tags TEXT[],
    event_type external_event_type_enum NOT NULL,
    event_signature VARCHAR(64) NOT NULL UNIQUE,  -- 중복 방지
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE rkyc_external_event IS '외부 이벤트 (뉴스, 공시 등) (PRD 14.5.1)';
COMMENT ON COLUMN rkyc_external_event.event_signature IS '중복 방지용 sha256 해시';

-- 14.5.2 rkyc_external_event_target (기업↔이벤트 매핑)
CREATE TABLE rkyc_external_event_target (
    target_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES rkyc_external_event(event_id),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id),
    match_basis match_basis_enum NOT NULL,
    score_hint INTEGER,                       -- 정렬 힌트 (점수화 아님)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_id, corp_id)
);

COMMENT ON TABLE rkyc_external_event_target IS '외부 이벤트 ↔ 기업 매핑 (PRD 14.5.2)';

-- ============================================
-- 14.6 Unified Context
-- ============================================

-- 14.6.1 rkyc_unified_context
CREATE TABLE rkyc_unified_context (
    context_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id),
    snapshot_id UUID NOT NULL REFERENCES rkyc_internal_snapshot(snapshot_id),
    context_hash VARCHAR(64) NOT NULL,        -- 중복 방지
    context_json JSONB NOT NULL,              -- snapshot + doc_fact refs + external refs
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE rkyc_unified_context IS '통합 컨텍스트 (PRD 14.6.1)';

-- ============================================
-- 14.7 Signals / Evidence / Index - 핵심!
-- ============================================

-- 14.7.1 rkyc_signal
CREATE TABLE rkyc_signal (
    signal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id),
    signal_type signal_type_enum NOT NULL,    -- DIRECT, INDUSTRY, ENVIRONMENT
    event_type event_type_enum NOT NULL,      -- 10종 고정
    event_signature VARCHAR(64) NOT NULL,     -- sha256(signal_type + event_type + refs)
    snapshot_version INTEGER NOT NULL,
    impact_direction impact_direction_enum NOT NULL,
    impact_strength impact_strength_enum NOT NULL,
    confidence confidence_level NOT NULL,
    summary TEXT NOT NULL,
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- 중복 방지 UNIQUE 제약
    UNIQUE(corp_id, signal_type, snapshot_version, event_signature)
);

COMMENT ON TABLE rkyc_signal IS '시그널 (PRD 14.7.1, 9장, 10장)';
COMMENT ON COLUMN rkyc_signal.signal_type IS 'DIRECT: 직접 리스크, INDUSTRY: 산업 리스크, ENVIRONMENT: 환경 리스크';
COMMENT ON COLUMN rkyc_signal.event_type IS 'PRD 9장 정의 10종 이벤트 타입';
COMMENT ON COLUMN rkyc_signal.event_signature IS '중복 방지용 sha256 해시';

-- 14.7.2 rkyc_evidence
CREATE TABLE rkyc_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id) ON DELETE CASCADE,
    evidence_type evidence_type_enum NOT NULL,
    ref_type ref_type_enum NOT NULL,
    ref_value TEXT NOT NULL,                  -- 예: /credit/loan_summary/overdue_flag, doc_id:page_no, url_hash
    snippet TEXT,
    meta JSONB,                               -- page_no, bbox, published_at 등
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE rkyc_evidence IS '시그널 근거 (PRD 14.7.2)';
COMMENT ON COLUMN rkyc_evidence.ref_value IS 'SNAPSHOT_KEYPATH: /credit/loan_summary/..., DOC_PAGE: doc_id:page_no, URL: url_hash';

-- 14.7.3 rkyc_signal_index (Dashboard 전용, 조인 금지!)
CREATE TABLE rkyc_signal_index (
    index_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL,
    corp_name VARCHAR(200) NOT NULL,          -- denormalized
    industry_code VARCHAR(10) NOT NULL,       -- denormalized
    signal_type signal_type_enum NOT NULL,
    event_type event_type_enum NOT NULL,
    impact_direction impact_direction_enum NOT NULL,
    impact_strength impact_strength_enum NOT NULL,
    confidence confidence_level NOT NULL,
    title VARCHAR(500) NOT NULL,              -- 짧은 요약 제목
    summary_short TEXT,                       -- 짧은 요약
    evidence_count INTEGER NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,         -- 정렬 기준
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE rkyc_signal_index IS 'Dashboard 전용 인덱스 (조인 금지!) (PRD 14.7.3)';

-- 14.7.4 rkyc_dashboard_summary (선택, 1row)
CREATE TABLE rkyc_dashboard_summary (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    counts_json JSONB NOT NULL,               -- type별 count, risk/opportunity count
    top_signals JSONB                         -- 상위 n개
);

COMMENT ON TABLE rkyc_dashboard_summary IS 'Dashboard 요약 (1 row) (PRD 14.7.4)';

-- ============================================
-- 14.8 Insight Memory
-- ============================================

-- 14.8.1 rkyc_case_index
CREATE TABLE rkyc_case_index (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id),
    industry_code VARCHAR(10),
    signal_type signal_type_enum NOT NULL,
    event_type event_type_enum NOT NULL,
    impact_direction impact_direction_enum NOT NULL,
    impact_strength impact_strength_enum NOT NULL,
    keywords TEXT[],
    summary TEXT NOT NULL,
    evidence_refs JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE rkyc_case_index IS '인사이트 메모리 케이스 인덱스 (PRD 14.8.1)';

-- ============================================
-- 14.9 Jobs (대회용)
-- ============================================

-- 14.9.1 rkyc_job
CREATE TABLE rkyc_job (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type job_type_enum NOT NULL,
    corp_id VARCHAR(20) REFERENCES corp(corp_id),
    status job_status_enum DEFAULT 'QUEUED',
    progress_step progress_step_enum,
    progress_percent INTEGER DEFAULT 0,
    error_code VARCHAR(50),
    error_message TEXT,
    queued_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

COMMENT ON TABLE rkyc_job IS '분석 작업 (PRD 14.9.1)';

-- ============================================
-- INDEXES (PRD 13장)
-- ============================================

-- rkyc_signal_index (Dashboard 성능)
CREATE INDEX idx_signal_index_type_detected ON rkyc_signal_index(signal_type, detected_at DESC);
CREATE INDEX idx_signal_index_corp_detected ON rkyc_signal_index(corp_id, detected_at DESC);
CREATE INDEX idx_signal_index_direction_detected ON rkyc_signal_index(impact_direction, detected_at DESC);
CREATE INDEX idx_signal_index_strength ON rkyc_signal_index(impact_strength, detected_at DESC);

-- rkyc_signal
CREATE UNIQUE INDEX idx_signal_unique ON rkyc_signal(corp_id, signal_type, snapshot_version, event_signature);
CREATE INDEX idx_signal_corp ON rkyc_signal(corp_id, created_at DESC);
CREATE INDEX idx_signal_type ON rkyc_signal(signal_type, created_at DESC);

-- rkyc_evidence
CREATE INDEX idx_evidence_signal ON rkyc_evidence(signal_id);

-- rkyc_external_event
CREATE INDEX idx_external_event_published ON rkyc_external_event(published_at DESC);
CREATE INDEX idx_external_event_type ON rkyc_external_event(event_type);

-- rkyc_external_event_target
CREATE INDEX idx_event_target_corp ON rkyc_external_event_target(corp_id, created_at DESC);

-- rkyc_internal_snapshot
CREATE INDEX idx_snapshot_corp_version ON rkyc_internal_snapshot(corp_id, snapshot_version DESC);

-- rkyc_document
CREATE INDEX idx_document_corp ON rkyc_document(corp_id);
CREATE INDEX idx_document_status ON rkyc_document(ingest_status);

-- rkyc_fact
CREATE INDEX idx_fact_corp ON rkyc_fact(corp_id);
CREATE INDEX idx_fact_doc ON rkyc_fact(doc_id);

-- corp
CREATE INDEX idx_corp_industry ON corp(industry_code);

-- rkyc_job
CREATE INDEX idx_job_status ON rkyc_job(status);
CREATE INDEX idx_job_corp ON rkyc_job(corp_id);

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
$$ LANGUAGE 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_corp_updated_at
    BEFORE UPDATE ON corp
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_snapshot_latest_updated_at
    BEFORE UPDATE ON rkyc_internal_snapshot_latest
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_signal_updated_at
    BEFORE UPDATE ON rkyc_signal
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_signal_index_updated_at
    BEFORE UPDATE ON rkyc_signal_index
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- VIEWS (편의용)
-- ============================================

-- 최신 Snapshot과 기업 정보 조인 뷰
CREATE VIEW v_corp_latest_snapshot AS
SELECT
    c.corp_id,
    c.corp_name,
    c.industry_code,
    c.ceo_name,
    l.snapshot_id,
    l.snapshot_version,
    s.snapshot_json,
    l.updated_at AS snapshot_updated_at
FROM corp c
LEFT JOIN rkyc_internal_snapshot_latest l ON c.corp_id = l.corp_id
LEFT JOIN rkyc_internal_snapshot s ON l.snapshot_id = s.snapshot_id;

-- Signal과 Evidence 카운트 뷰
CREATE VIEW v_signal_with_evidence_count AS
SELECT
    s.*,
    c.corp_name,
    COUNT(e.evidence_id) AS evidence_count
FROM rkyc_signal s
JOIN corp c ON s.corp_id = c.corp_id
LEFT JOIN rkyc_evidence e ON s.signal_id = e.signal_id
GROUP BY s.signal_id, c.corp_name;

-- ============================================
-- COMMENTS SUMMARY
-- ============================================

COMMENT ON SCHEMA public IS 'rKYC Schema v2.0 - PRD 14장 기준 재설계';
