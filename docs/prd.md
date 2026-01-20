rKYC 프로젝트 완전 설계 명세서 v0.2
Claude Code 실행용 Full-Stack 개발 가이드

PART 1: PROJECT OVERVIEW
1.1 프로젝트 정의
프로젝트명: rKYC (Really Know Your Customer)
목적: 은행 내부 데이터 + 외부 공개 데이터를 결합하여 
      사전 생성된 Signal을 직원에게 즉시 제공하는 AI 기반 인텔리전스 시스템

현재 상태:
├── Frontend: ✅ 완료 (React + Vite + shadcn/ui)
│   └── URL: https://rkyc.vercel.app/
│   └── 소스: /home/claude/rkyc-main/
├── Backend: ❌ 미구현 (Mock 데이터 사용 중)
├── Database: ❌ 미구현
└── Worker/Job: ❌ 미구현

1.2 개발 범위
이 문서의 작업 범위:

1. Backend API 개발 (FastAPI)
   ├── DB Schema 설계 및 DDL
   ├── SQLAlchemy 모델
   ├── Pydantic 스키마
   ├── 조회 API 엔드포인트
   └── Demo Job Trigger API

2. Worker/Job 시스템 (Celery + Redis)
   ├── Analyze Job Pipeline
   ├── LLM Prompt Chain
   └── Signal 생성 로직

3. Frontend API 연동
   ├── Mock 데이터 파일 삭제
   ├── API Client 생성 (React Query)
   ├── 타입 정의 업데이트
   └── 컴포넌트 API 연동

4. Demo Mode 구현
   ├── 환경변수 기반 UI 토글
   ├── Demo 패널 컴포넌트
   └── Job Trigger 연동

1.3 절대 준수 사항 (Guardrails)
⛔ NEVER (절대 금지):
├── UI 접속/조회 시 LLM 호출 트리거
├── API 서버에서 LLM 호출 (LLM Key 물리적 부재)
├── 추정/예측/단정 표현 ("~일 것이다", "반드시", "즉시 조치")
├── Evidence 없는 Signal 저장
└── Frontend에서 직접 LLM API 호출

✅ ALWAYS (필수):
├── Signal은 Background Worker에서만 사전 생성
├── UI/API는 저장된 결과 조회만
├── 모든 Signal은 Evidence(근거) 최소 1개 필수
├── LLM 호출은 Worker/Job Runner에서만
└── 물리적 아키텍처 분리 (API ≠ Worker)


PART 2: SYSTEM ARCHITECTURE
2.1 High-Level Architecture
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Vercel)                              │
│                                                                             │
│   React + Vite + TypeScript + shadcn/ui + React Query                       │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  Pages:                                                             │  │
│   │  ├── / (SignalInbox)        ← GET /api/v1/dashboard/signals         │  │
│   │  ├── /briefing              ← GET /api/v1/dashboard/summary         │  │
│   │  ├── /corporations          ← GET /api/v1/corp/search               │  │
│   │  ├── /corporates/:id        ← GET /api/v1/corp/{id}/snapshot/latest │  │
│   │  ├── /signals/:id           ← GET /api/v1/signals/{id}              │  │
│   │  ├── /signals/direct        ← GET /api/v1/dashboard/signals?type=   │  │
│   │  ├── /signals/industry      ← GET /api/v1/dashboard/signals?type=   │  │
│   │  ├── /signals/environment   ← GET /api/v1/dashboard/signals?type=   │  │
│   │  └── /analytics             ← GET /api/v1/jobs (Demo Mode)          │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      │ HTTP (REST API)                      │
│                                      ▼                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND API SERVER                                │
│                                                                             │
│   FastAPI + SQLAlchemy + Pydantic                                           │
│   ⚠️ LLM Key 없음 - 조회 전용                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  Endpoints:                                                         │  │
│   │  ├── GET  /api/v1/dashboard/summary                                 │  │
│   │  ├── GET  /api/v1/dashboard/signals                                 │  │
│   │  ├── GET  /api/v1/corp/search                                       │  │
│   │  ├── GET  /api/v1/corp/{corp_id}/snapshot/latest                    │  │
│   │  ├── GET  /api/v1/corp/{corp_id}/signals                            │  │
│   │  ├── GET  /api/v1/corp/{corp_id}/documents                          │  │
│   │  ├── GET  /api/v1/signals/{signal_id}                               │  │
│   │  ├── POST /api/v1/jobs/analyze/run  [Demo Only, X-DEMO-TOKEN]       │  │
│   │  └── GET  /api/v1/jobs/{job_id}                                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      │ SQLAlchemy                           │
│                                      ▼                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE (PostgreSQL)                          │
│                                                                             │
│   Tables:                                                                   │
│   ├── corp, industry_master                      (Master)                   │
│   ├── rkyc_internal_snapshot, _latest            (Snapshot)                 │
│   ├── rkyc_document, _page, rkyc_fact            (Documents)                │
│   ├── rkyc_external_event, _target               (External)                 │
│   ├── rkyc_unified_context                       (Context)                  │
│   ├── rkyc_signal, rkyc_evidence                 (Signals)                  │
│   ├── rkyc_signal_index, rkyc_dashboard_summary  (Dashboard Cache)          │
│   ├── rkyc_case_index                            (Insight Memory)           │
│   └── rkyc_job                                   (Job Management)           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           WORKER (Celery + Redis)                           │
│                                                                             │
│   ✅ LLM Key 있음 - Signal 생성 담당                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  Analyze Job Pipeline (8 Steps):                                    │  │
│   │                                                                     │  │
│   │  Step 1: SNAPSHOT ───────────────────── Internal → JSON             │  │
│   │  Step 2: DOC_INGEST ─── 🔗 Prompt 1 ─── OCR → Facts                 │  │
│   │  Step 3: EXTERNAL ───── 🔗 Prompt 2 ─── News → Summary              │  │
│   │  Step 4: CONTEXT ────── 🔗 Prompt 3 ─── Combine → Compress          │  │
│   │  Step 5: SIGNAL ─────── 🔗 Prompt 4,5,6 ─ Context → Signals (병렬)  │  │
│   │  Step 6: VALIDATION ─────────────────── Evidence Check              │  │
│   │  Step 7: INDEX ──────── 🔗 Prompt 7 ─── Dashboard Briefing          │  │
│   │  Step 8: INSIGHT ────── 🔗 Prompt 8 ─── Past Case Summary           │  │
│   │                                                                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

2.2 Physical Constraints
Component
LLM API Key
Database
Role
Frontend
❌ 없음
❌ 없음
Read-only UI
API Server
❌ 없음
✅ 있음
조회 API + Job Trigger
Worker
✅ 있음
✅ 있음
LLM Prompt Chain 실행


PART 3: DATABASE SCHEMA
3.1 Complete DDL
-- ============================================================
-- PART 3.1.1: Core Master Tables
-- ============================================================

