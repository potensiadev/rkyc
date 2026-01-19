# rKYC System Architecture v1.0

> AI-Driven Corporate Risk Signal Detection and Analysis System
> Last Updated: 2026-01-20

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              rKYC SYSTEM                                     │
│                   AI-Driven Corporate Risk Signal Detection                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    HTTPS     ┌──────────────┐    asyncpg    ┌──────────────┐
│   Frontend   │─────────────▶│   Backend    │──────────────▶│   Database   │
│   (Vercel)   │              │  (Railway)   │               │  (Supabase)  │
│              │              │              │               │              │
│ React 18     │              │ FastAPI      │               │ PostgreSQL   │
│ TypeScript   │              │ SQLAlchemy   │               │ pgvector     │
│ TanStack Q   │              │ Pydantic v2  │               │ pgbouncer    │
└──────────────┘              └──────┬───────┘               └──────────────┘
                                     │
                                     │ Celery Task Queue
                                     ▼
                              ┌──────────────┐     ┌──────────────────────────┐
                              │    Worker    │────▶│   External LLM Services  │
                              │   (Celery)   │     │                          │
                              │              │     │ Claude Opus 4.5 (Primary)│
                              │ 9-Stage      │     │ GPT-5 (Fallback 1)       │
                              │ Pipeline     │     │ Gemini 3 Pro (Fallback 2)│
                              └──────────────┘     │ Perplexity (Search)      │
                                     │             │ OpenAI Embedding         │
                                     ▼             └──────────────────────────┘
                              ┌──────────────┐
                              │    Redis     │
                              │  (Message    │
                              │   Broker)    │
                              └──────────────┘
```

## 2. Technology Stack

### 2.1 Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | 18.3.1 |
| Language | TypeScript | 5.8+ |
| Build Tool | Vite | 5.4.19 |
| State Management | TanStack Query | 5.83.0 |
| Routing | React Router | 6.30.1 |
| UI Components | shadcn/ui | Latest |
| Styling | Tailwind CSS | 3.4.17 |
| Icons | Lucide React | 0.462.0 |
| Forms | React Hook Form | 7.61.1 |
| Deployment | Vercel | - |

### 2.2 Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.109+ |
| Language | Python | 3.11+ |
| ORM | SQLAlchemy | 2.0+ |
| Async Driver | asyncpg | 0.29+ |
| Task Queue | Celery | 5.3+ |
| Message Broker | Redis | 5.0+ |
| Validation | Pydantic | 2.0+ |
| LLM Router | litellm | 1.0+ |
| PDF Parsing | pdfplumber | 0.10+ |
| Deployment | Railway | - |

### 2.3 Database

| Component | Technology |
|-----------|-----------|
| DBMS | PostgreSQL (Supabase) |
| Region | Tokyo (ap-northeast-1) |
| Vector Extension | pgvector 0.2+ |
| Connection Pool | pgbouncer (Transaction mode) |
| Port | 6543 (pooler) |

### 2.4 ML/LLM Stack

| Role | Model | Provider |
|------|-------|----------|
| Primary LLM | claude-opus-4-5-20251101 | Anthropic |
| Fallback 1 | gpt-5 | OpenAI |
| Fallback 2 | gemini-3-pro-preview | Google |
| External Search | sonar-pro | Perplexity |
| Embedding | text-embedding-3-large (2000d) | OpenAI |
| Vector Index | HNSW | pgvector |

## 3. Frontend Architecture

### 3.1 Directory Structure

```
src/
├── pages/                    # Page components (8 main pages)
│   ├── Index.tsx            # → SignalInbox (main dashboard)
│   ├── SignalInbox.tsx      # Signal listing with KPI cards + Demo Panel
│   ├── CorporationSearch.tsx# Corporation search & filtering
│   ├── SignalDetailPage.tsx # Signal detail + Evidence + Status update
│   ├── CorporateDetailPage.tsx  # Corporation detail with signals
│   ├── DirectSignalPage.tsx # DIRECT signal filtered view
│   ├── IndustrySignalPage.tsx   # INDUSTRY signal filtered view
│   ├── EnvironmentSignalPage.tsx # ENVIRONMENT signal filtered view
│   ├── DailyBriefingPage.tsx    # Briefing summary
│   ├── AnalyticsStatusPage.tsx  # Job status tracking
│   ├── ReportsPage.tsx          # Report generation
│   └── NotFound.tsx             # 404
│
├── components/
│   ├── layout/              # Layout components
│   │   ├── MainLayout.tsx  # Main wrapper with sidebar
│   │   ├── Sidebar.tsx     # Navigation sidebar
│   │   ├── TopBar.tsx      # Top navigation bar
│   │   └── GlassShell.tsx  # Glass-morphism shell
│   │
│   ├── signals/            # Signal-related components
│   │   ├── SignalCard.tsx         # Individual signal card
│   │   ├── SignalDetailPanel.tsx  # Detailed signal view
│   │   ├── SignalFilters.tsx      # Filter UI
│   │   └── SignalStats.tsx        # Statistics display
│   │
│   ├── dashboard/          # Dashboard components
│   │   ├── GravityGrid.tsx        # Grid layout
│   │   └── LevitatingCard.tsx     # Animated card
│   │
│   ├── detail/            # Detail view components
│   │   ├── AnalysisReport.tsx
│   │   ├── DocViewer.tsx
│   │   └── GlassSignalViewer.tsx
│   │
│   ├── demo/              # Demo Mode
│   │   └── DemoPanel.tsx  # Demo job trigger UI
│   │
│   └── ui/                # shadcn/ui components (40+)
│
├── hooks/
│   └── useApi.ts          # TanStack Query hooks + API data mapping
│
├── lib/
│   └── api.ts             # Fetch-based API client
│
├── types/
│   ├── signal.ts          # Signal type definitions
│   └── corporation.ts     # Corporation types
│
└── data/
    ├── corporations.ts    # Corporation utilities
    └── signals.ts         # Signal utilities