-- 법인 마스터
CREATE TABLE corp (
    corp_id VARCHAR(50) PRIMARY KEY,
    corp_reg_no VARCHAR(50) NOT NULL,
    corp_name VARCHAR(200) NOT NULL,
    biz_no VARCHAR(20),
    industry_code VARCHAR(10) NOT NULL,
    ceo_name VARCHAR(100) NOT NULL,
    employee_count INT,
    founded_year INT,
    headquarters VARCHAR(200),
    main_business TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 업종 마스터
CREATE TABLE industry_master (
    industry_code VARCHAR(10) PRIMARY KEY,
    industry_name VARCHAR(200) NOT NULL,
    industry_group VARCHAR(50) NOT NULL,
    is_sensitive BOOLEAN DEFAULT FALSE,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_industry_group CHECK (
        industry_group IN ('MANUFACTURING', 'CONSTRUCTION', 'WHOLESALE', 'SERVICE', 'OTHER')
    )
);

-- 은행 거래 관계
CREATE TABLE corp_bank_relationship (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(50) NOT NULL REFERENCES corp(corp_id),
    has_relationship BOOLEAN DEFAULT TRUE,
    deposit_balance BIGINT DEFAULT 0,
    loan_balance BIGINT DEFAULT 0,
    fx_volume_yearly BIGINT DEFAULT 0,
    has_retirement_pension BOOLEAN DEFAULT FALSE,
    has_payroll_service BOOLEAN DEFAULT FALSE,
    has_corporate_card BOOLEAN DEFAULT FALSE,
    relationship_since DATE,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_corp_relationship UNIQUE (corp_id)
);

-- 임원 정보
CREATE TABLE corp_executive (
    executive_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(50) NOT NULL REFERENCES corp(corp_id),
    name VARCHAR(100) NOT NULL,
    position VARCHAR(100) NOT NULL,
    is_key_man BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 주주 정보
CREATE TABLE corp_shareholder (
    shareholder_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(50) NOT NULL REFERENCES corp(corp_id),
    name VARCHAR(200) NOT NULL,
    ownership_ratio DECIMAL(5,2) NOT NULL,
    shareholder_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_shareholder_type CHECK (
        shareholder_type IN ('INDIVIDUAL', 'CORPORATION', 'INSTITUTION')
    )
);

-- 재무 스냅샷
CREATE TABLE corp_financial_snapshot (
    financial_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(50) NOT NULL REFERENCES corp(corp_id),
    fiscal_year INT NOT NULL,
    revenue BIGINT,
    operating_profit BIGINT,
    net_profit BIGINT,
    total_assets BIGINT,
    total_liabilities BIGINT,
    equity BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_corp_fiscal_year UNIQUE (corp_id, fiscal_year)
);

-- ============================================================
-- PART 3.1.2: Internal Snapshot Tables
-- ============================================================

-- Internal Snapshot (버전 관리, Append-only)
CREATE TABLE rkyc_internal_snapshot (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(50) NOT NULL REFERENCES corp(corp_id),
    snapshot_version INT NOT NULL,
    snapshot_json JSONB NOT NULL,
    snapshot_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_snapshot_version UNIQUE (corp_id, snapshot_version)
);

-- Latest Snapshot Pointer (Upsert)
CREATE TABLE rkyc_internal_snapshot_latest (
    corp_id VARCHAR(50) PRIMARY KEY REFERENCES corp(corp_id),
    snapshot_id UUID NOT NULL REFERENCES rkyc_internal_snapshot(snapshot_id),
    snapshot_version INT NOT NULL,
    snapshot_hash VARCHAR(64) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PART 3.1.3: Document Tables
-- ============================================================

-- KYC 문서
CREATE TABLE rkyc_document (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(50) NOT NULL REFERENCES corp(corp_id),
    doc_type VARCHAR(20) NOT NULL,
    storage_path TEXT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    page_count INT DEFAULT 1,
    ingest_status VARCHAR(20) DEFAULT 'PENDING',
    captured_at TIMESTAMPTZ,
    last_ingested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_doc_type CHECK (
        doc_type IN ('BIZ_REG', 'REGISTRY', 'SHAREHOLDERS', 'AOI', 'FIN_STATEMENT')
    ),
    CONSTRAINT chk_ingest_status CHECK (
        ingest_status IN ('PENDING', 'RUNNING', 'DONE', 'FAILED')
    )
);

-- 문서 페이지
CREATE TABLE rkyc_document_page (
    page_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL REFERENCES rkyc_document(doc_id) ON DELETE CASCADE,
    page_no INT NOT NULL,
    image_path TEXT NOT NULL,
    ocr_text TEXT,
    width INT,
    height INT,
    
    CONSTRAINT uq_doc_page UNIQUE (doc_id, page_no)
);

-- 문서에서 추출된 Facts
CREATE TABLE rkyc_fact (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(50) NOT NULL REFERENCES corp(corp_id),
    doc_id UUID NOT NULL REFERENCES rkyc_document(doc_id) ON DELETE CASCADE,
    doc_type VARCHAR(20) NOT NULL,
    fact_type VARCHAR(50) NOT NULL,
    field_key VARCHAR(100) NOT NULL,
    field_value_text TEXT,
    field_value_num NUMERIC,
    field_value_json JSONB,
    confidence VARCHAR(10) NOT NULL,
    evidence_snippet TEXT,
    evidence_page_no INT,
    evidence_bbox JSONB,
    extracted_by VARCHAR(100),
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_fact_confidence CHECK (confidence IN ('HIGH', 'MED', 'LOW'))
);

-- ============================================================
-- PART 3.1.4: External Event Tables
-- ============================================================

-- 외부 이벤트
CREATE TABLE rkyc_external_event (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(20) NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    url TEXT,
    url_hash VARCHAR(64),
    publisher VARCHAR(200),
    published_at TIMESTAMPTZ NOT NULL,
    tags TEXT[],
    event_type VARCHAR(50),
    event_signature VARCHAR(64) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_source_type CHECK (
        source_type IN ('NEWS', 'DISCLOSURE', 'POLICY', 'REPORT')
    ),
    CONSTRAINT chk_event_type CHECK (
        event_type IS NULL OR event_type IN ('INDUSTRY_SHOCK', 'POLICY_REGULATION_CHANGE')
    )
);

-- 외부 이벤트 ↔ 법인 매핑
CREATE TABLE rkyc_external_event_target (
    target_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES rkyc_external_event(event_id) ON DELETE CASCADE,
    corp_id VARCHAR(50) NOT NULL REFERENCES corp(corp_id),
    match_basis VARCHAR(50) NOT NULL,
    score_hint INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_event_corp UNIQUE (event_id, corp_id),
    CONSTRAINT chk_match_basis CHECK (
        match_basis IN ('INDUSTRY_CODE', 'INDUSTRY_GROUP', 'MANUAL_SEED', 'KEYWORD')
    )
);

-- ============================================================
-- PART 3.1.5: Context & Signal Tables
-- ============================================================

-- Unified Context
CREATE TABLE rkyc_unified_context (
    context_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(50) NOT NULL REFERENCES corp(corp_id),
    snapshot_id UUID NOT NULL REFERENCES rkyc_internal_snapshot(snapshot_id),
    context_json JSONB NOT NULL,
    context_hash VARCHAR(64) NOT NULL,
    token_count INT,
    truncated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Signal
CREATE TABLE rkyc_signal (
    signal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(50) NOT NULL REFERENCES corp(corp_id),
    signal_type VARCHAR(20) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_signature VARCHAR(64) NOT NULL,
    snapshot_version INT NOT NULL,
    impact_direction VARCHAR(20) NOT NULL,
    impact_strength VARCHAR(10) NOT NULL,
    confidence VARCHAR(10) NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary TEXT NOT NULL,
    detail_category VARCHAR(100),
    relevance_note TEXT,
    ai_summary TEXT,
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_signal_type CHECK (signal_type IN ('DIRECT', 'INDUSTRY', 'ENVIRONMENT')),
    CONSTRAINT chk_event_type CHECK (event_type IN (
        'KYC_REFRESH', 'INTERNAL_RISK_GRADE_CHANGE', 'OVERDUE_FLAG_ON',
        'LOAN_EXPOSURE_CHANGE', 'COLLATERAL_CHANGE', 'OWNERSHIP_CHANGE',
        'GOVERNANCE_CHANGE', 'FINANCIAL_STATEMENT_UPDATE',
        'INDUSTRY_SHOCK', 'POLICY_REGULATION_CHANGE'
    )),
    CONSTRAINT chk_impact_direction CHECK (impact_direction IN ('RISK', 'OPPORTUNITY', 'NEUTRAL')),
    CONSTRAINT chk_impact_strength CHECK (impact_strength IN ('HIGH', 'MED', 'LOW')),
    CONSTRAINT chk_signal_confidence CHECK (confidence IN ('HIGH', 'MED', 'LOW')),
    CONSTRAINT uq_signal_signature UNIQUE (corp_id, signal_type, snapshot_version, event_signature)
);

-- Evidence
CREATE TABLE rkyc_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id) ON DELETE CASCADE,
    evidence_type VARCHAR(20) NOT NULL,
    ref_type VARCHAR(30) NOT NULL,
    ref_value TEXT NOT NULL,
    title VARCHAR(500),
    snippet TEXT,
    source_name VARCHAR(200),
    source_url TEXT,
    published_at TIMESTAMPTZ,
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_evidence_type CHECK (evidence_type IN ('INTERNAL_FIELD', 'DOC', 'EXTERNAL')),
    CONSTRAINT chk_ref_type CHECK (ref_type IN ('SNAPSHOT_KEYPATH', 'DOC_PAGE', 'URL'))
);

-- ============================================================
-- PART 3.1.6: Dashboard & Index Tables
-- ============================================================

-- Signal Index (Dashboard 전용, 비정규화)
CREATE TABLE rkyc_signal_index (
    index_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id) ON DELETE CASCADE,
    corp_id VARCHAR(50) NOT NULL,
    corp_name VARCHAR(200) NOT NULL,
    industry_code VARCHAR(10) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    impact_direction VARCHAR(20) NOT NULL,
    impact_strength VARCHAR(10) NOT NULL,
    confidence VARCHAR(10) NOT NULL,
    title VARCHAR(500) NOT NULL,
    summary_short TEXT,
    evidence_count INT DEFAULT 0,
    detected_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'new',
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_index_status CHECK (status IN ('new', 'review', 'resolved'))
);

-- Dashboard Summary
CREATE TABLE rkyc_dashboard_summary (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_date DATE NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    briefing_text TEXT,
    counts_json JSONB,
    highlights JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_summary_date UNIQUE (summary_date)
);

-- Insight Memory
CREATE TABLE rkyc_case_index (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(50) NOT NULL,
    industry_code VARCHAR(10) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    impact_direction VARCHAR(20) NOT NULL,
    impact_strength VARCHAR(10) NOT NULL,
    keywords TEXT[],
    summary TEXT,
    similar_case_count INT DEFAULT 0,
    impact_classification VARCHAR(20),
    evidence_refs JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_impact_classification CHECK (impact_classification IN ('SHORT_TERM', 'MID_TERM', 'LONG_TERM'))
);

-- ============================================================
-- PART 3.1.7: Job Management
-- ============================================================

-- Job 상태 관리
CREATE TABLE rkyc_job (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(30) NOT NULL,
    corp_id VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'QUEUED',
    progress_step VARCHAR(50),
    progress_percent INT DEFAULT 0,
    error_code VARCHAR(50),
    error_message TEXT,
    result_summary JSONB,
    queued_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    
    CONSTRAINT chk_job_type CHECK (job_type IN ('ANALYZE', 'EXTERNAL_COLLECT', 'FULL_REFRESH')),
    CONSTRAINT chk_job_status CHECK (status IN ('QUEUED', 'RUNNING', 'DONE', 'PARTIAL_SUCCESS', 'FAILED')),
    CONSTRAINT chk_progress_step CHECK (progress_step IS NULL OR progress_step IN (
        'SNAPSHOT', 'DOC_INGEST', 'EXTERNAL', 'UNIFIED_CONTEXT', 
        'SIGNAL_DIRECT', 'SIGNAL_INDUSTRY', 'SIGNAL_ENVIRONMENT',
        'VALIDATION', 'INDEX', 'INSIGHT_MEMORY'
    ))
);

-- ============================================================
-- PART 3.1.8: Indexes
-- ============================================================

CREATE INDEX idx_signal_index_type_detected ON rkyc_signal_index(signal_type, detected_at DESC);
CREATE INDEX idx_signal_index_corp_detected ON rkyc_signal_index(corp_id, detected_at DESC);
CREATE INDEX idx_signal_index_impact_detected ON rkyc_signal_index(impact_direction, detected_at DESC);
CREATE INDEX idx_signal_index_status ON rkyc_signal_index(status, detected_at DESC);
CREATE INDEX idx_signal_corp_type ON rkyc_signal(corp_id, signal_type, snapshot_version DESC);
CREATE INDEX idx_external_event_published ON rkyc_external_event(published_at DESC);
CREATE INDEX idx_external_target_corp ON rkyc_external_event_target(corp_id, created_at DESC);
CREATE INDEX idx_snapshot_corp_version ON rkyc_internal_snapshot(corp_id, snapshot_version DESC);
CREATE INDEX idx_fact_corp_doctype ON rkyc_fact(corp_id, doc_type);
CREATE INDEX idx_job_status ON rkyc_job(status, queued_at DESC);
CREATE INDEX idx_job_corp ON rkyc_job(corp_id, queued_at DESC);
CREATE INDEX idx_corp_name ON corp(corp_name);
CREATE INDEX idx_corp_biz_no ON corp(biz_no);

3.2 Internal Snapshot JSON Schema v1.0
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "internal_snapshot_v1.json",
  "title": "rKYC Internal Snapshot JSON v1.0",
  "type": "object",
  "required": ["schema_version", "corp", "relationship", "credit", "collateral", "derived_hints"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "string", "const": "v1.0" },
    "corp": {
      "type": "object",
      "required": ["corp_id", "corp_reg_no", "corp_name", "industry_code", "ceo_name", "kyc_status"],
      "additionalProperties": false,
      "properties": {
        "corp_id": { "type": "string", "minLength": 1 },
        "corp_reg_no": { "type": "string", "minLength": 1 },
        "corp_name": { "type": "string", "minLength": 1 },
        "biz_no": { "type": "string" },
        "industry_code": { "type": "string", "minLength": 1 },
        "ceo_name": { "type": "string", "minLength": 1 },
        "kyc_status": {
          "type": "object",
          "required": ["is_kyc_completed", "last_kyc_updated", "internal_risk_grade"],
          "additionalProperties": false,
          "properties": {
            "is_kyc_completed": { "type": "boolean" },
            "last_kyc_updated": { "type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$" },
            "internal_risk_grade": { "type": "string", "enum": ["LOW", "MED", "HIGH"] }
          }
        }
      }
    },
    "relationship": {
      "type": "object",
      "required": ["has_relationship", "products"],
      "additionalProperties": false,
      "properties": {
        "has_relationship": { "type": "boolean" },
        "products": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "deposit": { "type": "boolean" },
            "loan": { "type": "boolean" },
            "fx": { "type": "boolean" }
          }
        },
        "relationship_since": { "type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$" }
      }
    },
    "credit": {
      "type": "object",
      "required": ["has_loan", "loan_summary"],
      "additionalProperties": false,
      "properties": {
        "has_loan": { "type": "boolean" },
        "loan_summary": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "total_exposure_krw": { "type": "number", "minimum": 0 },
            "overdue_flag": { "type": "boolean" },
            "risk_grade_internal": { "type": "string", "enum": ["LOW", "MED", "HIGH"] }
          }
        }
      }
    },
    "collateral": {
      "type": "object",
      "required": ["has_collateral", "collateral_types", "collateral_summary"],
      "additionalProperties": false,
      "properties": {
        "has_collateral": { "type": "boolean" },
        "collateral_types": {
          "type": "array",
          "items": { "type": "string", "enum": ["REAL_ESTATE", "DEPOSIT", "GUARANTEE", "OTHER"] }
        },
        "collateral_summary": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "collateral_count": { "type": "integer", "minimum": 0 }
          }
        }
      }
    },
    "derived_hints": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "industry_group": { 
          "type": "string", 
          "enum": ["MANUFACTURING", "CONSTRUCTION", "WHOLESALE", "SERVICE", "OTHER"] 
        },
        "is_sensitive_industry": { "type": "boolean" }
      }
    }
  }
}


PART 4: BACKEND API SPECIFICATION
4.1 API Overview
Method
Endpoint
Description
Auth
GET
/api/v1/dashboard/summary
대시보드 요약 (브리핑)
-
GET
/api/v1/dashboard/signals
시그널 인덱스 목록
-
GET
/api/v1/corp/search
법인 검색
-
GET
/api/v1/corp/{corp_id}
법인 상세
-
GET
/api/v1/corp/{corp_id}/snapshot/latest
최신 스냅샷
-
GET
/api/v1/corp/{corp_id}/signals
법인별 시그널
-
GET
/api/v1/corp/{corp_id}/insight-memory
인사이트 메모리
-
GET
/api/v1/signals/{signal_id}
시그널 상세 + Evidence
-
POST
/api/v1/jobs/analyze/run
분석 Job 실행
X-DEMO-TOKEN
GET
/api/v1/jobs/{job_id}
Job 상태 조회
-

4.2 Response Schemas (TypeScript)
4.2.1 Dashboard Schemas
```typescript // GET /api/v1/dashboard/summary interface DashboardSummaryResponse { generated_at: string; summary_date: string; briefing_text: string; counts: { total: number; new_today: number; risk_7d: number; opportunity_7d: number; neutral_7d: number; by_type: { direct: number; industry: number; environment: number; }; by_status: { new: number; review: number; resolved: number; }; }; highlights: Array<{ corp_name: string; signal_type: string; impact: string; title: string; }>; }
// GET /api/v1/dashboard/signals interface SignalIndexResponse { signals: SignalIndex[]; next_cursor: string | null; total_count: number; }
interface SignalIndex { id: string; corp_id: string; corp_name: string; industry_code: string; signal_type: "direct" | "industry" | "environment"; event_type: string; status: "new" | "review" | "resolved"; title: string; summary_short: string; impact: "risk" | "opportunity" | "neutral"; impact_strength: "high" | "medium" | "low"; confidence: "high" | "medium" | "low"; evidence_count: number; detected_at: string; } ```
4.2.2 Corporation Schemas
```typescript // GET /api/v1/corp/search interface CorpSearchResponse { corporations: CorpSummary[]; }
interface CorpSummary { corp_id: string; corp_name: string; biz_no: string; industry: string; industry_code: string; ceo_name: string; headquarters: string; has_loan: boolean; recent_signal_count: number; }
// GET /api/v1/corp/{corp_id} interface CorpDetailResponse { corp_id: string; corp_name: string; biz_no: string; corp_reg_no: string; industry: string; industry_code: string; main_business: string; ceo_name: string; employee_count: number; founded_year: number; headquarters: string;
executives: Array<{ name: string; position: string; is_key_man: boolean; }>; shareholders: Array<{ name: string; ownership: string; type: "개인" | "법인" | "기관"; }>;
bank_relationship: { has_relationship: boolean; deposit_balance: string; loan_balance: string; fx_transactions: string; has_retirement_pension: boolean; has_payroll_service: boolean; has_corporate_card: boolean; };
financial_snapshots: Array<{ year: number; revenue: string; operating_profit: string; net_profit: string; total_assets: string; total_liabilities: string; equity: string; }>;
signal_counts: { total: number; direct: number; industry: number; environment: number; risk: number; opportunity: number; };
last_reviewed: string; } ```
4.2.3 Signal Schemas
```typescript // GET /api/v1/signals/{signal_id} interface SignalDetailResponse { id: string; corp_id: string; corp_name: string; signal_type: "direct" | "industry" | "environment"; signal_sub_type: "news" | "financial" | "regulatory" | "governance" | "market" | "macro"; event_type: string; status: "new" | "review" | "resolved"; title: string; summary: string; ai_summary: string; source: string; source_url?: string; detected_at: string; detail_category: string; relevance_note?: string; related_corporations?: string[];
impact: "risk" | "opportunity" | "neutral"; impact_strength: "high" | "medium" | "low"; confidence: "high" | "medium" | "low"; source_type: "internal" | "external" | "mixed"; event_classification: string;
evidences: Evidence[];
has_loan_relationship?: boolean; loan_risk_insight?: string;
past_case_stats?: { similar_cases: number; short_term_only: number; escalated_to_mid_term: number; }; }
interface Evidence { id: string; evidence_type: "INTERNAL_FIELD" | "DOC" | "EXTERNAL"; source_type: "news" | "disclosure" | "report" | "regulation" | "internal"; title: string; snippet: string; source_name: string; source_url?: string; published_at: string; } ```
4.2.4 Job Schemas
```typescript // POST /api/v1/jobs/analyze/run interface JobTriggerRequest { corp_id: string; }
interface JobTriggerResponse { job_id: string; job_type: "ANALYZE"; corp_id: string; status: "QUEUED"; queued_at: string; }
// GET /api/v1/jobs/{job_id} interface JobStatusResponse { job_id: string; job_type: "ANALYZE" | "EXTERNAL_COLLECT"; corp_id: string; status: "QUEUED" | "RUNNING" | "DONE" | "PARTIAL_SUCCESS" | "FAILED"; progress: { step: string; percent: number; }; started_at?: string; finished_at?: string; error?: { code: string; message: string; }; result_summary?: { signals_created: number; signals_by_type: { direct: number; industry: number; environment: number; }; }; } ```