```

### 3.2 Routing Structure

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | SignalInbox | Main dashboard |
| `/corporations` | CorporationSearch | Corporation list |
| `/signals/direct` | DirectSignalPage | DIRECT signals |
| `/signals/industry` | IndustrySignalPage | INDUSTRY signals |
| `/signals/environment` | EnvironmentSignalPage | ENVIRONMENT signals |
| `/signals/:signalId` | SignalDetailPage | Signal detail |
| `/corporates/:corporateId` | CorporateDetailPage | Corporation detail |
| `/briefing` | DailyBriefingPage | Daily briefing |
| `/analytics` | AnalyticsStatusPage | Job tracking |
| `/reports` | ReportsPage | Report generation |

### 3.3 State Management (TanStack Query)

```typescript
// Query Keys
['corporations']               // All corporations
['corporation', corpId]        // Single corporation
['signals', params]            // Filtered signals
['signal', signalId, 'detail'] // Signal with Evidence
['dashboard', 'summary']       // Dashboard stats
['job', jobId]                 // Job status polling

// Mutations
updateSignalStatus()           // Change signal state
dismissSignal()                // Dismiss with reason
triggerAnalyzeJob()            // Start analysis job
```

### 3.4 API Data Transformation

```
API Response (ApiSignal)
        ↓
mapApiSignalToFrontend()
        ↓
Frontend Signal type
        ↓