PART 5: FRONTEND INTEGRATION
5.1 Files to Create
5.1.1 src/lib/api-client.ts
```typescript import axios from 'axios';
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const apiClient = axios.create({ baseURL: `${API_BASE_URL}/api/v1`, headers: { 'Content-Type': 'application/json' }, });
const DEMO_TOKEN = import.meta.env.VITE_DEMO_TOKEN;
export const demoApiClient = axios.create({ baseURL: `${API_BASE_URL}/api/v1`, headers: { 'Content-Type': 'application/json', 'X-DEMO-TOKEN': DEMO_TOKEN, }, });
apiClient.interceptors.response.use( (response) => response, (error) => { console.error('API Error:', error.response?.data || error.message); return Promise.reject(error); } ); ```
5.1.2 src/lib/api.ts
```typescript import { apiClient, demoApiClient } from './api-client'; import type { DashboardSummaryResponse, SignalIndexResponse, CorpSearchResponse, CorpDetailResponse, SignalDetailResponse, InsightMemoryResponse, JobTriggerResponse, JobStatusResponse, } from '@/types/api';
// Dashboard export const getDashboardSummary = async (): Promise<DashboardSummaryResponse> => { const { data } = await apiClient.get('/dashboard/summary'); return data; };
export const getDashboardSignals = async (params: { type?: string; impact?: string; status?: string; limit?: number; cursor?: string; }): Promise<SignalIndexResponse> => { const { data } = await apiClient.get('/dashboard/signals', { params }); return data; };
// Corporation export const searchCorporations = async (q: string): Promise<CorpSearchResponse> => { const { data } = await apiClient.get('/corp/search', { params: { q } }); return data; };
export const getCorpDetail = async (corpId: string): Promise<CorpDetailResponse> => { const { data } = await apiClient.get(`/corp/${corpId}`); return data; };
export const getCorpSignals = async (corpId: string, type?: string) => { const { data } = await apiClient.get(`/corp/${corpId}/signals`, { params: { type } }); return data; };
export const getCorpInsightMemory = async (corpId: string): Promise<InsightMemoryResponse> => { const { data } = await apiClient.get(`/corp/${corpId}/insight-memory`); return data; };
// Signal export const getSignalDetail = async (signalId: string): Promise<SignalDetailResponse> => { const { data } = await apiClient.get(`/signals/${signalId}`); return data; };
// Jobs (Demo Mode) export const triggerAnalyzeJob = async (corpId: string): Promise<JobTriggerResponse> => { const { data } = await demoApiClient.post('/jobs/analyze/run', { corp_id: corpId }); return data; };
export const getJobStatus = async (jobId: string): Promise<JobStatusResponse> => { const { data } = await apiClient.get(`/jobs/${jobId}`); return data; }; ```
5.1.3 src/hooks/useApi.ts
```typescript import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'; import * as api from '@/lib/api';
export const useDashboardSummary = () => { return useQuery({ queryKey: ['dashboard', 'summary'], queryFn: api.getDashboardSummary, staleTime: 60 * 1000, }); };
export const useDashboardSignals = (params: { type?: string; impact?: string; status?: string; limit?: number; }) => { return useQuery({ queryKey: ['dashboard', 'signals', params], queryFn: () => api.getDashboardSignals(params), staleTime: 30 * 1000, }); };
export const useCorpSearch = (query: string) => { return useQuery({ queryKey: ['corp', 'search', query], queryFn: () => api.searchCorporations(query), enabled: query.length >= 2, staleTime: 5 * 60 * 1000, }); };
export const useCorpDetail = (corpId: string) => { return useQuery({ queryKey: ['corp', corpId], queryFn: () => api.getCorpDetail(corpId), enabled: !!corpId, staleTime: 5 * 60 * 1000, }); };
export const useCorpSignals = (corpId: string, type?: string) => { return useQuery({ queryKey: ['corp', corpId, 'signals', type], queryFn: () => api.getCorpSignals(corpId, type), enabled: !!corpId, staleTime: 60 * 1000, }); };
export const useCorpInsightMemory = (corpId: string) => { return useQuery({ queryKey: ['corp', corpId, 'insight-memory'], queryFn: () => api.getCorpInsightMemory(corpId), enabled: !!corpId, }); };
export const useSignalDetail = (signalId: string) => { return useQuery({ queryKey: ['signal', signalId], queryFn: () => api.getSignalDetail(signalId), enabled: !!signalId, staleTime: 60 * 1000, }); };
export const useAnalyzeJob = () => { const queryClient = useQueryClient(); return useMutation({ mutationFn: (corpId: string) => api.triggerAnalyzeJob(corpId), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['dashboard'] }); queryClient.invalidateQueries({ queryKey: ['corp'] }); queryClient.invalidateQueries({ queryKey: ['signal'] }); }, }); };
export const useJobStatus = (jobId: string, options?: { enabled?: boolean }) => { return useQuery({ queryKey: ['job', jobId], queryFn: () => api.getJobStatus(jobId), enabled: options?.enabled ?? !!jobId, refetchInterval: (data) => { if (data?.status === 'DONE' || data?.status === 'FAILED' || data?.status === 'PARTIAL_SUCCESS') { return false; } return 2000; }, }); }; ```
5.2 Files to Delete
``` 삭제 대상 (Mock 데이터 파일):
src/data/corporations.ts ← 삭제 src/data/signals.ts ← 삭제 src/data/insightMemory.ts ← 삭제 ```
5.3 Page Migration Examples
5.3.1 SignalInbox.tsx
Before (Mock): ```typescript import { SIGNALS } from "@/data/signals"; const filteredSignals = SIGNALS.filter(...); ```
After (API): ```typescript import { useDashboardSignals } from "@/hooks/useApi";
const { data, isLoading, error } = useDashboardSignals({ type: activeType !== 'all' ? activeType : undefined, status: activeStatus !== 'all' ? activeStatus : undefined, });
if (isLoading) return <LoadingSpinner />; if (error) return <ErrorMessage error={error} />;
const filteredSignals = data?.signals || []; ```
5.3.2 CorporateDetailPage.tsx
Before (Mock): ```typescript import { getCorporationById } from "@/data/corporations"; const corporation = getCorporationById(corporateId || "1"); ```
After (API): ```typescript import { useCorpDetail, useCorpSignals, useCorpInsightMemory } from "@/hooks/useApi";
const { data: corporation, isLoading } = useCorpDetail(corporateId!); const { data: signalsData } = useCorpSignals(corporateId!); const { data: insightMemory } = useCorpInsightMemory(corporateId!);
if (isLoading) return <LoadingSpinner />; if (!corporation) return <NotFound />; ```
5.3.3 SignalDetailPage.tsx
Before (Mock): ```typescript const mockSignalDetails: Record<string, ExtendedSignal> = { /* hardcoded */ }; const signal = mockSignalDetails[signalId!]; ```
After (API): ```typescript import { useSignalDetail } from "@/hooks/useApi";
const { data: signal, isLoading, error } = useSignalDetail(signalId!);
if (isLoading) return <LoadingSpinner />; if (error || !signal) return <NotFound />; ```
5.4 Demo Mode Implementation
5.4.1 Environment Variables (.env.local)
``` VITE_API_URL=http://localhost:8000 VITE_DEMO_MODE=true VITE_DEMO_TOKEN=your-demo-token-here ```
5.4.2 src/components/demo/DemoPanel.tsx
```typescript import { useState } from 'react'; import { useAnalyzeJob, useJobStatus, useDashboardSignals } from '@/hooks/useApi'; import { Button } from '@/components/ui/button'; import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'; import { Progress } from '@/components/ui/progress'; import { AlertCircle, CheckCircle, Loader2, Play, RefreshCw } from 'lucide-react';
// DemoPanel now uses useCorporations() hook to fetch from corp table
// Corp table data:
// - 엠케이전자 (8001-3719240)
// - 동부건설 (8000-7647330)
// - 전북식품 (4028-1234567)
// - 광주정밀기계 (6201-2345678)
// - 삼성전자 (4301-3456789)
// - 휴림로봇 (6701-4567890)
export function DemoPanel() { const [selectedCorpId, setSelectedCorpId] = useState<string>(''); const [currentJobId, setCurrentJobId] = useState<string | null>(null);
const analyzeJob = useAnalyzeJob(); const { data: jobStatus } = useJobStatus(currentJobId || '', { enabled: !!currentJobId }); const { refetch: refetchSignals } = useDashboardSignals({});
const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true'; if (!isDemoMode) return null;
const handleRunAnalysis = async () => { if (!selectedCorpId) return; try { const result = await analyzeJob.mutateAsync(selectedCorpId); setCurrentJobId(result.job_id); } catch (error) { console.error('Job trigger failed:', error); } };
const handleRefresh = () => { refetchSignals(); setCurrentJobId(null); };
const getStatusIcon = () => { if (!jobStatus) return null; switch (jobStatus.status) { case 'QUEUED': case 'RUNNING': return <Loader2 className="w-4 h-4 animate-spin" />; case 'DONE': case 'PARTIAL_SUCCESS': return <CheckCircle className="w-4 h-4 text-green-500" />; case 'FAILED': return <AlertCircle className="w-4 h-4 text-red-500" />; } };
const getStatusText = () => { if (!jobStatus) return ''; switch (jobStatus.status) { case 'QUEUED': return '대기 중...'; case 'RUNNING': return `분석 중... (${jobStatus.progress.step})`; case 'DONE': return '분석 완료!'; case 'PARTIAL_SUCCESS': return '부분 완료'; case 'FAILED': return `실패: ${jobStatus.error?.message}`; } };
return ( <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6"> <div className="flex items-center gap-2 mb-3"> <span className="bg-amber-500 text-white text-xs px-2 py-0.5 rounded font-medium"> DEMO MODE </span> <span className="text-sm text-amber-700">시연용 수동 실행 기능</span> </div>
 <p className="text-xs text-amber-600 mb-4">
    접속/조회는 분석을 실행하지 않습니다. 아래 기능은 시연을 위한 수동 실행입니다.
  </p>

  <div className="flex items-center gap-3">
    <Select value={selectedCorpId} onValueChange={setSelectedCorpId}>
      <SelectTrigger className="w-[200px]">
        <SelectValue placeholder="법인 선택" />
      </SelectTrigger>
      <SelectContent>
        {DEMO_CORPORATIONS.map((corp) => (
          <SelectItem key={corp.id} value={corp.id}>{corp.name}</SelectItem>
        ))}
      </SelectContent>
    </Select>

    <Button
      onClick={handleRunAnalysis}
      disabled={!selectedCorpId || analyzeJob.isPending || jobStatus?.status === 'RUNNING'}
    >
      <Play className="w-4 h-4 mr-2" />
      분석 실행 (시연용)
    </Button>

    <Button variant="outline" onClick={handleRefresh}>
      <RefreshCw className="w-4 h-4 mr-2" />
      결과 새로고침
    </Button>
  </div>

  {currentJobId && jobStatus && (
    <div className="mt-4 p-3 bg-white rounded border">
      <div className="flex items-center gap-2 mb-2">
        {getStatusIcon()}
        <span className="text-sm font-medium">{getStatusText()}</span>
      </div>
      
      {(jobStatus.status === 'RUNNING' || jobStatus.status === 'QUEUED') && (
        <Progress value={jobStatus.progress.percent} className="h-2" />
      )}

      {jobStatus.status === 'DONE' && jobStatus.result_summary && (
        <div className="text-xs text-gray-600 mt-2">
          생성된 시그널: {jobStatus.result_summary.signals_created}건
        </div>
      )}
    </div>
  )}
</div>

); } ```
5.4.3 SignalInbox.tsx에 Demo Panel 추가
```typescript import { DemoPanel } from '@/components/demo/DemoPanel';
export default function SignalInbox() { return ( <MainLayout> <div className="max-w-7xl"> {/* Demo Panel (Demo Mode에서만 표시) */} <DemoPanel />
   <div className="mb-6">
      <h1>AI 감지 최신 RKYC 시그널</h1>
    </div>
    {/* ... */}
  </div>
</MainLayout>

); } ```

PART 6: WORKER/JOB SYSTEM
6.1 Analyze Job Pipeline
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ANALYZE JOB PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Input: corp_id                                                             │
│                                                                             │
│  Step 1: SNAPSHOT (0-10%)     ─── Internal → JSON (No LLM)                  │
│      Output: rkyc_internal_snapshot + rkyc_internal_snapshot_latest         │
│      On Fail: Job FAILED                                                    │
│                                                                             │
│  Step 2: DOC_INGEST (10-30%)  ─── 🔗 Prompt 1 ─── OCR → Facts               │
│      Output: rkyc_fact                                                      │
│      On Fail: 결측 표시, 계속 진행                                          │
│                                                                             │
│  Step 3: EXTERNAL (30-40%)    ─── 🔗 Prompt 2 ─── News → Summary            │
│      Output: rkyc_external_event + rkyc_external_event_target               │
│      On Fail: 결측 표시, 계속 진행                                          │
│                                                                             │
│  Step 4: CONTEXT (40-50%)     ─── 🔗 Prompt 3 ─── Combine → Compress        │
│      Output: rkyc_unified_context                                           │
│      Token Limit: Input 8,000 / Output 4,000                                │
│                                                                             │
│  Step 5: SIGNAL (50-70%)      ─── 🔗 Prompt 4,5,6 (병렬) ─── Signal 생성    │
│      ├── Direct Signal (Prompt 4)                                           │
│      ├── Industry Signal (Prompt 5)                                         │
│      └── Environment Signal (Prompt 6)                                      │
│      Output: rkyc_signal + rkyc_evidence                                    │
│      On Fail: 각 독립 처리 (부분 성공 가능)                                 │
│                                                                             │
│  Step 6: VALIDATION (70-80%)  ─── Evidence Check (No LLM)                   │
│      Rules: Evidence >= 1, 단정 표현 필터링, event_signature 중복 체크      │
│                                                                             │
│  Step 7: INDEX (80-95%)       ─── 🔗 Prompt 7 ─── Dashboard Briefing        │
│      Output: rkyc_signal_index + rkyc_dashboard_summary                     │
│                                                                             │
│  Step 8: INSIGHT (95-100%)    ─── 🔗 Prompt 8 ─── Past Case Summary         │
│      Output: rkyc_case_index                                                │
│                                                                             │
│  Final Status: DONE | PARTIAL_SUCCESS | FAILED                              │
└─────────────────────────────────────────────────────────────────────────────┘

6.2 LLM Prompt Templates
Prompt 4: Direct Signal Generation
You are a financial signal analyst for Korean banks.
Generate a Direct Signal based on internal data and document facts.

INPUT:
- snapshot_json: {snapshot_json}
- doc_facts: {doc_facts}
- corp_name: {corp_name}

ALLOWED EVENT_TYPES for DIRECT:
- KYC_REFRESH, INTERNAL_RISK_GRADE_CHANGE, OVERDUE_FLAG_ON
- LOAN_EXPOSURE_CHANGE, COLLATERAL_CHANGE
- OWNERSHIP_CHANGE, GOVERNANCE_CHANGE, FINANCIAL_STATEMENT_UPDATE

OUTPUT FORMAT (JSON only):
{
  "signal": {
    "event_type": "one of allowed types",
    "title": "간결한 제목 (50자 이내)",
    "summary": "근거 기반 요약 (2-3문장)",
    "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
    "impact_strength": "HIGH|MED|LOW",
    "confidence": "HIGH|MED|LOW",
    "detail_category": "분류"
  },
  "evidences": [
    {
      "evidence_type": "INTERNAL_FIELD|DOC",
      "ref_type": "SNAPSHOT_KEYPATH|DOC_PAGE",
      "ref_value": "/corp/kyc_status/... or doc_id:page_no",
      "title": "근거 제목",
      "snippet": "근거 발췌"
    }
  ]
}

RULES:
- MUST include at least 1 evidence
- NEVER use: "~일 것이다", "반드시", "즉시 조치"
- Use neutral tone: "참고", "확인됨", "검토 권장"
- If no signal found, return: {"signal": null, "evidences": []}

Prompt 5: Industry Signal Generation
You are a financial signal analyst for Korean banks.
Generate an Industry Signal based on external events.

INPUT:
- unified_context: {unified_context}
- corp_name: {corp_name}
- industry_code: {industry_code}
- external_events: {external_events}

ALLOWED EVENT_TYPES: INDUSTRY_SHOCK

OUTPUT FORMAT (JSON only):
{
  "signal": {
    "event_type": "INDUSTRY_SHOCK",
    "title": "간결한 제목",
    "summary": "근거 기반 요약",
    "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
    "impact_strength": "HIGH|MED|LOW",
    "confidence": "HIGH|MED|LOW",
    "detail_category": "산업 동향",
    "relevance_note": "해당 법인과의 관련성",
    "related_corporations": ["관련 기업명"]
  },
  "evidences": [...]
}

Prompt 6: Environment Signal Generation
You are a financial signal analyst for Korean banks.
Generate an Environment Signal based on policy/macro events.

INPUT:
- unified_context: {unified_context}
- corp_name: {corp_name}
- external_events: {external_events}  // policy/regulation filtered

ALLOWED EVENT_TYPES: POLICY_REGULATION_CHANGE

OUTPUT FORMAT (JSON only):
{
  "signal": {
    "event_type": "POLICY_REGULATION_CHANGE",
    "title": "간결한 제목",
    "summary": "근거 기반 요약",
    "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
    "impact_strength": "HIGH|MED|LOW",
    "confidence": "HIGH|MED|LOW",
    "detail_category": "정책/규제",
    "relevance_note": "잠재적 영향 설명"
  },
  "evidences": [...]
}

Prompt 7: Dashboard Summary
You are creating a daily briefing for Korean bank employees.

INPUT:
- summary_date: {summary_date}
- signals: {signals_json}
- counts: {counts_json}

OUTPUT FORMAT (JSON only):
{
  "briefing_text": "2-3문장의 한국어 브리핑 (100자 이내)",
  "highlights": [
    {"corp_name": "기업명", "signal_type": "direct", "impact": "risk", "title": "제목"}
  ]
}

RULES:
- Neutral, factual tone
- NEVER use action-forcing language
- Maximum 5 highlights


PART 7: BACKEND PROJECT STRUCTURE
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application
│   ├── config.py                    # Settings
│   ├── database.py                  # SQLAlchemy engine
│   │
│   ├── models/                      # SQLAlchemy Models
│   │   ├── corp.py
│   │   ├── snapshot.py
│   │   ├── document.py
│   │   ├── external.py
│   │   ├── signal.py
│   │   └── job.py
│   │
│   ├── schemas/                     # Pydantic Schemas
│   │   ├── dashboard.py
│   │   ├── corp.py
│   │   ├── signal.py
│   │   └── job.py
│   │
│   ├── api/                         # API Routes
│   │   ├── router.py
│   │   ├── dashboard.py
│   │   ├── corp.py
│   │   ├── signal.py
│   │   └── job.py
│   │
│   └── services/                    # Business Logic
│       ├── dashboard_service.py
│       ├── corp_service.py
│       └── signal_service.py
│
├── workers/                         # Celery Workers
│   ├── celery_app.py
│   ├── tasks/
│   │   ├── analyze_task.py          # Main pipeline
│   │   ├── snapshot_task.py
│   │   ├── doc_ingest_task.py
│   │   ├── external_task.py
│   │   ├── context_task.py
│   │   ├── signal_task.py
│   │   ├── validation_task.py
│   │   ├── index_task.py
│   │   └── insight_task.py
│   │
│   └── llm/
│       ├── client.py                # LLM API Client
│       └── prompts/                 # Prompt templates
│
├── seeds/                           # Demo seed data
├── migrations/                      # Alembic
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.worker
└── requirements.txt


PART 8: SEED DATA (Demo용 6개 법인) - 실제 corp 테이블 참조
-- Corporations (실제 Supabase corp 테이블 데이터)
-- 아래 목록은 실제 데이터베이스와 동기화되어 있음. 최신 데이터는 corp 테이블 직접 조회 필요.
INSERT INTO corp VALUES
('8001-3719240', '...', '엠케이전자', '135-81-06406', 'C26', '현기진', ...),
('8000-7647330', '...', '동부건설', '824-87-03495', 'F41', '윤진오', ...),
('4028-1234567', '...', '전북식품', '418-01-55362', 'C10', '강동구', ...),
('6201-2345678', '...', '광주정밀기계', '415-02-96323', 'C29', '강성우', ...),
('4301-3456789', '...', '삼성전자', '124-81-00998', 'C21', '전영현', ...),
('6701-4567890', '...', '휴림로봇', '109-81-60401', 'D35', '김봉관', ...);

-- Bank Relationships
INSERT INTO corp_bank_relationship (corp_id, deposit_balance, loan_balance) VALUES
('1', 3200000000, 8500000000),
('2', 1800000000, 12000000000),
('3', 4500000000, 21000000000),
('4', 1200000000, 9500000000),
('5', 2800000000, 18000000000),
('6', 800000000, 6500000000);

-- Pre-seeded Signals (8개)
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, ...) VALUES
('sig-1', '1', 'DIRECT', 'FINANCIAL_STATEMENT_UPDATE', 'OPPORTUNITY', 'HIGH', '전북식품, 미국 유통망 입점'),
('sig-2', '1', 'INDUSTRY', 'INDUSTRY_SHOCK', 'OPPORTUNITY', 'MEDIUM', 'K-푸드 수출 호조'),
('sig-3', '2', 'DIRECT', 'FINANCIAL_STATEMENT_UPDATE', 'OPPORTUNITY', 'HIGH', '현대차 부품 수주'),
('sig-4', '2', 'ENVIRONMENT', 'POLICY_REGULATION_CHANGE', 'RISK', 'MEDIUM', '원자재 가격 상승'),
('sig-5', '3', 'DIRECT', 'GOVERNANCE_CHANGE', 'OPPORTUNITY', 'MEDIUM', '신규 품목허가'),
('sig-6', '4', 'INDUSTRY', 'INDUSTRY_SHOCK', 'RISK', 'HIGH', '태양광 가격 급락'),
('sig-7', '5', 'DIRECT', 'OWNERSHIP_CHANGE', 'OPPORTUNITY', 'HIGH', 'HD조선 합작법인'),
('sig-8', '6', 'ENVIRONMENT', 'POLICY_REGULATION_CHANGE', 'OPPORTUNITY', 'MEDIUM', '물류 인프라 확충');


PART 9: DOCKER CONFIGURATION
docker-compose.yml
version: '3.8'
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: rkyc
      POSTGRES_PASSWORD: rkyc_password
      POSTGRES_DB: rkyc
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://rkyc:rkyc_password@db:5432/rkyc
      REDIS_URL: redis://redis:6379/0
      DEMO_MODE: "true"
      DEMO_TOKEN: "demo-token-2024"
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      DATABASE_URL: postgresql://rkyc:rkyc_password@db:5432/rkyc
      REDIS_URL: redis://redis:6379/0
      LLM_API_KEY: ${LLM_API_KEY}
    depends_on:
      - db
      - redis


PART 10: EXECUTION CHECKLIST
Implementation Order
Phase 1: Database Setup
□ Create PostgreSQL DDL (schema.sql)
□ Create SQLAlchemy models
□ Create Pydantic schemas
□ Run seed data

Phase 2: Backend API
□ Setup FastAPI app
□ Create API routes
□ Implement services
□ Test all endpoints

Phase 3: Worker System
□ Setup Celery
□ Create LLM client
□ Write prompt templates
□ Implement task steps

Phase 4: Frontend Integration
□ Create API client
□ Create React Query hooks
□ Delete mock data files
□ Update page components
□ Add Demo Panel

Phase 5: Integration Testing
□ Docker compose up
□ Test demo scenario
□ Verify signal generation