Component rendering
```

## 4. Backend Architecture

### 4.1 Directory Structure

```
backend/app/
├── main.py                       # FastAPI app entry point
│
├── core/                         # Configuration & Database
│   ├── config.py                # Pydantic Settings (env vars)
│   ├── database.py              # SQLAlchemy async engine
│   └── security.py              # Auth utilities (MVP: unused)
│
├── models/                       # SQLAlchemy ORM Models
│   ├── corporation.py           # corp table
│   ├── signal.py                # rkyc_signal, rkyc_signal_index, rkyc_evidence
│   ├── snapshot.py              # rkyc_internal_snapshot
│   ├── document.py              # rkyc_document, rkyc_fact
│   ├── external_intel.py        # External search tables
│   ├── profile.py               # rkyc_corp_profile
│   └── job.py                   # rkyc_job
│
├── schemas/                      # Pydantic Request/Response
│   ├── corporation.py
│   ├── signal.py
│   ├── snapshot.py
│   ├── job.py
│   ├── document.py
│   └── profile.py
│
├── api/v1/
│   ├── router.py                # Aggregates all routers
│   └── endpoints/
│       ├── corporations.py      # Corporation CRUD + snapshot
│       ├── signals.py           # Signal list/detail/status/dismiss
│       ├── jobs.py              # Job trigger/status
│       ├── dashboard.py         # Dashboard summary
│       ├── documents.py         # Document/facts
│       ├── profiles.py          # Corp profile
│       └── admin.py             # Circuit breaker status
│
├── services/                     # Business Logic
│   ├── corporation_service.py
│   ├── signal_service.py
│   └── query_selector.py        # Environment query selection
│
└── worker/                       # Celery Worker
    ├── celery_app.py            # Celery config
    ├── db.py                    # Sync DB session
    │
    ├── tasks/
    │   ├── analysis.py          # 9-stage pipeline orchestrator
    │   └── profile_refresh.py   # Background refresh
    │
    ├── pipelines/               # Pipeline Implementations
    │   ├── snapshot.py          # Stage 1
    │   ├── doc_ingest.py        # Stage 2
    │   ├── corp_profiling.py    # Stage 3 (Anti-hallucination)
    │   ├── external_search.py   # Stage 4
    │   ├── context.py           # Stage 5
    │   ├── signal_extraction.py # Stage 6
    │   ├── validation.py        # Stage 7
    │   ├── deduplication.py     # Stage 7b
    │   ├── index.py             # Stage 8
    │   ├── insight.py           # Stage 9
    │   └── doc_parsers/         # PDF parsing
    │       ├── base.py
    │       ├── biz_reg_parser.py
    │       ├── registry_parser.py
    │       ├── shareholders_parser.py
    │       ├── aoi_parser.py
    │       └── fin_statement_parser.py
    │
    └── llm/                     # LLM Services
        ├── service.py           # Primary LLM (3-tier fallback)
        ├── orchestrator.py      # Multi-agent (4-layer)
        ├── consensus_engine.py  # Field consensus
        ├── circuit_breaker.py   # Resilience pattern
        ├── external_llm.py      # Perplexity service
        ├── internal_llm.py      # Internal LLM abstraction
        ├── gemini_adapter.py    # Gemini validation
        ├── embedding.py         # OpenAI embedding
        ├── prompts.py           # All prompts
        └── exceptions.py        # LLM exceptions
```

### 4.2 API Endpoints

#### Corporations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/corporations` | List corporations |
| GET | `/api/v1/corporations/{id}` | Get corporation |
| GET | `/api/v1/corporations/{id}/snapshot` | Get internal snapshot |
| POST | `/api/v1/corporations` | Create corporation |
| PATCH | `/api/v1/corporations/{id}` | Update corporation |

#### Signals

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/signals` | List signals (denormalized) |
| GET | `/api/v1/signals/{id}` | Get signal basic info |
| GET | `/api/v1/signals/{id}/detail` | Get signal + Evidence |
| PATCH | `/api/v1/signals/{id}/status` | Update status |
| POST | `/api/v1/signals/{id}/dismiss` | Dismiss with reason |

#### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/jobs/analyze/run` | Trigger 9-stage pipeline |
| GET | `/api/v1/jobs/{id}` | Get job status |
| GET | `/api/v1/jobs` | List jobs |

#### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboard/summary` | Aggregated stats |

#### Corp Profiling

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/corporations/{id}/profile` | Get profile |
| GET | `/api/v1/corporations/{id}/profile/detail` | Profile + provenance |
| GET | `/api/v1/corporations/{id}/profile/queries` | Selected queries |
| POST | `/api/v1/corporations/{id}/profile/refresh` | Force refresh |

#### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/circuit-breaker/status` | All breakers |
| GET | `/api/v1/admin/circuit-breaker/status/{provider}` | Single breaker |
| POST | `/api/v1/admin/circuit-breaker/reset` | Reset breaker |
| GET | `/api/v1/admin/health/llm` | LLM health summary |

## 5. Database Schema

### 5.1 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     DATABASE SCHEMA                          │
└─────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  industry_master │
                    │  (업종 마스터)     │
                    └────────┬─────────┘
                             │ 1:N
                             ▼
┌──────────────────┐    ┌──────────────────┐
│ rkyc_internal_   │    │      corp        │
│ snapshot         │◀───│   (기업 마스터)   │
│ (내부 스냅샷)     │    └────────┬─────────┘
└──────────────────┘             │
         ▲                       │ 1:N
         │                       ├─────────────────┬─────────────────┐
         │                       ▼                 ▼                 ▼
┌────────┴─────────┐    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ rkyc_internal_   │    │  rkyc_signal │  │ rkyc_document│  │rkyc_corp_    │
│ snapshot_latest  │    │  (시그널)     │  │  (문서)      │  │profile       │
└──────────────────┘    └──────┬───────┘  └──────┬───────┘  │(프로파일)     │
                               │                 │          └──────────────┘
                    ┌──────────┼─────────┐       │
                    ▼          ▼         ▼       ▼
             ┌──────────┐ ┌─────────┐ ┌─────────────────┐
             │rkyc_     │ │rkyc_    │ │rkyc_document_   │
             │signal_   │ │evidence │ │page / rkyc_fact │
             │index     │ └─────────┘ └─────────────────┘
             │(대시보드) │
             └──────────┘
                    │
                    ▼
             ┌──────────────┐
             │rkyc_signal_  │
             │embedding     │
             │(벡터 2000d)  │
             └──────────────┘
```

### 5.2 Core Tables

#### corp (기업 마스터)
```sql
corp_id         VARCHAR(20) PK  -- 고객번호 (예: '8001-3719240')
corp_name       VARCHAR(100)    -- 기업명
corp_reg_no     VARCHAR(20)     -- 법인번호
biz_no          VARCHAR(20)     -- 사업자등록번호
industry_code   VARCHAR(10) FK  -- 업종코드
ceo_name        VARCHAR(50)     -- 대표자명
address         TEXT            -- 주소
founded_date    DATE            -- 설립일
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
```

#### rkyc_signal (시그널)
```sql
signal_id           UUID PK
corp_id             VARCHAR(20) FK
signal_type         ENUM (DIRECT, INDUSTRY, ENVIRONMENT)
event_type          ENUM (10 types)
event_signature     VARCHAR(64)     -- sha256 (중복 방지)
impact_direction    ENUM (RISK, OPPORTUNITY, NEUTRAL)
impact_strength     ENUM (HIGH, MED, LOW)
confidence          ENUM (HIGH, MED, LOW)
title               VARCHAR(200)
summary             TEXT
signal_status       ENUM (NEW, REVIEWED, DISMISSED)
reviewed_at         TIMESTAMPTZ
dismissed_at        TIMESTAMPTZ
dismiss_reason      TEXT
created_at          TIMESTAMPTZ
```

#### rkyc_signal_index (대시보드용 비정규화)
```sql
index_id            UUID PK
signal_id           UUID FK
corp_id             VARCHAR(20)
corp_name           VARCHAR(100)    -- 비정규화
industry_code       VARCHAR(10)     -- 비정규화
signal_type         ENUM
event_type          ENUM
impact_direction    ENUM
impact_strength     ENUM
confidence          ENUM
title               VARCHAR(200)
summary_short       VARCHAR(500)    -- 짧은 요약
evidence_count      INT
detected_at         TIMESTAMPTZ
signal_status       ENUM
```

#### rkyc_evidence (근거)
```sql
evidence_id         UUID PK
signal_id           UUID FK
evidence_type       ENUM (INTERNAL_FIELD, DOC, EXTERNAL, CORP_PROFILE)
ref_type            ENUM (SNAPSHOT_KEYPATH, DOC_PAGE, URL, PROFILE_KEYPATH)
ref_value           TEXT            -- JSON Pointer 또는 URL
snippet             TEXT            -- 발췌문
meta                JSONB           -- 추가 메타데이터
created_at          TIMESTAMPTZ
```

#### rkyc_signal_embedding (벡터)
```sql
signal_id           UUID FK
embedding           VECTOR(2000)    -- pgvector
created_at          TIMESTAMPTZ
```

#### rkyc_corp_profile (기업 프로파일)
```sql
profile_id          UUID PK
corp_id             VARCHAR(20) FK
corp_name           VARCHAR(100)
industry_code       VARCHAR(10)
-- 19개 프로파일 필드
revenue_krw         BIGINT
export_ratio_pct    DECIMAL
country_exposure    JSONB
key_materials       JSONB
overseas_operations JSONB
supply_chain        JSONB
shareholders        JSONB
-- 메타데이터
field_confidence    JSONB           -- 필드별 신뢰도
field_provenance    JSONB           -- 필드별 출처
consensus_metadata  JSONB           -- fallback_layer, discrepancies
confidence          ENUM
expires_at          TIMESTAMPTZ     -- TTL: 7일
is_fallback         BOOLEAN         -- 저하 모드 여부
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
```

### 5.3 Enums

```sql
-- Signal Types (3종)
signal_type_enum: DIRECT | INDUSTRY | ENVIRONMENT