Validation Checklist
Architecture:
□ API Server has NO LLM_API_KEY
□ Worker has LLM_API_KEY
□ All LLM calls in workers/tasks/*.py only

Database:
□ Signal UNIQUE constraint on (corp_id, signal_type, snapshot_version, event_signature)
□ Evidence count >= 1 enforced
□ Signal Index denormalized (no JOIN)

Signal Rules:
□ No forbidden expressions
□ Every signal has evidence
□ event_signature is SHA256

Frontend:
□ All data via API (no mock imports)
□ React Query for all fetching
□ Demo Panel only when VITE_DEMO_MODE=true


Document Version: 0.2 Created: 2024-12-30 Purpose: Complete Full-Stack Development Specification for Claude Code
rKYC 추가 지침서
명세서 v0.2 보충 문서
중요: 이 문서는 rKYC_Claude_Code_Spec_v0.2.md와 rKYC_LLM_Integration_Guide.md를 보충합니다. 본 문서의 내용이 명세서와 충돌할 경우, 이 문서의 내용을 우선합니다.

1. Database: Supabase PostgreSQL 사용
1.1 변경 사항
항목
명세서 v0.2 (변경 전)
이 문서 (변경 후)
Database
Docker PostgreSQL
Supabase PostgreSQL
환경
로컬 컨테이너
클라우드 (Tokyo 리전)
docker-compose
db 서비스 포함
db 서비스 제거

1.2 Supabase 프로젝트 설정
Step 1: 프로젝트 생성
1. https://supabase.com 접속 및 로그인
2. "New Project" 클릭
3. 설정:
   - Name: rkyc-demo
   - Database Password: (강력한 비밀번호 설정, 기록해둘 것)
   - Region: Northeast Asia (Tokyo) ← 한국에서 가장 가까움
4. "Create new project" 클릭
5. 프로젝트 생성 완료까지 약 2분 대기

Step 2: Connection String 확인
Project Settings > Database > Connection string

두 가지 연결 문자열을 확인:

1. Transaction Pooler (API Server용, 권장)
   postgresql://postgres.[project-ref]:[password]@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres

2. Session Pooler (Worker용)
   postgresql://postgres.[project-ref]:[password]@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres

Step 3: SSL 설정 확인
Supabase는 SSL 연결이 필수입니다.
Connection String에 ?sslmode=require 파라미터가 자동 포함됩니다.

1.3 환경변수 설정
.env 파일
# ============================================
# DATABASE (Supabase PostgreSQL)
# ============================================

# API Server용 (Transaction Pooler - port 6543)
DATABASE_URL=postgresql://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require

# Worker용 (Session Pooler - port 5432, 긴 트랜잭션용)
DATABASE_URL_DIRECT=postgresql://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres?sslmode=require

# ============================================
# REDIS (로컬 Docker 유지)
# ============================================
REDIS_URL=redis://localhost:6379/0

# ============================================
# DEMO MODE
# ============================================
DEMO_MODE=true
DEMO_TOKEN=rkyc-demo-token-2025

# ============================================
# LLM API KEYS (LLM Integration Guide 참조)
# ============================================
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
GEMINI_API_KEY=xxxxx
PERPLEXITY_API_KEY=pplx-xxxxx

1.4 SQLAlchemy 설정 수정
app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Supabase PostgreSQL (SSL 필수)
DATABASE_URL = os.getenv("DATABASE_URL")

# Engine 생성 (Supabase 호환)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # 연결 상태 확인
    pool_size=5,             # 기본 연결 풀 크기
    max_overflow=10,         # 최대 추가 연결
    pool_recycle=300,        # 5분마다 연결 재활용
    connect_args={
        "sslmode": "require"  # Supabase SSL 필수
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI Dependency용 DB 세션"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

1.5 수정된 docker-compose.yml
version: '3.8'

services:
  # ❌ db 서비스 제거 (Supabase 클라우드 사용)
  
  # ✅ Redis는 로컬 유지 (Celery Broker)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # ✅ API Server
  api:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://redis:6379/0
      DEMO_MODE: ${DEMO_MODE}
      DEMO_TOKEN: ${DEMO_TOKEN}
    ports:
      - "8000:8000"
    depends_on:
      - redis

  # ✅ Worker (LLM Key 포함)
  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      DATABASE_URL: ${DATABASE_URL_DIRECT}
      REDIS_URL: redis://redis:6379/0
      # LLM Keys
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      PERPLEXITY_API_KEY: ${PERPLEXITY_API_KEY}
    depends_on:
      - redis

volumes:
  redis_data:

1.6 DDL 실행 방법
Supabase SQL Editor에서 실행
1. Supabase Dashboard > SQL Editor
2. "New query" 클릭
3. 명세서 v0.2 Part 3의 DDL 전체 복사/붙여넣기
4. "Run" 클릭
5. 테이블 생성 확인: Table Editor에서 15개 테이블 확인

또는 로컬에서 Alembic 사용
# DATABASE_URL이 Supabase를 가리키는 상태에서
alembic upgrade head


2. Seed Data: 실데이터 + 가라 데이터
2.1 법인 데이터 구성
실데이터 (2개) - 실제 존재하는 식별자
순번
법인명
고객번호
법인번호
비고
1
엠케이전자
8001-3719240
134511-0004412
실제 식별자
2
동부건설
8000-7647330
110111-0005002
실제 식별자

가라 데이터 (4개) - 가상의 법인 (실제처럼 생성)
순번
법인명
고객번호
법인번호
업종
3
전북식품
8002-1234567
134511-0012345
식품제조
4
광주정밀기계
8002-2345678
134511-0023456
기계제조
5
익산바이오텍
8002-3456789
134511-0034567
바이오/의약
6
나주태양에너지
8002-4567890
134511-0045678
신재생에너지

2.2 법인별 상세 Seed 데이터
1. 엠케이전자 (실데이터)
{
  "corp_id": "8001-3719240",
  "corp_reg_no": "134511-0004412",
  "corp_name": "엠케이전자",
  "biz_no": "123-45-67890",
  "industry_code": "C26",
  "industry_name": "전자부품 제조업",
  "ceo_name": "김민수",
  "employee_count": 320,
  "founded_year": 1998,
  "headquarters": "경기도 수원시 영통구",
  "main_business": "반도체 검사장비, 전자부품 제조",
  
  "bank_relationship": {
    "has_relationship": true,
    "deposit_balance": 4500000000,
    "loan_balance": 12000000000,
    "fx_transactions": 8500000000,
    "relationship_since": "2015-03-15"
  },
  
  "kyc_status": {
    "is_kyc_completed": true,
    "last_kyc_updated": "2025-09-20",
    "internal_risk_grade": "LOW"
  },
  
  "credit": {
    "has_loan": true,
    "total_exposure_krw": 12000000000,
    "overdue_flag": false,
    "risk_grade_internal": "LOW"
  },
  
  "collateral": {
    "has_collateral": true,
    "collateral_types": ["REAL_ESTATE", "DEPOSIT"],
    "collateral_count": 3
  },
  
  "shareholders": [
    {"name": "김민수", "ownership": "35%", "type": "개인"},
    {"name": "MK홀딩스", "ownership": "25%", "type": "법인"},
    {"name": "국민연금", "ownership": "8%", "type": "기관"}
  ],
  
  "executives": [
    {"name": "김민수", "position": "대표이사", "is_key_man": true},
    {"name": "이정훈", "position": "부사장", "is_key_man": true},
    {"name": "박서연", "position": "CFO", "is_key_man": false}
  ],
  
  "financial_snapshots": [
    {"year": 2024, "revenue": "1,850억", "operating_profit": "185억", "net_profit": "142억"},
    {"year": 2023, "revenue": "1,620억", "operating_profit": "156억", "net_profit": "118억"},
    {"year": 2022, "revenue": "1,480억", "operating_profit": "133억", "net_profit": "98억"}
  ]
}

2. 동부건설 (실데이터)
{
  "corp_id": "8000-7647330",
  "corp_reg_no": "110111-0005002",
  "corp_name": "동부건설",
  "biz_no": "234-56-78901",
  "industry_code": "F41",
  "industry_name": "건설업",
  "ceo_name": "박건호",
  "employee_count": 890,
  "founded_year": 1970,
  "headquarters": "서울특별시 강남구",
  "main_business": "토목, 건축, 주택사업",
  
  "bank_relationship": {
    "has_relationship": true,
    "deposit_balance": 8200000000,
    "loan_balance": 45000000000,
    "fx_transactions": 3200000000,
    "relationship_since": "2008-07-22"
  },
  
  "kyc_status": {
    "is_kyc_completed": true,
    "last_kyc_updated": "2025-11-05",
    "internal_risk_grade": "MED"
  },
  
  "credit": {
    "has_loan": true,
    "total_exposure_krw": 45000000000,
    "overdue_flag": false,
    "risk_grade_internal": "MED"
  },
  
  "collateral": {
    "has_collateral": true,
    "collateral_types": ["REAL_ESTATE", "GUARANTEE"],
    "collateral_count": 5
  },
  
  "shareholders": [
    {"name": "동부그룹", "ownership": "42%", "type": "법인"},
    {"name": "박건호", "ownership": "18%", "type": "개인"},
    {"name": "외국인투자자", "ownership": "12%", "type": "기관"}
  ],
  
  "executives": [
    {"name": "박건호", "position": "대표이사", "is_key_man": true},
    {"name": "김영철", "position": "부회장", "is_key_man": true},
    {"name": "이미영", "position": "전무이사", "is_key_man": false}
  ],
  
  "financial_snapshots": [
    {"year": 2024, "revenue": "9,200억", "operating_profit": "460억", "net_profit": "312억"},
    {"year": 2023, "revenue": "8,750억", "operating_profit": "394억", "net_profit": "267억"},
    {"year": 2022, "revenue": "8,100억", "operating_profit": "324억", "net_profit": "219억"}
  ]
}

3. 전북식품 (가라 데이터)
{
  "corp_id": "8002-1234567",
  "corp_reg_no": "134511-0012345",
  "corp_name": "전북식품",
  "biz_no": "402-81-12345",
  "industry_code": "C10",
  "industry_name": "식품제조업",
  "ceo_name": "김정호",
  "employee_count": 245,
  "founded_year": 1987,
  "headquarters": "전북 전주시 덕진구",
  "main_business": "김치, 젓갈 등 전통 발효식품 제조 및 수출",
  
  "bank_relationship": {
    "has_relationship": true,
    "deposit_balance": 3200000000,
    "loan_balance": 8500000000,
    "fx_transactions": 12000000000,
    "relationship_since": "2012-04-10"
  },
  
  "kyc_status": {
    "is_kyc_completed": true,
    "last_kyc_updated": "2025-12-15",
    "internal_risk_grade": "LOW"
  },
  
  "credit": {
    "has_loan": true,
    "total_exposure_krw": 8500000000,
    "overdue_flag": false,
    "risk_grade_internal": "LOW"
  },
  
  "collateral": {
    "has_collateral": true,
    "collateral_types": ["REAL_ESTATE"],
    "collateral_count": 2
  },
  
  "shareholders": [
    {"name": "김정호", "ownership": "45%", "type": "개인"},
    {"name": "김영수", "ownership": "25%", "type": "개인"},
    {"name": "전북창업투자", "ownership": "15%", "type": "법인"}
  ],
  
  "executives": [
    {"name": "김정호", "position": "대표이사", "is_key_man": true},
    {"name": "이미자", "position": "상무이사", "is_key_man": false}
  ],
  
  "financial_snapshots": [
    {"year": 2024, "revenue": "580억", "operating_profit": "52억", "net_profit": "38억"},
    {"year": 2023, "revenue": "520억", "operating_profit": "44억", "net_profit": "31억"},
    {"year": 2022, "revenue": "465억", "operating_profit": "37억", "net_profit": "26억"}
  ]
}

4. 광주정밀기계 (가라 데이터)
{
  "corp_id": "8002-2345678",
  "corp_reg_no": "134511-0023456",
  "corp_name": "광주정밀기계",
  "biz_no": "410-81-23456",
  "industry_code": "C29",
  "industry_name": "기타 기계 및 장비 제조업",
  "ceo_name": "이상훈",
  "employee_count": 178,
  "founded_year": 1995,
  "headquarters": "광주 광산구 평동산단",
  "main_business": "자동차 정밀 금형 및 부품 제조",
  
  "bank_relationship": {
    "has_relationship": true,
    "deposit_balance": 1800000000,
    "loan_balance": 12000000000,
    "fx_transactions": 2500000000,
    "relationship_since": "2016-09-01"
  },
  
  "kyc_status": {
    "is_kyc_completed": true,
    "last_kyc_updated": "2025-10-28",
    "internal_risk_grade": "LOW"
  },
  
  "credit": {
    "has_loan": true,
    "total_exposure_krw": 12000000000,
    "overdue_flag": false,
    "risk_grade_internal": "LOW"
  },
  
  "collateral": {
    "has_collateral": true,
    "collateral_types": ["REAL_ESTATE", "DEPOSIT"],
    "collateral_count": 2
  },
  
  "shareholders": [
    {"name": "이상훈", "ownership": "52%", "type": "개인"},
    {"name": "광주테크밸리", "ownership": "20%", "type": "법인"},
    {"name": "현대모비스", "ownership": "10%", "type": "법인"}
  ],
  
  "executives": [
    {"name": "이상훈", "position": "대표이사", "is_key_man": true},
    {"name": "최기술", "position": "기술이사", "is_key_man": true}
  ],
  
  "financial_snapshots": [
    {"year": 2024, "revenue": "420억", "operating_profit": "46억", "net_profit": "33억"},
    {"year": 2023, "revenue": "385억", "operating_profit": "39억", "net_profit": "27억"},
    {"year": 2022, "revenue": "352억", "operating_profit": "32억", "net_profit": "22억"}
  ]
}

5. 익산바이오텍 (가라 데이터)
{
  "corp_id": "8002-3456789",
  "corp_reg_no": "134511-0034567",
  "corp_name": "익산바이오텍",
  "biz_no": "403-81-34567",
  "industry_code": "C21",
  "industry_name": "의약품 제조업",
  "ceo_name": "박성민",
  "employee_count": 312,
  "founded_year": 2003,
  "headquarters": "전북 익산시 왕궁면",
  "main_business": "동물용 의약품, 사료첨가제 제조",
  
  "bank_relationship": {
    "has_relationship": true,
    "deposit_balance": 4500000000,
    "loan_balance": 21000000000,
    "fx_transactions": 5800000000,
    "relationship_since": "2010-11-20"
  },
  
  "kyc_status": {
    "is_kyc_completed": true,
    "last_kyc_updated": "2025-08-30",
    "internal_risk_grade": "MED"
  },
  
  "credit": {
    "has_loan": true,
    "total_exposure_krw": 21000000000,
    "overdue_flag": false,
    "risk_grade_internal": "MED"
  },
  
  "collateral": {
    "has_collateral": true,
    "collateral_types": ["REAL_ESTATE", "DEPOSIT", "GUARANTEE"],
    "collateral_count": 4
  },
  
  "shareholders": [
    {"name": "박성민", "ownership": "38%", "type": "개인"},
    {"name": "바이오인베스트", "ownership": "22%", "type": "법인"},
    {"name": "농협중앙회", "ownership": "12%", "type": "기관"}
  ],
  
  "executives": [
    {"name": "박성민", "position": "대표이사", "is_key_man": true},
    {"name": "김연구", "position": "연구소장", "is_key_man": true},
    {"name": "이품질", "position": "품질관리이사", "is_key_man": false}
  ],
  
  "financial_snapshots": [
    {"year": 2024, "revenue": "780억", "operating_profit": "94억", "net_profit": "68억"},
    {"year": 2023, "revenue": "695억", "operating_profit": "76억", "net_profit": "54억"},
    {"year": 2022, "revenue": "612억", "operating_profit": "61억", "net_profit": "43억"}
  ]
}

6. 나주태양에너지 (가라 데이터)
{
  "corp_id": "8002-4567890",
  "corp_reg_no": "134511-0045678",
  "corp_name": "나주태양에너지",
  "biz_no": "411-81-45678",
  "industry_code": "C28",
  "industry_name": "전기장비 제조업",
  "ceo_name": "정태양",
  "employee_count": 156,
  "founded_year": 2010,
  "headquarters": "전남 나주시 빛가람동",
  "main_business": "태양광 모듈 및 인버터 제조",
  
  "bank_relationship": {
    "has_relationship": true,
    "deposit_balance": 1200000000,
    "loan_balance": 9500000000,
    "fx_transactions": 4200000000,
    "relationship_since": "2015-06-15"
  },
  
  "kyc_status": {
    "is_kyc_completed": true,
    "last_kyc_updated": "2025-11-10",
    "internal_risk_grade": "MED"
  },
  
  "credit": {
    "has_loan": true,
    "total_exposure_krw": 9500000000,
    "overdue_flag": false,
    "risk_grade_internal": "MED"
  },
  
  "collateral": {
    "has_collateral": true,
    "collateral_types": ["REAL_ESTATE"],
    "collateral_count": 1
  },
  
  "shareholders": [
    {"name": "정태양", "ownership": "40%", "type": "개인"},
    {"name": "한국에너지공단", "ownership": "18%", "type": "기관"},
    {"name": "그린벤처스", "ownership": "15%", "type": "법인"}
  ],
  
  "executives": [
    {"name": "정태양", "position": "대표이사", "is_key_man": true},
    {"name": "김그린", "position": "기술이사", "is_key_man": false}
  ],
  
  "financial_snapshots": [
    {"year": 2024, "revenue": "320억", "operating_profit": "22억", "net_profit": "15억"},
    {"year": 2023, "revenue": "410억", "operating_profit": "37억", "net_profit": "26억"},
    {"year": 2022, "revenue": "385억", "operating_profit": "31억", "net_profit": "21억"}
  ]
}

2.3 Pre-seeded Signals (시연용)
법인별 초기 시그널
-- 전북식품
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, impact_direction, impact_strength, title, summary) VALUES
('sig-001', '8002-1234567', 'DIRECT', 'FINANCIAL_STATEMENT_UPDATE', 'OPPORTUNITY', 'HIGH', 
 '전북식품, 미국 대형 유통망 입점 확정', 
 '코스트코 미국 본사와 김치 제품 공급 계약 체결. 연간 150억원 규모 수출 예상.');

-- 광주정밀기계
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, impact_direction, impact_strength, title, summary) VALUES
('sig-002', '8002-2345678', 'DIRECT', 'FINANCIAL_STATEMENT_UPDATE', 'OPPORTUNITY', 'HIGH',
 '현대차 신규 전기차 부품 수주',
 '현대자동차 아이오닉7용 정밀 금형 부품 3년간 공급 계약 체결. 계약 규모 약 280억원.');

-- 익산바이오텍
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, impact_direction, impact_strength, title, summary) VALUES
('sig-003', '8002-3456789', 'DIRECT', 'GOVERNANCE_CHANGE', 'OPPORTUNITY', 'MEDIUM',
 '농림부 신규 동물용 의약품 허가',
 '조류인플루엔자 예방 백신 품목 허가 획득. 국내 양계 농가 대상 판매 가능.');

-- 나주태양에너지
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, impact_direction, impact_strength, title, summary) VALUES
('sig-004', '8002-4567890', 'INDUSTRY', 'INDUSTRY_SHOCK', 'RISK', 'HIGH',
 '중국산 태양광 모듈 가격 급락',
 '중국 LONGI, JINKO 등 대형 업체 공격적 가격 인하. 국내 모듈 업체 수익성 압박 예상.');

-- 엠케이전자
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, impact_direction, impact_strength, title, summary) VALUES
('sig-005', '8001-3719240', 'INDUSTRY', 'INDUSTRY_SHOCK', 'OPPORTUNITY', 'HIGH',
 '반도체 검사장비 수요 급증',
 'AI 반도체 생산 확대에 따른 검사장비 수요 증가. 삼성전자, SK하이닉스 발주 증가 전망.');

-- 동부건설
INSERT INTO rkyc_signal (signal_id, corp_id, signal_type, event_type, impact_direction, impact_strength, title, summary) VALUES
('sig-006', '8000-7647330', 'ENVIRONMENT', 'POLICY_REGULATION_CHANGE', 'RISK', 'MEDIUM',
 '부동산 PF 규제 강화 시행',
 '금융당국 부동산 PF 대출 규제 강화 발표. 신규 사업 진행 시 자기자본 비율 상향 필요.');


3. Mock Documents: 가라 문서 이미지 생성
3.1 개요
KYC 문서 이미지는 실제 스캔본이 없으므로 가라 문서 이미지를 생성해야 합니다. Worker의 DOC_INGEST 파이프라인이 이 이미지를 LLM Vision으로 읽어 구조화합니다.
3.2 문서 유형 (5종)
doc_type
한글명
설명
BIZ_REG
사업자등록증
사업자등록번호, 상호, 대표자, 소재지
REGISTRY
법인등기부등본
법인번호, 설립일, 목적, 이사/감사
SHAREHOLDERS
주주명부
주주명, 지분율, 주식수
AOI
정관
회사 목적, 주식, 이사회 규정
FIN_STATEMENT
재무제표 요약
매출, 영업이익, 자산/부채

3.3 생성 방법
방법 1: Python으로 직접 생성 (권장)
# scripts/generate_mock_documents.py

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pdf2image import convert_from_path
import os

# 한글 폰트 등록 (NanumGothic 등)
pdfmetrics.registerFont(TTFont('NanumGothic', '/path/to/NanumGothic.ttf'))

def generate_biz_reg(corp_data: dict, output_path: str):
    """사업자등록증 가라 문서 생성"""
    
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    # 제목
    c.setFont('NanumGothic', 24)
    c.drawCentredString(width/2, height - 80, "사 업 자 등 록 증")
    
    # 내용
    c.setFont('NanumGothic', 12)
    y = height - 150
    
    fields = [
        ("등록번호", corp_data["biz_no"]),
        ("상    호", corp_data["corp_name"]),
        ("대 표 자", corp_data["ceo_name"]),
        ("개업연월일", f"{corp_data['founded_year']}년 01월 01일"),
        ("사업장소재지", corp_data["headquarters"]),
        ("사업의종류", corp_data["main_business"]),
    ]
    
    for label, value in fields:
        c.drawString(100, y, f"{label}: {value}")
        y -= 30
    
    c.save()
    
    # PDF → PNG 변환
    images = convert_from_path(output_path)
    png_path = output_path.replace('.pdf', '.png')
    images[0].save(png_path, 'PNG')
    
    return png_path


def generate_shareholders(corp_data: dict, output_path: str):
    """주주명부 가라 문서 생성"""
    
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    c.setFont('NanumGothic', 20)
    c.drawCentredString(width/2, height - 80, "주 주 명 부")
    
    c.setFont('NanumGothic', 14)
    c.drawCentredString(width/2, height - 110, corp_data["corp_name"])
    
    # 테이블 헤더
    c.setFont('NanumGothic', 11)
    y = height - 180
    c.drawString(80, y, "성명/법인명")
    c.drawString(250, y, "지분율")
    c.drawString(350, y, "유형")
    
    y -= 30
    for sh in corp_data["shareholders"]:
        c.drawString(80, y, sh["name"])
        c.drawString(250, y, sh["ownership"])
        c.drawString(350, y, sh["type"])
        y -= 25
    
    c.save()
    
    images = convert_from_path(output_path)
    png_path = output_path.replace('.pdf', '.png')
    images[0].save(png_path, 'PNG')
    
    return png_path


# 전체 법인에 대해 문서 생성
def generate_all_documents(corporations: list, output_dir: str):
    """모든 법인에 대해 가라 문서 생성"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    for corp in corporations:
        corp_dir = os.path.join(output_dir, corp["corp_id"])
        os.makedirs(corp_dir, exist_ok=True)
        
        # 사업자등록증
        generate_biz_reg(corp, os.path.join(corp_dir, "BIZ_REG.pdf"))
        
        # 주주명부
        generate_shareholders(corp, os.path.join(corp_dir, "SHAREHOLDERS.pdf"))
        
        # TODO: REGISTRY, AOI, FIN_STATEMENT 추가
        
        print(f"Generated documents for {corp['corp_name']}")

방법 2: HTML → PDF → PNG
# HTML 템플릿으로 문서 생성
from weasyprint import HTML

biz_reg_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Nanum Gothic', sans-serif; padding: 40px; }
        h1 { text-align: center; font-size: 28px; }
        .field { margin: 15px 0; }
        .label { display: inline-block; width: 150px; }
    </style>
</head>
<body>
    <h1>사 업 자 등 록 증</h1>
    <div class="field"><span class="label">등록번호:</span> {biz_no}</div>
    <div class="field"><span class="label">상호:</span> {corp_name}</div>
    <div class="field"><span class="label">대표자:</span> {ceo_name}</div>
    <div class="field"><span class="label">소재지:</span> {headquarters}</div>
</body>
</html>
"""

def generate_from_html(template: str, data: dict, output_path: str):
    html_content = template.format(**data)
    HTML(string=html_content).write_pdf(output_path)

3.4 저장 위치
backend/
└── seeds/
    └── documents/
        ├── 8001-3719240/           # 엠케이전자
        │   ├── BIZ_REG.png
        │   ├── SHAREHOLDERS.png
        │   └── FIN_STATEMENT.png
        ├── 8000-7647330/           # 동부건설
        │   ├── BIZ_REG.png
        │   ├── REGISTRY.png
        │   └── SHAREHOLDERS.png
        ├── 8002-1234567/           # 전북식품
        │   ├── BIZ_REG.png
        │   └── SHAREHOLDERS.png
        ├── 8002-2345678/           # 광주정밀기계
        │   ├── BIZ_REG.png
        │   └── SHAREHOLDERS.png
        ├── 8002-3456789/           # 익산바이오텍
        │   ├── BIZ_REG.png
        │   └── SHAREHOLDERS.png
        └── 8002-4567890/           # 나주태양에너지
            ├── BIZ_REG.png
            └── SHAREHOLDERS.png

3.5 문서 내용 일관성 규칙
중요: 가라 문서의 내용은 반드시 Seed 데이터와 일치해야 합니다.
필드
Seed 데이터 출처
문서 반영 위치
법인명
corp_name
모든 문서
사업자번호
biz_no
BIZ_REG
대표자
ceo_name
BIZ_REG, REGISTRY
주주 정보
shareholders[]
SHAREHOLDERS
임원 정보
executives[]
REGISTRY
재무 정보
financial_snapshots[]
FIN_STATEMENT

3.6 최소 요구사항
시연을 위한 최소 문서 세트:
법인
필수 문서
선택 문서
모든 법인
BIZ_REG, SHAREHOLDERS
REGISTRY, AOI, FIN_STATEMENT

최소 2종 문서만 있으면 DOC_INGEST 파이프라인 테스트 가능합니다.

4. 체크리스트
4.1 Supabase 설정
[ ] Supabase 프로젝트 생성
[ ] Connection String 확인
[ ] .env 파일 설정
[ ] DDL 실행 (테이블 생성)
[ ] 연결 테스트
4.2 Seed Data
[ ] 6개 법인 INSERT
[ ] 초기 시그널 INSERT
[ ] 데이터 확인 (Supabase Table Editor)
4.3 Mock Documents
[ ] 문서 생성 스크립트 작성
[ ] 법인별 최소 2종 문서 생성
[ ] 파일 경로 확인
4.4 통합 테스트
[ ] API Server 기동 확인
[ ] Worker 기동 확인
[ ] Demo Job 실행 테스트
[ ] 문서 OCR 결과 확인

5. 요약
항목
내용
Database
Supabase PostgreSQL (Tokyo 리전)
법인 수
6개 (실데이터 2 + 가라 4)
실데이터 법인
엠케이전자, 동부건설
가라 법인
전북식품, 광주정밀기계, 익산바이오텍, 나주태양에너지
문서 유형
5종 (BIZ_REG, REGISTRY, SHAREHOLDERS, AOI, FIN_STATEMENT)
최소 문서
법인당 2종


문서 버전: 1.0 작성일: 2024-12-30 목적: rKYC 명세서 v0.2 보충 - Supabase, Seed Data, Mock Documents
rKYC LLM Integration Guide
2025년 12월 기준 - 최상 퀄리티 멀티 프로바이더 설정

1. 개요
1.1 목적
rKYC 프로젝트의 각 Task별로 최상의 퀄리티를 낼 수 있는 LLM Provider와 Model을 매핑합니다. 비용보다 시연 품질을 최우선으로 합니다.
1.2 사용 가능한 Provider
Provider
용도
API Key 환경변수
Anthropic (Claude)
문서 이해, Signal 생성, 분석
ANTHROPIC_API_KEY
OpenAI
브리핑 생성, 자연스러운 문체
OPENAI_API_KEY
Google (Gemini)
Fallback, 대용량 컨텍스트
GEMINI_API_KEY
Perplexity
실시간 웹검색, 뉴스 수집
PERPLEXITY_API_KEY


2. Task별 최적 Provider 매핑
2.1 매핑 테이블 (2025년 12월 기준)
Task
Primary Provider
Model
Fallback
선정 이유
DOC_INGEST
Claude
claude-sonnet-4-20250514
Gemini 1.5 Pro
한국어 문서 OCR 정확도 최상, 구조화 추출 1위
EXTERNAL
Perplexity
sonar-pro
-
실시간 웹검색 내장, 소스 URL 자동 제공
CONTEXT
Claude
claude-sonnet-4-20250514
Gemini 1.5 Pro
200K 컨텍스트, 긴 문서 압축 능력 최상
SIGNAL_DIRECT
Claude
claude-sonnet-4-20250514
GPT-4o
금융 도메인 이해, 한국어 뉘앙스 정확
SIGNAL_INDUSTRY
Claude
claude-sonnet-4-20250514
GPT-4o
산업 분석 깊이, 근거 기반 추론
SIGNAL_ENVIRONMENT
Claude
claude-sonnet-4-20250514
GPT-4o
정책/규제 해석 정확도
DASHBOARD_SUMMARY
OpenAI
gpt-4o
Claude Sonnet
짧은 브리핑 문체 자연스러움
INSIGHT_MEMORY
Claude
claude-sonnet-4-20250514
GPT-4o
케이스 비교 분석, 논리적 구조화

2.2 선정 근거 (벤치마크 기준)
평가 항목
Claude Sonnet 4
GPT-4o
Gemini 1.5 Pro
Perplexity sonar-pro
한국어 이해
🥇 최상
🥈 우수
🥉 양호
🥈 우수
구조화 출력 (JSON)
🥇 최상
🥇 최상
🥈 우수
🥈 우수
긴 컨텍스트 처리
🥇 200K
🥈 128K
🥇 1M
🥉 제한적
금융 도메인
🥇 최상
🥈 우수
🥉 양호
🥈 우수
근거 기반 추론
🥇 최상
🥈 우수
🥈 우수
🥈 우수
Vision (문서 OCR)
🥇 최상
🥈 우수
🥈 우수
❌ 미지원
실시간 웹검색
❌ 미지원
❌ 미지원
❌ 미지원
🥇 최상


3. 환경변수 설정
3.1 .env 파일
# ============================================
# LLM API KEYS
# ============================================

# Anthropic Claude - Primary (Signal, Context, OCR)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx

# OpenAI - Dashboard Summary
OPENAI_API_KEY=sk-xxxxxxxxxxxxx

# Google Gemini - Fallback
GEMINI_API_KEY=xxxxxxxxxxxxx

# Perplexity - External Search
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxx

# ============================================
# MODEL CONFIGURATION (2025년 12월 최신)
# ============================================

# Claude Models
CLAUDE_MODEL_PRIMARY=claude-sonnet-4-20250514
CLAUDE_MODEL_VISION=claude-sonnet-4-20250514

# OpenAI Models  
OPENAI_MODEL_PRIMARY=gpt-4o
OPENAI_MODEL_MINI=gpt-4o-mini

# Gemini Models
GEMINI_MODEL_PRIMARY=gemini-1.5-pro
GEMINI_MODEL_FLASH=gemini-1.5-flash

# Perplexity Models
PERPLEXITY_MODEL_PRIMARY=sonar-pro
PERPLEXITY_MODEL_REASONING=sonar-reasoning

# ============================================
# LLM ROUTING CONFIG
# ============================================

LLM_FALLBACK_ENABLED=true
LLM_MAX_RETRIES=3
LLM_TIMEOUT_SECONDS=120
LLM_LOG_REQUESTS=true

3.2 Docker Compose 환경변수
# docker-compose.yml (worker 서비스)

worker:
  environment:
    # LLM Keys
    ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    OPENAI_API_KEY: ${OPENAI_API_KEY}
    GEMINI_API_KEY: ${GEMINI_API_KEY}
    PERPLEXITY_API_KEY: ${PERPLEXITY_API_KEY}
    
    # Models
    CLAUDE_MODEL_PRIMARY: claude-sonnet-4-20250514
    OPENAI_MODEL_PRIMARY: gpt-4o
    GEMINI_MODEL_PRIMARY: gemini-1.5-pro
    PERPLEXITY_MODEL_PRIMARY: sonar-pro


4. Python 구현
4.1 requirements.txt (LLM 관련)
# LLM SDKs (2025년 12월 최신 버전)
anthropic>=0.42.0
openai>=1.58.0
google-generativeai>=0.8.3
httpx>=0.28.0

# Utilities
tenacity>=9.0.0
tiktoken>=0.8.0
Pillow>=11.0.0
pdf2image>=1.17.0

4.2 LLM Router 구현
# workers/llm/router.py

from enum import Enum
from typing import Optional, List
import anthropic
from openai import OpenAI
import google.generativeai as genai
import httpx
import os
import json
from tenacity import retry, stop_after_attempt, wait_exponential


class LLMProvider(Enum):
    CLAUDE = "claude"
    OPENAI = "openai"
    PERPLEXITY = "perplexity"
    GEMINI = "gemini"


class TaskType(Enum):
    DOC_INGEST = "doc_ingest"
    EXTERNAL = "external"
    CONTEXT = "context"
    SIGNAL_DIRECT = "signal_direct"
    SIGNAL_INDUSTRY = "signal_industry"
    SIGNAL_ENVIRONMENT = "signal_environment"
    DASHBOARD_SUMMARY = "dashboard_summary"
    INSIGHT_MEMORY = "insight_memory"


# Task → Provider 매핑 (2025년 12월 최상 퀄리티)
TASK_PROVIDER_MAP = {
    TaskType.DOC_INGEST: LLMProvider.CLAUDE,
    TaskType.EXTERNAL: LLMProvider.PERPLEXITY,
    TaskType.CONTEXT: LLMProvider.CLAUDE,
    TaskType.SIGNAL_DIRECT: LLMProvider.CLAUDE,
    TaskType.SIGNAL_INDUSTRY: LLMProvider.CLAUDE,
    TaskType.SIGNAL_ENVIRONMENT: LLMProvider.CLAUDE,
    TaskType.DASHBOARD_SUMMARY: LLMProvider.OPENAI,
    TaskType.INSIGHT_MEMORY: LLMProvider.CLAUDE,
}

# Task별 Fallback Provider
TASK_FALLBACK_MAP = {
    TaskType.DOC_INGEST: LLMProvider.GEMINI,
    TaskType.EXTERNAL: None,  # Perplexity는 대체 불가
    TaskType.CONTEXT: LLMProvider.GEMINI,
    TaskType.SIGNAL_DIRECT: LLMProvider.OPENAI,
    TaskType.SIGNAL_INDUSTRY: LLMProvider.OPENAI,
    TaskType.SIGNAL_ENVIRONMENT: LLMProvider.OPENAI,
    TaskType.DASHBOARD_SUMMARY: LLMProvider.CLAUDE,
    TaskType.INSIGHT_MEMORY: LLMProvider.OPENAI,
}


class LLMRouter:
    """
    다중 LLM Provider 라우터 (2025년 12월 최상 퀄리티 버전)
    
    사용법:
        router = LLMRouter()
        result = await router.generate(
            task=TaskType.SIGNAL_DIRECT,
            prompt="분석 프롬프트...",
            system_prompt="시스템 프롬프트..."
        )
    """
    
    def __init__(self):
        # Claude (Anthropic)
        self.claude = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.claude_model = os.getenv("CLAUDE_MODEL_PRIMARY", "claude-sonnet-4-20250514")
        
        # OpenAI
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.openai_model = os.getenv("OPENAI_MODEL_PRIMARY", "gpt-4o")
        
        # Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.gemini_model = os.getenv("GEMINI_MODEL_PRIMARY", "gemini-1.5-pro")
        
        # Perplexity
        self.perplexity_key = os.getenv("PERPLEXITY_API_KEY")
        self.perplexity_model = os.getenv("PERPLEXITY_MODEL_PRIMARY", "sonar-pro")
        
        # Config
        self.fallback_enabled = os.getenv("LLM_FALLBACK_ENABLED", "true") == "true"
        self.log_requests = os.getenv("LLM_LOG_REQUESTS", "false") == "true"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def generate(
        self,
        task: TaskType,
        prompt: str,
        images: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Task 기반 자동 라우팅으로 LLM 호출
        
        Args:
            task: TaskType enum
            prompt: 사용자 프롬프트
            images: base64 인코딩된 이미지 리스트 (Vision용)
            system_prompt: 시스템 프롬프트
            temperature: 생성 온도 (0.0 ~ 1.0)
            max_tokens: 최대 출력 토큰
            
        Returns:
            LLM 응답 텍스트
        """
        provider = TASK_PROVIDER_MAP.get(task, LLMProvider.CLAUDE)
        
        if self.log_requests:
            print(f"[LLM] Task: {task.value}, Provider: {provider.value}")
        
        try:
            return await self._call_provider(
                provider, prompt, images, system_prompt, temperature, max_tokens
            )
        except Exception as e:
            print(f"[LLM] Primary provider {provider.value} failed: {e}")
            
            if self.fallback_enabled:
                fallback = TASK_FALLBACK_MAP.get(task)
                if fallback:
                    print(f"[LLM] Falling back to {fallback.value}")
                    return await self._call_provider(
                        fallback, prompt, images, system_prompt, temperature, max_tokens
                    )
            raise
    
    async def _call_provider(
        self,
        provider: LLMProvider,
        prompt: str,
        images: Optional[List[str]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Provider별 API 호출"""
        
        if provider == LLMProvider.CLAUDE:
            return await self._call_claude(prompt, images, system_prompt, temperature, max_tokens)
        elif provider == LLMProvider.OPENAI:
            return await self._call_openai(prompt, images, system_prompt, temperature, max_tokens)
        elif provider == LLMProvider.PERPLEXITY:
            return await self._call_perplexity(prompt, system_prompt, temperature, max_tokens)
        elif provider == LLMProvider.GEMINI:
            return await self._call_gemini(prompt, images, system_prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def _call_claude(
        self,
        prompt: str,
        images: Optional[List[str]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Claude API 호출 (Vision 지원)
        
        - 한국어 문서 이해 최상
        - 구조화된 JSON 출력 안정적
        - 200K 컨텍스트 윈도우
        """
        content = []
        
        # 이미지가 있으면 Vision 모드
        if images:
            for img_base64 in images:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_base64,
                    }
                })
        
        content.append({"type": "text", "text": prompt})
        
        message = self.claude.messages.create(
            model=self.claude_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "You are a helpful assistant.",
            messages=[{"role": "user", "content": content}]
        )
        
        return message.content[0].text
    
    async def _call_openai(
        self,
        prompt: str,
        images: Optional[List[str]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        OpenAI API 호출
        
        - 짧은 브리핑 생성에 자연스러운 문체
        - 빠른 응답 속도
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if images:
            content = [{"type": "text", "text": prompt}]
            for img_base64 in images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                })
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": prompt})
        
        response = self.openai.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return response.choices[0].message.content
    
    async def _call_perplexity(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Perplexity API 호출 (실시간 웹검색)
        
        - 실시간 뉴스/공시 검색
        - 소스 URL 자동 제공
        - citations 포함
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.perplexity_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.perplexity_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "return_citations": True,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def _call_gemini(
        self,
        prompt: str,
        images: Optional[List[str]],
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Gemini API 호출 (Fallback)
        
        - 1M 컨텍스트 윈도우 (최대)
        - 비용 효율적
        - 안정적인 백업
        """
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        model = genai.GenerativeModel(
            self.gemini_model,
            system_instruction=system_prompt,
            generation_config=generation_config,
        )
        
        if images:
            import base64
            from PIL import Image
            import io
            
            content = [prompt]
            for img_base64 in images:
                img_bytes = base64.b64decode(img_base64)
                img = Image.open(io.BytesIO(img_bytes))
                content.append(img)
            
            response = model.generate_content(content)
        else:
            response = model.generate_content(prompt)
        
        return response.text


# Singleton instance
_router_instance: Optional[LLMRouter] = None

def get_llm_router() -> LLMRouter:
    """LLMRouter 싱글톤 인스턴스 반환"""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance


5. Task별 사용 예시
5.1 DOC_INGEST (문서 OCR)
# workers/tasks/doc_ingest_task.py

from workers.llm.router import get_llm_router, TaskType
import base64

async def ingest_document(doc_id: str, image_path: str) -> dict:
    """
    KYC 문서 이미지에서 정보 추출
    
    Provider: Claude (Vision)
    Model: claude-sonnet-4-20250514
    """
    router = get_llm_router()
    
    # 이미지 로드
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode()
    
    prompt = """
    이 한국어 KYC 문서에서 다음 정보를 추출하세요.
    
    추출할 필드:
    - 문서 유형 (사업자등록증/등기부등본/주주명부/정관/재무제표)
    - 법인명
    - 사업자등록번호
    - 대표자명
    - 소재지
    - 기타 핵심 정보
    
    JSON 형식으로만 출력하세요. 마크다운 없이 순수 JSON만 출력하세요.
    """
    
    system_prompt = """
    당신은 한국 금융기관의 KYC 문서 분석 전문가입니다.
    문서에서 명시적으로 확인되는 정보만 추출하세요.
    불확실한 정보는 "unknown"으로 표시하세요.
    추측하지 마세요.
    """
    
    result = await router.generate(
        task=TaskType.DOC_INGEST,
        prompt=prompt,
        images=[image_base64],
        system_prompt=system_prompt,
        temperature=0.1,  # 낮은 온도로 정확도 향상
    )
    
    return json.loads(result)

5.2 EXTERNAL (뉴스/공시 수집)
# workers/tasks/external_task.py

from workers.llm.router import get_llm_router, TaskType

async def collect_external_events(corp_name: str, industry: str) -> list:
    """
    실시간 뉴스/공시 수집
    
    Provider: Perplexity
    Model: sonar-pro
    """
    router = get_llm_router()
    
    prompt = f"""
    다음 조건으로 최근 72시간 내 한국어 뉴스와 공시를 검색하세요:
    
    검색 대상:
    - 기업명: {corp_name}
    - 업종: {industry}
    - 관련 키워드: 실적, 계약, 수주, 인수합병, 규제, 정책, 산업동향
    
    각 기사별로 다음 정보를 JSON 배열로 반환하세요:
    - title: 기사 제목
    - summary: 핵심 내용 2-3문장
    - url: 원본 URL
    - source: 출처 (언론사/공시)
    - published_at: 발행일 (YYYY-MM-DD)
    - event_type: INDUSTRY_SHOCK 또는 POLICY_REGULATION_CHANGE
    - tags: 관련 태그 배열
    
    최대 10건까지만 반환하세요.
    JSON 배열만 출력하세요. 마크다운 없이.
    """
    
    system_prompt = """
    당신은 한국 금융시장 전문 리서치 애널리스트입니다.
    신뢰할 수 있는 출처의 뉴스와 공시만 포함하세요.
    각 항목에 반드시 원본 URL을 포함하세요.
    """
    
    result = await router.generate(
        task=TaskType.EXTERNAL,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.3,
    )
    
    return json.loads(result)

5.3 SIGNAL_DIRECT (직접 시그널)
# workers/tasks/signal_task.py

from workers.llm.router import get_llm_router, TaskType

async def generate_direct_signal(
    corp_name: str,
    snapshot_json: dict,
    doc_facts: list
) -> dict:
    """
    Direct Signal 생성
    
    Provider: Claude
    Model: claude-sonnet-4-20250514
    """
    router = get_llm_router()
    
    prompt = f"""
    다음 내부 데이터와 문서 Facts를 기반으로 Direct Signal을 생성하세요.
    
    [기업명]
    {corp_name}
    
    [Internal Snapshot]
    {json.dumps(snapshot_json, ensure_ascii=False, indent=2)}
    
    [Document Facts]
    {json.dumps(doc_facts, ensure_ascii=False, indent=2)}
    
    출력 형식 (JSON):
    {{
      "signal": {{
        "event_type": "KYC_REFRESH|INTERNAL_RISK_GRADE_CHANGE|OVERDUE_FLAG_ON|LOAN_EXPOSURE_CHANGE|COLLATERAL_CHANGE|OWNERSHIP_CHANGE|GOVERNANCE_CHANGE|FINANCIAL_STATEMENT_UPDATE",
        "title": "간결한 제목 (50자 이내)",
        "summary": "근거 기반 요약 (2-3문장)",
        "impact_direction": "RISK|OPPORTUNITY|NEUTRAL",
        "impact_strength": "HIGH|MED|LOW",
        "confidence": "HIGH|MED|LOW",
        "detail_category": "분류"
      }},
      "evidences": [
        {{
          "evidence_type": "INTERNAL_FIELD|DOC",
          "ref_type": "SNAPSHOT_KEYPATH|DOC_PAGE",
          "ref_value": "JSON 경로 또는 doc_id:page_no",
          "title": "근거 제목",
          "snippet": "근거 발췌 (원문)"
        }}
      ]
    }}
    
    의미 있는 시그널이 없으면: {{"signal": null, "evidences": []}}
    JSON만 출력하세요.
    """
    
    system_prompt = """
    당신은 한국 은행의 금융 시그널 분석가입니다.
    
    반드시 지켜야 할 규칙:
    1. 모든 시그널은 최소 1개 이상의 evidence를 포함해야 합니다
    2. 추측이나 예측을 하지 마세요
    3. 다음 표현을 절대 사용하지 마세요: "~일 것이다", "반드시", "즉시 조치", "확실히"
    4. 중립적 톤을 유지하세요: "참고", "확인됨", "검토 권장"
    5. 근거가 명확하지 않으면 시그널을 생성하지 마세요
    """
    
    result = await router.generate(
        task=TaskType.SIGNAL_DIRECT,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.5,
    )
    
    return json.loads(result)

5.4 DASHBOARD_SUMMARY (브리핑)
# workers/tasks/index_task.py

from workers.llm.router import get_llm_router, TaskType

async def generate_dashboard_summary(
    summary_date: str,
    signals: list,
    counts: dict
) -> dict:
    """
    일일 대시보드 브리핑 생성
    
    Provider: OpenAI
    Model: gpt-4o
    """
    router = get_llm_router()
    
    prompt = f"""
    오늘 날짜: {summary_date}
    
    시그널 통계:
    {json.dumps(counts, ensure_ascii=False, indent=2)}
    
    주요 시그널 목록:
    {json.dumps(signals[:10], ensure_ascii=False, indent=2)}
    
    위 정보를 바탕으로 은행 직원용 일일 브리핑을 작성하세요.
    
    출력 형식 (JSON):
    {{
      "briefing_text": "2-3문장의 한국어 브리핑 (100자 이내)",
      "highlights": [
        {{
          "corp_name": "기업명",
          "signal_type": "direct|industry|environment",
          "impact": "risk|opportunity|neutral",
          "title": "시그널 제목"
        }}
      ]
    }}
    
    highlights는 최대 5개까지.
    JSON만 출력하세요.
    """
    
    system_prompt = """
    당신은 한국 은행의 리스크 관리 브리핑 작성자입니다.
    
    규칙:
    - 간결하고 명확하게 작성하세요
    - 행동을 강요하는 표현을 사용하지 마세요
    - 중립적이고 사실 기반으로 작성하세요
    - 가장 중요한 시그널을 먼저 언급하세요
    """
    
    result = await router.generate(
        task=TaskType.DASHBOARD_SUMMARY,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.7,  # 자연스러운 문체를 위해 약간 높게
    )
    
    return json.loads(result)


6. 아키텍처 다이어그램
┌─────────────────────────────────────────────────────────────────────────────┐
│                      LLM INTEGRATION ARCHITECTURE                           │
│                        (2025년 12월 최상 퀄리티)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │     Claude      │  │     OpenAI      │  │       Perplexity            │ │
│  │  Sonnet 4       │  │     GPT-4o      │  │       sonar-pro             │ │
│  │                 │  │                 │  │                             │ │
│  │  ✓ DOC_INGEST   │  │  ✓ DASHBOARD    │  │  ✓ EXTERNAL                 │ │
│  │  ✓ CONTEXT      │  │    _SUMMARY     │  │    (실시간 웹검색)           │ │
│  │  ✓ SIGNAL_*     │  │                 │  │                             │ │
│  │  ✓ INSIGHT      │  │                 │  │                             │ │
│  └────────┬────────┘  └────────┬────────┘  └─────────────┬───────────────┘ │
│           │                    │                        │                  │
│           │                    │                        │                  │
│           ▼                    ▼                        ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         LLM Router                                  │   │
│  │                                                                     │   │
│  │   ┌─────────────────────────────────────────────────────────────┐  │   │
│  │   │  TASK_PROVIDER_MAP (Primary)                                │  │   │
│  │   │                                                             │  │   │
│  │   │  DOC_INGEST ─────────────────────────────► Claude          │  │   │
│  │   │  EXTERNAL ───────────────────────────────► Perplexity      │  │   │
│  │   │  CONTEXT ────────────────────────────────► Claude          │  │   │
│  │   │  SIGNAL_DIRECT ──────────────────────────► Claude          │  │   │
│  │   │  SIGNAL_INDUSTRY ────────────────────────► Claude          │  │   │
│  │   │  SIGNAL_ENVIRONMENT ─────────────────────► Claude          │  │   │
│  │   │  DASHBOARD_SUMMARY ──────────────────────► OpenAI          │  │   │
│  │   │  INSIGHT_MEMORY ─────────────────────────► Claude          │  │   │
│  │   └─────────────────────────────────────────────────────────────┘  │   │
│  │                                                                     │   │
│  │   ┌─────────────────────────────────────────────────────────────┐  │   │
│  │   │  FALLBACK (on error)                                        │  │   │
│  │   │                                                             │  │   │
│  │   │  Claude 실패 시 ──────────────────────────► Gemini 1.5 Pro  │  │   │
│  │   │  OpenAI 실패 시 ──────────────────────────► Claude          │  │   │
│  │   │  Perplexity 실패 시 ──────────────────────► (없음)          │  │   │
│  │   └─────────────────────────────────────────────────────────────┘  │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Worker Tasks                                   │   │
│  │                                                                      │   │
│  │   analyze_task.py                                                    │   │
│  │   ├── Step 1: SNAPSHOT ─────────────────────── (No LLM)             │   │
│  │   ├── Step 2: DOC_INGEST ───────── Claude ──── 문서 OCR             │   │
│  │   ├── Step 3: EXTERNAL ─────────── Perplexity ─ 뉴스 수집           │   │
│  │   ├── Step 4: CONTEXT ──────────── Claude ──── 컨텍스트 압축        │   │
│  │   ├── Step 5: SIGNAL_DIRECT ────── Claude ──── Direct 시그널        │   │
│  │   ├── Step 5: SIGNAL_INDUSTRY ──── Claude ──── Industry 시그널      │   │
│  │   ├── Step 5: SIGNAL_ENVIRONMENT ─ Claude ──── Environment 시그널   │   │
│  │   ├── Step 6: VALIDATION ───────────────────── (No LLM)             │   │
│  │   ├── Step 7: INDEX ────────────── OpenAI ──── 브리핑 생성          │   │
│  │   └── Step 8: INSIGHT_MEMORY ───── Claude ──── 과거 사례 요약       │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


7. 비용 추정 (참고용)
Provider
Model
Task 수
일일 호출
토큰/호출
일일 비용
Claude
Sonnet 4
6
~36
~8K
~$2.50
OpenAI
GPT-4o
1
~6
~2K
~$0.30
Perplexity
sonar-pro
1
~6
~4K
~$0.50
Gemini
1.5 Pro
Fallback
~3
~4K
~$0.20
합계








~$3.50/일

6개 법인 × 매일 1회 분석 기준 실제 비용은 사용량에 따라 달라질 수 있음

8. 체크리스트
8.1 구현 전 확인
[ ] 모든 API Key 발급 완료
[ ] ANTHROPIC_API_KEY
[ ] OPENAI_API_KEY
[ ] GEMINI_API_KEY
[ ] PERPLEXITY_API_KEY
[ ] .env 파일 설정 완료
[ ] requirements.txt 설치 완료
8.2 구현 후 확인
[ ] LLMRouter 정상 초기화
[ ] 각 Provider 개별 테스트
[ ] Task별 라우팅 정상 동작
[ ] Fallback 동작 확인
[ ] JSON 출력 파싱 정상
8.3 퀄리티 확인
[ ] 한국어 출력 자연스러움
[ ] JSON 구조 일관성
[ ] Evidence 포함 여부
[ ] 금지 표현 미사용 확인

문서 버전: 1.0 작성일: 2024-12-30 기준일: 2025년 12월 목적: Claude Code가 rKYC LLM Integration을 구현할 때 참조하는 가이드