-- Event Types (10종)
event_type_enum:
  KYC_REFRESH                    -- KYC 갱신
  INTERNAL_RISK_GRADE_CHANGE     -- 내부 등급 변경
  OVERDUE_FLAG_ON                -- 연체 플래그
  LOAN_EXPOSURE_CHANGE           -- 여신 노출 변화
  COLLATERAL_CHANGE              -- 담보 변화
  OWNERSHIP_CHANGE               -- 소유구조 변화
  GOVERNANCE_CHANGE              -- 지배구조 변화
  FINANCIAL_STATEMENT_UPDATE     -- 재무제표 갱신
  INDUSTRY_SHOCK                 -- 산업 이벤트
  POLICY_REGULATION_CHANGE       -- 정책/규제 변화

-- Signal Status (3종)
signal_status_enum: NEW | REVIEWED | DISMISSED

-- Impact Direction (3종)
impact_direction_enum: RISK | OPPORTUNITY | NEUTRAL

-- Impact Strength (3종)
impact_strength_enum: HIGH | MED | LOW

-- Confidence (3종)
confidence_enum: HIGH | MED | LOW

-- Progress Step (9종)
progress_step_enum:
  SNAPSHOT | DOC_INGEST | PROFILING | EXTERNAL |
  UNIFIED_CONTEXT | SIGNAL | VALIDATION | INDEX | INSIGHT
```

### 5.4 Indexes

```sql
-- Signal Index Table (Dashboard)
CREATE INDEX idx_signal_index_corp_id ON rkyc_signal_index(corp_id);
CREATE INDEX idx_signal_index_signal_type ON rkyc_signal_index(signal_type);
CREATE INDEX idx_signal_index_detected_at ON rkyc_signal_index(detected_at DESC);
CREATE INDEX idx_signal_index_status ON rkyc_signal_index(signal_status);

-- Signal Original Table
CREATE INDEX idx_signal_corp_id ON rkyc_signal(corp_id);
CREATE INDEX idx_signal_event_signature ON rkyc_signal(event_signature);
CREATE INDEX idx_signal_status ON rkyc_signal(signal_status);

-- Evidence
CREATE INDEX idx_evidence_signal_id ON rkyc_evidence(signal_id);

-- Vector (pgvector HNSW)
CREATE INDEX ON rkyc_signal_embedding
  USING hnsw (embedding vector_cosine_ops)
  WITH (m=16, ef_construction=64);

-- Corp Profile
CREATE INDEX idx_corp_profile_corp_id ON rkyc_corp_profile(corp_id);
CREATE INDEX idx_corp_profile_expires ON rkyc_corp_profile(expires_at);
```

## 6. Worker Pipeline (9 Stages)

### 6.1 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────┐
│                 ANALYSIS PIPELINE (9 Stages)                 │
│                    Total Time: ~22.7 seconds                 │
└─────────────────────────────────────────────────────────────┘

Stage 1: SNAPSHOT (5-15%)
├── Fetch internal snapshot from Supabase
├── Validate corporation exists
└── Extract: credit, collateral, ownership data

Stage 2: DOC_INGEST (20-25%)
├── Parse PDF documents (pdfplumber)
├── Extract facts via regex patterns
├── LLM fallback for complex documents
├── Store in rkyc_fact table
└── 5 document types: BIZ_REG, REGISTRY, SHAREHOLDERS, AOI, FIN_STATEMENT

Stage 3: PROFILING (28%) ← Anti-Hallucination
├── Multi-agent orchestrator (4-layer fallback)
│   ├── Layer 0: Cache check (7-day TTL)
│   ├── Layer 1: Perplexity search
│   ├── Layer 1.5: Gemini validation
│   ├── Layer 2: Consensus engine
│   ├── Layer 3: Rule-based merge
│   └── Layer 4: Graceful degradation
├── Conditional query selection (11 categories)
├── Source verification + provenance tracking
└── Store in rkyc_corp_profile

Stage 4: EXTERNAL (30-40%)
├── Perplexity API search
├── Parse news/events with citations
├── Score source credibility
└── Store in rkyc_external_event

Stage 5: UNIFIED_CONTEXT (45-50%)
├── Merge all context sources:
│   ├── Internal snapshot
│   ├── Document facts
│   ├── Corp profile
│   └── External events
├── Vector search for similar cases (pgvector)
└── Build LLM context prompt

Stage 6: SIGNAL_EXTRACTION (55-75%)
├── Call LLM (3-tier fallback)
│   ├── Primary: Claude Opus 4.5
│   ├── Fallback 1: GPT-5
│   └── Fallback 2: Gemini 3 Pro
├── Extract signals (DIRECT/INDUSTRY/ENVIRONMENT)
├── Create event_signature (sha256)
└── Generate evidence references

Stage 7: VALIDATION (75-85%)
├── Apply guardrails:
│   ├── Evidence requirement (≥1 per signal)
│   ├── Confidence/strength validation
│   ├── Signal type mapping
│   ├── Duplicate detection (event_signature)
│   └── Hallucination check
└── Deduplication (within-batch + vs DB)

Stage 8: INDEX (85-90%)
├── Save signals:
│   ├── rkyc_signal (original)
│   ├── rkyc_signal_index (denormalized)
│   └── rkyc_evidence (provenance)
├── Generate embeddings (text-embedding-3-large)
└── Store in rkyc_signal_embedding

Stage 9: INSIGHT (90-100%)
├── Generate executive briefing
├── Summarize key findings
└── Update job status → DONE
```

### 6.2 Pipeline Data Flow

```
Corporation Data (Snapshot)
        │
        ▼
┌───────────────────┐
│ Stage 1: SNAPSHOT │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Stage 2: DOC_INGEST│──▶ PDF Parser + Regex + LLM Fallback
└─────────┬─────────┘
          │
          ▼
┌───────────────────────┐
│ Stage 3: PROFILING    │──▶ MultiAgentOrchestrator (4-Layer)
│ (Anti-Hallucination)  │
└─────────┬─────────────┘
          │
          ▼
┌───────────────────┐
│ Stage 4: EXTERNAL │──▶ Perplexity Search
└─────────┬─────────┘
          │
          ▼
┌─────────────────────────┐
│ Stage 5: UNIFIED_CONTEXT│──▶ Vector Search (pgvector)
└─────────┬───────────────┘
          │
          ▼
     Unified Context
          │
          ▼
┌─────────────────────────────┐
│ Stage 6: SIGNAL_EXTRACTION  │──▶ LLMService (3-tier Fallback)
└─────────┬───────────────────┘
          │
          ▼
  Extracted Signals + Evidence
          │
          ▼
┌──────────────────────────┐
│ Stage 7: VALIDATION      │──▶ Guardrails + Deduplication
└─────────┬────────────────┘
          │
          ▼
  Validated Signals
          │
          ▼
┌─────────────────────┐
│ Stage 8: INDEX      │──▶ DB Save + Embedding (2000d)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Stage 9: INSIGHT    │──▶ Executive Briefing
└─────────┬───────────┘
          │
          ▼
    Job Status → DONE
```

## 7. LLM Orchestration

### 7.1 Multi-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  LLM ORCHESTRATION                           │
└─────────────────────────────────────────────────────────────┘

Tier 1: LLMService (Signal Extraction)
┌───────────────────────────────────────┐
│  Primary:   Claude Opus 4.5           │
│  Fallback1: GPT-5                     │
│  Fallback2: Gemini 3 Pro              │
│                                       │
│  Retry: 3 attempts                    │
│  Backoff: Exponential                 │
│  Timeout: 120 seconds                 │
└───────────────────────────────────────┘

Tier 2: MultiAgentOrchestrator (Corp Profiling)
┌───────────────────────────────────────┐
│  Layer 0: Cache (7-day TTL)           │
│  Layer 1: Perplexity Search           │
│  Layer 1.5: Gemini Validation         │
│  Layer 2: Consensus Engine            │
│  Layer 3: Rule-Based Merge            │
│  Layer 4: Graceful Degradation        │
└───────────────────────────────────────┘

Tier 3: Circuit Breaker (Resilience)
┌───────────────────────────────────────┐
│  Perplexity: threshold=3, cooldown=5m │
│  Gemini:     threshold=3, cooldown=5m │
│  Claude:     threshold=2, cooldown=10m│
│                                       │
│  States: CLOSED → OPEN → HALF_OPEN    │
└───────────────────────────────────────┘
```

### 7.2 Consensus Engine

```
┌───────────────────────────────────────┐
│           CONSENSUS ENGINE            │
├───────────────────────────────────────┤
│ Source Priority:                      │
│   PERPLEXITY_VERIFIED:  100           │
│   GEMINI_VALIDATED:      90           │
│   CLAUDE_SYNTHESIZED:    80           │
│   GEMINI_INFERRED:       50           │
│   RULE_BASED:            30           │
├───────────────────────────────────────┤
│ Match Criteria:                       │
│   Jaccard Similarity >= 0.7           │
│   Korean Stopwords Handling           │
├───────────────────────────────────────┤
│ Output:                               │
│   - Merged profile                    │
│   - Discrepancy flags                 │
│   - Per-field confidence              │
└───────────────────────────────────────┘
```

### 7.3 Embedding Service

```
Model:      text-embedding-3-large
Dimensions: 2000 (pgvector max)
Index:      HNSW (m=16, ef_construction=64)
Search:     Cosine similarity
Use Cases:
  - Similar signal retrieval
  - Case-based reasoning
  - Insight memory
```

## 8. Security Architecture

### 8.1 2-Track LLM Separation

```
┌─────────────────────────────────────────┐
│     External LLM (Public Data Only)     │
├─────────────────────────────────────────┤
│ • Perplexity (news search)              │
│ • GPT-5 (external analysis)             │
│ • Gemini 3 (validation)                 │
│                                         │
│ Data: News, public filings, market data │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│     Internal LLM (Sensitive Data)       │
├─────────────────────────────────────────┤
│ MVP:     GPT-3.5 / Claude Haiku         │
│ Phase 2: Azure OpenAI (Private Cloud)   │
│ Phase 3: On-Premise Llama               │
│                                         │
│ Data: Internal financials, KYC data     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           LLM Audit Log                 │
├─────────────────────────────────────────┤
│ • Timestamp                             │
│ • Model used                            │
│ • Token count                           │
│ • Data classification                   │
│ • Request/response hash                 │
└─────────────────────────────────────────┘
```

### 8.2 Anti-Hallucination (4-Layer Defense)

```
Layer 1: Source Verification
├── Perplexity citations required
├── Domain credibility scoring
└── URL validation

Layer 2: Extraction Guardrails
├── "Return null if uncertain" prompt
├── Structured JSON with confidence
└── Required field validation

Layer 3: Validation Layer (Gemini)
├── Cross-validate Perplexity results
├── Identify discrepancies
└── Flag low-confidence fields

Layer 4: Audit Trail (ProvenanceTracker)
├── Per-field source tracking
├── is_fallback flag for degraded data
└── consensus_metadata.fallback_layer
```

### 8.3 Guardrails

```
Evidence Requirement
└── Every signal must have ≥1 Evidence

Confidence Validation
└── Must be HIGH/MED/LOW (no nulls)

Signal Type Mapping
└── signal_type ∈ {DIRECT, INDUSTRY, ENVIRONMENT}

Duplicate Detection
├── event_signature = sha256(corp_id + event_type + key_fields)
└── Check against existing signals in DB

Hallucination Detection
├── Evidence ref_value must exist in source
├── Signal severity must match evidence
└── Reject ungrounded claims
```

## 9. Deployment Architecture

### 9.1 Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT TOPOLOGY                       │
└─────────────────────────────────────────────────────────────┘

    Vercel                    Railway                  Supabase
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │  HTTPS  │   Backend    │ asyncpg │   Database   │
│              │────────▶│   (API)      │────────▶│  PostgreSQL  │
│ React SPA    │         │   FastAPI    │         │  pgvector    │
│ Vite Build   │         │   uvicorn    │         │  pgbouncer   │
└──────────────┘         └──────┬───────┘         └──────────────┘
                                │
                         Celery │ Redis
                                ▼
                         ┌──────────────┐
                         │   Worker     │
                         │   (Celery)   │────────▶ External LLMs
                         │   9-Stage    │
                         └──────────────┘
```

### 9.2 URLs

| Component | URL |
|-----------|-----|
| Frontend | https://rkyc-wine.vercel.app |
| Backend API | https://rkyc-production.up.railway.app |
| Health Check | https://rkyc-production.up.railway.app/health |
| Database | Supabase Tokyo (ap-northeast-1) |

### 9.3 Environment Variables

**Vercel (Frontend)**
```bash
VITE_API_URL=https://rkyc-production.up.railway.app
VITE_DEMO_MODE=true
VITE_DEMO_TOKEN=demo
```

**Railway (Backend)**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://...@pooler.supabase.com:6543/postgres
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# Redis
REDIS_URL=redis://...

# LLM Keys
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
PERPLEXITY_API_KEY=...

# Security
SECRET_KEY=...
CORS_ORIGINS=https://rkyc-wine.vercel.app
```

## 10. Performance Metrics

### 10.1 Pipeline Performance

| Stage | Duration | Cumulative |
|-------|----------|------------|
| SNAPSHOT | ~1s | 5% |
| DOC_INGEST | ~5s | 25% |
| PROFILING | ~3s | 28% |
| EXTERNAL | ~2s | 40% |
| UNIFIED_CONTEXT | ~1s | 50% |
| SIGNAL_EXTRACTION | ~8s | 75% |
| VALIDATION | ~1s | 85% |
| INDEX | ~1.5s | 90% |
| INSIGHT | ~0.5s | 100% |
| **Total** | **~22.7s** | |

### 10.2 API Response Times

| Endpoint | Latency |
|----------|---------|
| GET /signals | 50-100ms |
| GET /signals/{id}/detail | 80-150ms |
| PATCH /signals/{id}/status | 100-200ms |
| GET /dashboard/summary | 50-100ms |
| POST /jobs/analyze/run | 50-100ms |

### 10.3 Database Metrics

| Metric | Value |
|--------|-------|
| Corporations | 6 (demo) |
| Signals | 29 (demo) |
| Query Latency | <50ms |
| Index Coverage | 95%+ |
| Vector Dimension | 2000 |

## 11. Key Files Reference

### Frontend

| File | Purpose |
|------|---------|
| `src/App.tsx` | Router setup |
| `src/lib/api.ts` | API client |
| `src/hooks/useApi.ts` | TanStack Query hooks |
| `src/pages/SignalInbox.tsx` | Main dashboard |
| `src/pages/SignalDetailPage.tsx` | Signal detail |
| `src/types/signal.ts` | Type definitions |

### Backend

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI entry |
| `app/core/config.py` | Settings |
| `app/core/database.py` | DB engine |
| `app/models/signal.py` | Signal models |
| `app/api/v1/endpoints/signals.py` | Signal API |
| `app/worker/tasks/analysis.py` | Pipeline orchestrator |
| `app/worker/llm/orchestrator.py` | Multi-agent |
| `app/worker/llm/service.py` | LLM service |

### Database

| File | Purpose |
|------|---------|
| `backend/sql/schema_v2.sql` | Core schema |
| `backend/sql/seed_v2.sql` | Test data |
| `backend/sql/migration_v*.sql` | Migrations |

---

## Appendix A: Signal Flow (End-to-End)

```
1. User navigates to Signal Inbox
          │
          ▼
2. Frontend: useSignals() → GET /api/v1/signals
          │
          ▼
3. Backend: Query rkyc_signal_index
          │
          ▼
4. Frontend: Render signal cards
          │
          ▼
5. User clicks signal card
          │
          ▼
6. Frontend: useSignalDetail() → GET /signals/{id}/detail
          │
          ▼
7. Backend: Join rkyc_signal + rkyc_evidence
          │
          ▼
8. Frontend: Render detail + Evidence list
          │
          ▼
9. User clicks "검토완료"
          │
          ▼
10. Frontend: PATCH /signals/{id}/status {status: "REVIEWED"}
          │
          ▼
11. Backend: Update rkyc_signal + rkyc_signal_index
          │
          ▼
12. Frontend: Invalidate queries, re-render
```

## Appendix B: Demo Mode Analysis Flow

```
1. User clicks "분석 실행 (시연용)" in DemoPanel
          │
          ▼
2. POST /api/v1/jobs/analyze/run {corp_id: "8001-3719240"}
          │
          ▼
3. Backend: Create rkyc_job (status=QUEUED)
          │
          ▼
4. Celery Worker: Execute 9-stage pipeline
          │
          ▼
5. Frontend: Poll GET /jobs/{id} every 2s
          │
   ┌──────┴──────────────────────────────────┐
   │ SNAPSHOT → DOC_INGEST → PROFILING →     │
   │ EXTERNAL → CONTEXT → SIGNAL →           │
   │ VALIDATION → INDEX → INSIGHT            │
   └──────┬──────────────────────────────────┘
          │
          ▼
6. Worker: Create new signals in DB
          │
          ▼
7. Job status → DONE
          │
          ▼
8. Frontend: Refresh signal list
          │
          ▼
9. New signals appear in Inbox
```

---

*Document Version: 1.0*
*Last Updated: 2026-01-20*
*Generated from codebase analysis*
