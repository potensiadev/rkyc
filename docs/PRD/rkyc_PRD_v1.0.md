# rKYC (Really Know Your Customer) - Comprehensive PRD v2.0

**Product Requirement Document**
**Version**: 2.0
**Last Updated**: 2026-01-20
**Status**: Production Ready (MVP Complete)
**Author**: Product Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision & Goals](#2-product-vision--goals)
3. [Target Users & Use Cases](#3-target-users--use-cases)
4. [System Architecture](#4-system-architecture)
5. [Core Domain Concepts](#5-core-domain-concepts)
6. [Functional Requirements](#6-functional-requirements)
7. [AI/ML Pipeline Specification](#7-aiml-pipeline-specification)
8. [Data Model & Schema](#8-data-model--schema)
9. [API Specification](#9-api-specification)
10. [Frontend Specification](#10-frontend-specification)
11. [Security & Compliance](#11-security--compliance)
12. [Anti-Hallucination Framework](#12-anti-hallucination-framework)
13. [Performance & Reliability](#13-performance--reliability)
14. [Deployment Architecture](#14-deployment-architecture)
15. [Roadmap & Future Enhancements](#15-roadmap--future-enhancements)
16. [Appendix](#16-appendix)

---

## 1. Executive Summary

### 1.1 Product Overview

**rKYC (Really Know Your Customer)** is an AI-powered risk signal detection and analysis platform designed for financial institution credit analysts. The system monitors real-time external data and internal financial information to detect early-stage corporate risk signals, providing evidence-grounded insights for proactive risk management.

### 1.2 Problem Statement

| Current Challenge | Impact |
|------------------|--------|
| Manual KYC review cycles (quarterly/annual) | Risk signals detected too late |
| Information silos between news, filings, internal data | Fragmented risk view |
| Analyst cognitive overload from data volume | Critical signals missed |
| Lack of evidence-backed recommendations | Low trust in AI outputs |
| Generic risk alerts without company context | Alert fatigue |

### 1.3 Solution

rKYC provides:
- **Real-time signal detection** across 3 categories (DIRECT, INDUSTRY, ENVIRONMENT)
- **Evidence-grounded analysis** with mandatory source attribution
- **Anti-hallucination framework** for trustworthy AI outputs
- **Contextual risk signals** grounded in company-specific business profiles
- **Unified dashboard** for prioritized signal review and action

### 1.4 Key Metrics (Target)

| Metric | Target | Current |
|--------|--------|---------|
| Signal Detection Latency | < 5 minutes | ~2.5 minutes |
| Evidence Coverage | 100% (all signals have sources) | 100% |
| False Positive Rate | < 15% | Measuring |
| Analyst Time Savings | 40% reduction | TBD |
| Signal Review Throughput | 50+ signals/day | 29 seed signals |

### 1.5 Current Implementation Status

| Component | Status | Deployment |
|-----------|--------|------------|
| Frontend | ✅ Complete | Vercel |
| Backend API | ✅ Complete | Railway |
| Database | ✅ Complete | Supabase (Tokyo) |
| Worker Pipeline | ✅ Complete | Railway |
| Corp Profiling | ✅ Complete | Integrated |
| Consensus Engine | ✅ Complete | Integrated |

---

## 2. Product Vision & Goals

### 2.1 Vision Statement

> Enable financial institutions to transform from reactive KYC processes to proactive, AI-augmented risk monitoring with human-in-the-loop verification.

### 2.2 Strategic Goals

1. **Risk Anticipation**: Detect risk signals before they materialize into defaults
2. **Evidence Transparency**: Every AI recommendation backed by verifiable sources
3. **Analyst Augmentation**: Multiply analyst productivity without replacing judgment
4. **Regulatory Readiness**: Maintain audit trails for compliance requirements

### 2.3 Non-Goals

- Automated credit decisioning (human-in-the-loop required)
- Real-time trading signals
- Consumer credit scoring (B2B focus only)
- Direct LLM access from frontend (security boundary)

### 2.4 Success Criteria

| Criteria | Metric | Target |
|----------|--------|--------|
| Adoption | Active daily users | 80% of analysts |
| Trust | Signal dismissal rate | < 20% |
| Efficiency | Time-to-review | < 3 min/signal |
| Coverage | Detected vs. actual events | > 85% |

---

## 3. Target Users & Use Cases

### 3.1 Primary Persona: Credit Analyst

**Name**: 김민수 (Credit Analyst)
**Role**: Corporate Credit Analysis Team, Major Bank
**Experience**: 5+ years in corporate lending

**Daily Tasks**:
- Review 50+ corporate clients for risk changes
- Prepare credit review memos for committee
- Monitor news and DART filings for portfolio companies
- Update internal risk grades

**Pain Points**:
- Information overload from multiple sources
- Difficulty connecting external events to client impact
- Time pressure from increasing portfolio size
- Lack of standardized risk signal definitions

### 3.2 Secondary Persona: Risk Manager

**Name**: 박영희 (Risk Manager)
**Role**: Credit Risk Management Department Head
**Responsibility**: Portfolio-level risk oversight

**Needs**:
- High-level signal distribution visualization
- Industry-wide trend identification
- Audit trail for regulatory reporting

### 3.3 Core Use Cases

#### UC-01: Daily Signal Triage
```
Actor: Credit Analyst
Trigger: Login to rKYC at start of business day
Flow:
1. View Daily Briefing with top signals
2. Scan Risk signals (prioritized by impact)
3. Review Opportunity signals
4. Click through to detailed analysis
5. Mark as Reviewed or Dismiss with reason
Outcome: Prioritized work queue for the day
```

#### UC-02: Company-Specific Deep Dive
```
Actor: Credit Analyst
Trigger: Receive signal for specific company
Flow:
1. Navigate to Corporate Detail page
2. Review company profile and bank relationship
3. Check KYC status and credit grade
4. Review all active signals for company
5. Access Internal Snapshot data
6. Generate report for credit committee
Outcome: Complete risk assessment with evidence
```

#### UC-03: Industry Monitoring
```
Actor: Risk Manager
Trigger: Industry-wide event detected
Flow:
1. View Industry signals in dedicated tab
2. Identify affected companies in portfolio
3. Assess portfolio-level exposure
4. Trigger company-level reviews
Outcome: Proactive portfolio risk mitigation
```

#### UC-04: Macro Risk Assessment (ENVIRONMENT Signals)
```
Actor: Credit Analyst
Trigger: Policy/regulation change signal
Flow:
1. View ENVIRONMENT signal with context
2. Check conditional queries (FX_RISK, TRADE_BLOC, etc.)
3. Review company-specific exposure (export ratio, country exposure)
4. Assess impact using grounded business profile
Outcome: Contextual risk assessment, not generic alert
```

---

## 4. System Architecture

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER LAYER                                  │
│  ┌──────────────┐                                                       │
│  │   Browser    │  React 18 + TypeScript + Vite                         │
│  │  (Vercel)    │  shadcn/ui + Tailwind CSS                             │
│  │              │  TanStack Query                                        │
│  └──────┬───────┘                                                       │
└─────────┼───────────────────────────────────────────────────────────────┘
          │ HTTPS (REST API)
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            API LAYER                                     │
│  ┌──────────────┐                                                       │
│  │   FastAPI    │  Python 3.11+                                         │
│  │  (Railway)   │  SQLAlchemy 2.0 (async)                               │
│  │              │  Pydantic v2                                           │
│  │  ❌ NO LLM   │                                                       │
│  └──────┬───────┘                                                       │
└─────────┼───────────────────────────────────────────────────────────────┘
          │ Database Connection (Transaction Pooler)
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │  PostgreSQL  │  │   pgvector   │  │    Redis     │                   │
│  │  (Supabase)  │  │  (Embedded)  │  │   (Queue)    │                   │
│  │  Tokyo, JP   │  │  2000-dim    │  │   Railway    │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
          │ Celery Task Queue
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          WORKER LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                    Celery Worker (Railway)                    │       │
│  │  ┌─────────────────────────────────────────────────────────┐ │       │
│  │  │              9-Stage Analysis Pipeline                   │ │       │
│  │  │  SNAPSHOT → DOC_INGEST → PROFILING → EXTERNAL →         │ │       │
│  │  │  CONTEXT → SIGNAL → VALIDATION → INDEX → INSIGHT        │ │       │
│  │  └─────────────────────────────────────────────────────────┘ │       │
│  │  ✅ LLM ACCESS (Claude, GPT-5, Gemini, Perplexity)          │       │
│  └──────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Physical Constraints (Critical Security Boundary)

| Component | LLM Keys | DB Access | Purpose |
|-----------|----------|-----------|---------|
| Frontend (Vercel) | ❌ None | ❌ None | UI rendering only |
| Backend API (Railway) | ❌ None | ✅ Yes | CRUD operations |
| Worker (Railway) | ✅ Yes | ✅ Yes | All AI processing |

**Rationale**: This separation prevents LLM API key exposure to client-side code and ensures all AI processing is auditable on the server side.

### 4.3 Technology Stack

#### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI framework |
| TypeScript | 5.x | Type safety |
| Vite | 5.x | Build tool |
| Tailwind CSS | 3.4 | Styling |
| shadcn/ui | Latest | Component library |
| TanStack Query | 5.x | Server state management |
| React Router | 6.x | Routing |
| Framer Motion | Latest | Animations |

#### Backend API
| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.109+ | Web framework |
| Python | 3.11+ | Runtime |
| SQLAlchemy | 2.0 | ORM (async) |
| asyncpg | Latest | PostgreSQL driver |
| Pydantic | 2.x | Validation |
| uvicorn | Latest | ASGI server |

#### Worker
| Technology | Version | Purpose |
|------------|---------|---------|
| Celery | 5.x | Task queue |
| Redis | 7.x | Message broker |
| litellm | Latest | Multi-provider LLM |
| pdfplumber | 0.10+ | PDF parsing |
| kiwipiepy | Latest | Korean NLP |
| OpenAI SDK | 1.x | Embeddings |

#### Database
| Technology | Version | Purpose |
|------------|---------|---------|
| PostgreSQL | 15+ | Primary database |
| pgvector | Latest | Vector similarity search |
| Supabase | Hosted | Managed PostgreSQL |

### 4.4 Deployment URLs

| Environment | URL | Platform |
|-------------|-----|----------|
| Frontend (Production) | https://rkyc-wine.vercel.app | Vercel |
| Backend API (Production) | https://rkyc-production.up.railway.app | Railway |
| Database | ap-northeast-1 (Tokyo) | Supabase |

---

## 5. Core Domain Concepts

### 5.1 Corporation (기업)

The central entity representing a financial institution's corporate customer.

**Identifiers**:
- `corp_id`: Primary customer number (e.g., "8001-3719240")
- `corp_reg_no`: Corporate registration number (법인번호)
- `biz_no`: Business registration number (사업자등록번호)
- `industry_code`: Standard industry classification (e.g., "C26" = Electronics)

**Key Attributes**:
- Basic info: name, CEO, address, founded date
- Industry classification: code, type, main business
- Bank relationship: deposits, loans, FX exposure

### 5.2 Signal (시그널)

A detected risk or opportunity event requiring analyst attention.

#### Signal Types (3 Categories)

| Type | Definition | Examples |
|------|------------|----------|
| **DIRECT** | Direct impact on specific company | Credit grade change, Overdue flag, Collateral change |
| **INDUSTRY** | Sector-wide event affecting multiple companies | Market crash, Industry regulation, Supply chain disruption |
| **ENVIRONMENT** | Macro/external factors | FX volatility, Policy change, Geopolitical event |

#### Event Types (10 Categories)

| Event Type | Signal Type | Description |
|------------|-------------|-------------|
| KYC_REFRESH | DIRECT | KYC information requires update |
| INTERNAL_RISK_GRADE_CHANGE | DIRECT | Internal risk rating changed |
| OVERDUE_FLAG_ON | DIRECT | Delinquency triggered |
| LOAN_EXPOSURE_CHANGE | DIRECT | Credit exposure shift |
| COLLATERAL_CHANGE | DIRECT | Collateral value/composition change |
| OWNERSHIP_CHANGE | DIRECT | Shareholder structure change |
| GOVERNANCE_CHANGE | DIRECT | Management/board change |
| FINANCIAL_STATEMENT_UPDATE | DIRECT | New financial data available |
| INDUSTRY_SHOCK | INDUSTRY | Industry-wide event |
| POLICY_REGULATION_CHANGE | ENVIRONMENT | Policy/regulation change |

#### Signal Lifecycle

```
         ┌─────────┐
         │   NEW   │ ← Signal detected
         └────┬────┘
              │ Analyst reviews
              ▼
         ┌─────────┐
         │REVIEWED │ ← Evidence verified
         └────┬────┘
              │
    ┌─────────┴─────────┐
    ▼                   ▼
┌─────────┐       ┌─────────┐
│CONFIRMED│       │DISMISSED│ (with reason)
└─────────┘       └─────────┘
```

### 5.3 Evidence (근거)

Mandatory source attribution for every signal.

**Evidence Types**:
| Type | Description | Example ref_value |
|------|-------------|-------------------|
| INTERNAL_FIELD | From internal snapshot data | `/credit/loan_summary/overdue_flag` |
| DOC | From submitted documents | `doc_id:page_3` |
| EXTERNAL | From external sources | `https://www.dart.fss.or.kr/...` |
| CORP_PROFILE | From business profile | `/export_ratio_pct` |

**Critical Rule**: Every signal MUST have at least 1 evidence entry. Signals without evidence are rejected during validation.

### 5.4 Internal Snapshot (내부 스냅샷)

Versioned internal financial/non-financial data per company.

**Schema (PRD 7章 Compliant)**:
```json
{
  "schema_version": "v1.0",
  "corp": {
    "corp_id": "8001-3719240",
    "kyc_status": {
      "is_kyc_completed": true,
      "last_kyc_updated": "2024-11-15",
      "internal_risk_grade": "MED"
    }
  },
  "credit": {
    "has_loan": true,
    "loan_summary": {
      "total_exposure_krw": 1200000000,
      "overdue_flag": false,
      "risk_grade_internal": "MED"
    }
  },
  "collateral": {
    "has_collateral": true,
    "collateral_summary": {
      "total_value_krw": 500000000,
      "collateral_types": ["부동산", "예금"]
    }
  },
  "derived_hints": {
    "kyc_overdue_days": 45,
    "exposure_change_30d_pct": 5.2
  }
}
```

### 5.5 Corp Profile (기업 프로필)

Business intelligence for ENVIRONMENT signal grounding (Anti-hallucination).

**19 Profile Fields**:

| Category | Fields |
|----------|--------|
| Basic | corp_name, ceo_name, employee_count, founded_year, headquarters, executives |
| Value Chain | industry_overview, business_model, competitors, macro_factors |
| Supply Chain | key_suppliers, supplier_countries, single_source_risk |
| Overseas | subsidiaries, manufacturing_countries, export_ratio_pct |
| Shareholders | major_shareholders |
| Financial | revenue_krw, financial_history (3-year) |

**Conditional Query Selection** (11 Categories):

| Condition | Queries Activated |
|-----------|-------------------|
| export_ratio_pct ≥ 30% | FX_RISK, TRADE_BLOC |
| China exposure | GEOPOLITICAL, SUPPLY_CHAIN, REGULATION |
| US exposure | GEOPOLITICAL, REGULATION, TRADE_BLOC |
| Key materials exist | COMMODITY, SUPPLY_CHAIN |
| Overseas operations | PANDEMIC_HEALTH, POLITICAL_INSTABILITY |
| Industry C26/C21 (Electronics) | CYBER_TECH |
| Industry D35 (Energy) | ENERGY_SECURITY |
| Industry C10 (Food) | FOOD_SECURITY |

---

## 6. Functional Requirements

### 6.1 Signal Management

#### FR-001: Signal Inbox
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-001-01 | Display all signals with pagination | P0 | ✅ |
| FR-001-02 | Filter by signal_type (DIRECT/INDUSTRY/ENVIRONMENT) | P0 | ✅ |
| FR-001-03 | Filter by signal_status (NEW/REVIEWED/DISMISSED) | P0 | ✅ |
| FR-001-04 | Filter by impact_direction (RISK/OPPORTUNITY/NEUTRAL) | P0 | ✅ |
| FR-001-05 | Sort by detection date, impact, company name | P1 | ✅ |
| FR-001-06 | Show evidence count per signal | P0 | ✅ |
| FR-001-07 | Click-through to signal detail | P0 | ✅ |

#### FR-002: Signal Detail View
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-002-01 | Display full signal summary | P0 | ✅ |
| FR-002-02 | Show all evidence with source links | P0 | ✅ |
| FR-002-03 | Display confidence score | P0 | ✅ |
| FR-002-04 | Action: Mark as Reviewed | P0 | ✅ |
| FR-002-05 | Action: Dismiss with reason (mandatory) | P0 | ✅ |
| FR-002-06 | Show company context (name, industry) | P0 | ✅ |
| FR-002-07 | Navigation to corporate detail | P0 | ✅ |

#### FR-003: Signal Status Management
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-003-01 | PATCH /signals/{id}/status - change status | P0 | ✅ |
| FR-003-02 | POST /signals/{id}/dismiss - dismiss with reason | P0 | ✅ |
| FR-003-03 | Sync status to both rkyc_signal and rkyc_signal_index | P0 | ✅ |
| FR-003-04 | Record review timestamp | P1 | ✅ |

### 6.2 Corporation Management

#### FR-004: Corporation Search
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-004-01 | Search by company name | P0 | ✅ |
| FR-004-02 | Search by business number | P0 | ✅ |
| FR-004-03 | Filter by industry code | P1 | ✅ |
| FR-004-04 | Display signal counts per company | P0 | ✅ |
| FR-004-05 | Pagination (limit/offset) | P0 | ✅ |

#### FR-005: Corporate Detail View
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-005-01 | Display company profile | P0 | ✅ |
| FR-005-02 | Show bank relationship (deposits, loans) | P0 | ✅ |
| FR-005-03 | Display KYC status and risk grade | P0 | ✅ |
| FR-005-04 | List all signals for company | P0 | ✅ |
| FR-005-05 | Access Internal Snapshot data | P0 | ✅ |
| FR-005-06 | Export to PDF | P1 | ✅ |
| FR-005-07 | Generate share link | P2 | ✅ |

#### FR-006: Corp Profile API
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-006-01 | GET /corporations/{id}/profile | P0 | ✅ |
| FR-006-02 | GET /corporations/{id}/profile/detail (with provenance) | P0 | ✅ |
| FR-006-03 | GET /corporations/{id}/profile/queries (conditional selection) | P1 | ✅ |
| FR-006-04 | POST /corporations/{id}/profile/refresh | P1 | ✅ |

### 6.3 Daily Briefing

#### FR-007: Daily Briefing Page
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-007-01 | Show top 3 RISK signals | P0 | ✅ |
| FR-007-02 | Show top 3 OPPORTUNITY signals | P0 | ✅ |
| FR-007-03 | Show reference signals (INDUSTRY/ENVIRONMENT) | P1 | ✅ |
| FR-007-04 | Display today's date | P0 | ✅ |
| FR-007-05 | Click-through to signal detail | P0 | ✅ |

### 6.4 Analytics Dashboard

#### FR-008: Dashboard Summary
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-008-01 | Total signal count | P0 | ✅ |
| FR-008-02 | Breakdown by signal_type | P0 | ✅ |
| FR-008-03 | Breakdown by signal_status | P0 | ✅ |
| FR-008-04 | Breakdown by impact_direction | P0 | ✅ |
| FR-008-05 | Single-query aggregation (no N+1) | P0 | ✅ |

### 6.5 Document Management

#### FR-009: Document Upload & Processing
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-009-01 | Upload documents (PDF, JPG, PNG, TIFF) | P0 | ✅ |
| FR-009-02 | Max file size: 10MB | P0 | ✅ |
| FR-009-03 | Support 5 document types | P0 | ✅ |
| FR-009-04 | Hash-based duplicate detection | P1 | ✅ |
| FR-009-05 | PDF text extraction + regex parsing | P0 | ✅ |
| FR-009-06 | LLM fallback for unextracted fields | P1 | ✅ |
| FR-009-07 | Fact storage with confidence | P0 | ✅ |

### 6.6 Analysis Pipeline (Demo Mode)

#### FR-010: Job Management
| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-010-01 | POST /jobs/analyze/run - trigger analysis | P0 | ✅ |
| FR-010-02 | Validate corp_id exists | P0 | ✅ |
| FR-010-03 | GET /jobs/{job_id} - check status | P0 | ✅ |
| FR-010-04 | Progress tracking (9 stages) | P0 | ✅ |
| FR-010-05 | Error handling with messages | P0 | ✅ |
| FR-010-06 | Demo Panel UI component | P1 | ✅ |

---

## 7. AI/ML Pipeline Specification

### 7.1 Pipeline Overview (9 Stages)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                         ANALYSIS PIPELINE                                  │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Stage 1: SNAPSHOT (5-15%)                                                │
│  ├─ Fetch corporation master data                                         │
│  ├─ Load InternalSnapshot (PRD 7章 schema)                                │
│  └─ Output: snapshot_json + corp metadata                                 │
│                                                                           │
│  Stage 2: DOC_INGEST (20-25%) ⚠️ Non-fatal                               │
│  ├─ PDF text extraction (pdfplumber)                                      │
│  ├─ Regex-based field extraction                                          │
│  ├─ LLM fallback for unmatched                                            │
│  └─ Output: extracted facts                                               │
│                                                                           │
│  Stage 3: PROFILING (28-32%) ⚠️ Non-fatal                                │
│  ├─ MultiAgentOrchestrator execution                                      │
│  ├─ 4-Layer Fallback (Cache → Perplexity+Gemini → Claude → Rule-based)   │
│  ├─ Consensus Engine merge                                                │
│  └─ Output: grounded business profile                                     │
│                                                                           │
│  Stage 4: EXTERNAL (35-42%)                                               │
│  ├─ Perplexity sonar-pro web search                                       │
│  ├─ News, events, regulatory changes                                      │
│  └─ Output: external events with relevance                                │
│                                                                           │
│  Stage 4b: UNIFIED_CONTEXT (45-50%)                                       │
│  ├─ Merge snapshot + doc + external + profile                             │
│  ├─ Extract derived hints                                                 │
│  └─ Output: unified context for LLM                                       │
│                                                                           │
│  Stage 5: SIGNAL (55-65%)                                                 │
│  ├─ LLM signal extraction (Claude → GPT-5 → Gemini)                      │
│  ├─ 3 signal types, 10 event types                                        │
│  ├─ Mandatory evidence per signal                                         │
│  └─ Output: raw signals list                                              │
│                                                                           │
│  Stage 6: VALIDATION (70-80%)                                             │
│  ├─ Intra-batch deduplication                                             │
│  ├─ Guardrails: forbidden expression replacement                          │
│  ├─ Enum validation                                                       │
│  ├─ Cross-DB deduplication (event_signature)                              │
│  └─ Output: validated signals                                             │
│                                                                           │
│  Stage 7: INDEX (85-90%)                                                  │
│  ├─ Create rkyc_signal records                                            │
│  ├─ Create rkyc_evidence records                                          │
│  ├─ Create rkyc_signal_index (denormalized)                               │
│  ├─ Generate embeddings (batch)                                           │
│  └─ Output: signal IDs                                                    │
│                                                                           │
│  Stage 8: INSIGHT (95-100%)                                               │
│  ├─ Vector search: similar past cases                                     │
│  ├─ LLM briefing generation                                               │
│  └─ Output: executive insight                                             │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

### 7.2 LLM Provider Strategy

#### Primary Fallback Chain (3-Stage)

| Priority | Model | Provider | Max Tokens | Use Case |
|----------|-------|----------|------------|----------|
| Primary | claude-opus-4-5-20251101 | Anthropic | 4096 | Signal extraction, Synthesis |
| Fallback 1 | gpt-5 | OpenAI | 4096 | Fallback when Claude fails |
| Fallback 2 | gemini-3-pro-preview | Google | 4096 | Final fallback |

#### Specialized LLM Uses

| Task | Model | Rationale |
|------|-------|-----------|
| Signal Extraction | Claude Opus 4.5 | Best Korean language + JSON accuracy |
| Document Vision | Claude/GPT-5 | Vision capability required |
| Web Search | Perplexity sonar-pro | Real-time web access |
| Embeddings | text-embedding-3-large | 2000-dim, cost-effective |
| Gemini Validation | gemini-3-pro | Cross-verification, enrichment |

#### Fallback Triggers

| Trigger | Action |
|---------|--------|
| Rate limit exceeded | Retry with next provider |
| API connection error | Retry with backoff |
| Timeout (9 min soft, 10 min hard) | Skip to next provider |
| Content policy violation | Skip (non-retryable) |
| Invalid API key | Skip (non-retryable) |

### 7.3 MultiAgent Orchestrator (Corp Profiling)

#### 4-Layer Fallback Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 0: CACHE                                │
│  ├─ Check rkyc_corp_profile for non-expired entry               │
│  ├─ TTL: 7 days (normal), 1 day (fallback)                      │
│  └─ Cache hit → Return immediately                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Cache miss
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                Layer 1+1.5: PERPLEXITY + GEMINI                 │
│  ├─ Perplexity: Web search (Circuit Breaker protected)          │
│  ├─ Gemini: Validate + enrich (Circuit Breaker protected)       │
│  ├─ Consensus Engine: Merge with Jaccard similarity             │
│  └─ Output: 2-source verified profile                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Perplexity failed
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                Layer 2: CLAUDE SYNTHESIS                        │
│  ├─ Claude generates profile from available data                │
│  ├─ Source: CLAUDE_SYNTHESIZED                                  │
│  └─ Lower confidence than Layer 1                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Claude failed
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                Layer 3: RULE-BASED MERGE                        │
│  ├─ Deterministic merge (no LLM)                                │
│  ├─ Source priority: PERPLEXITY > GEMINI > CLAUDE > FALLBACK    │
│  └─ Range validation (ratios sum to 100%)                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ All failed
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Layer 4: GRACEFUL DEGRADATION                      │
│  ├─ Return minimum profile + _degraded: true                    │
│  ├─ Log error messages for audit                                │
│  └─ NEVER FAIL - always return something                        │
└─────────────────────────────────────────────────────────────────┘
```

#### Consensus Engine

| Field Type | Consensus Threshold |
|------------|---------------------|
| String | Jaccard ≥ 0.7 |
| Numeric | ≤ 10% difference |
| List | 50% overlap |
| Discrepancy | Perplexity preferred |

### 7.4 Circuit Breaker Configuration

| Provider | Failure Threshold | Cooldown |
|----------|-------------------|----------|
| Perplexity | 3 failures | 5 minutes |
| Gemini | 3 failures | 5 minutes |
| Claude | 2 failures | 10 minutes |

**States**:
- `CLOSED`: Normal operation
- `OPEN`: Provider blocked (cooling down)
- `HALF_OPEN`: Testing recovery

### 7.5 Embedding & Vector Search

| Configuration | Value |
|---------------|-------|
| Model | text-embedding-3-large |
| Dimension | 2000 (pgvector max) |
| Index | HNSW (m=16, ef_construction=64) |
| Similarity | Cosine |
| Batch Size | 100 |

**Use Cases**:
- Signal similarity search for deduplication
- Similar past case retrieval for insights
- Case index for institutional memory

---

## 8. Data Model & Schema

### 8.1 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   corporation   │       │   rkyc_signal   │       │  rkyc_evidence  │
│─────────────────│       │─────────────────│       │─────────────────│
│ corp_id (PK)    │◄──────│ corp_id (FK)    │       │ evidence_id (PK)│
│ corp_name       │       │ signal_id (PK)  │◄──────│ signal_id (FK)  │
│ corp_reg_no     │       │ signal_type     │       │ evidence_type   │
│ biz_no          │       │ event_type      │       │ ref_type        │
│ industry_code   │       │ impact_direction│       │ ref_value       │
│ ceo_name        │       │ impact_strength │       │ snippet         │
│ ...             │       │ confidence      │       │ meta            │
└─────────────────┘       │ title           │       └─────────────────┘
        │                 │ summary         │
        │                 │ event_signature │
        ▼                 │ signal_status   │
┌─────────────────┐       └─────────────────┘
│rkyc_internal_   │               │
│ snapshot        │               ▼
│─────────────────│       ┌─────────────────┐
│ snapshot_id (PK)│       │rkyc_signal_index│
│ corp_id (FK)    │       │ (Denormalized)  │
│ snapshot_version│       │─────────────────│
│ snapshot_json   │       │ index_id (PK)   │
│ snapshot_hash   │       │ signal_id       │
└─────────────────┘       │ corp_id         │
        │                 │ corp_name       │
        ▼                 │ industry_code   │
┌─────────────────┐       │ ... (all signal │
│rkyc_internal_   │       │     fields)     │
│ snapshot_latest │       └─────────────────┘
│─────────────────│
│ corp_id (PK)    │       ┌─────────────────┐
│ snapshot_id (FK)│       │rkyc_corp_profile│
└─────────────────┘       │─────────────────│
                          │ profile_id (PK) │
┌─────────────────┐       │ corp_id (FK)    │
│  rkyc_document  │       │ business_summary│
│─────────────────│       │ revenue_krw     │
│ doc_id (PK)     │       │ export_ratio_pct│
│ corp_id (FK)    │       │ country_exposure│
│ doc_type        │       │ field_provenance│
│ storage_path    │       │ expires_at      │
│ ingest_status   │       │ is_fallback     │
└─────────────────┘       └─────────────────┘
        │
        ▼
┌─────────────────┐
│   rkyc_fact     │
│─────────────────│
│ fact_id (PK)    │
│ doc_id (FK)     │
│ corp_id (FK)    │
│ fact_type       │
│ field_key       │
│ field_value_*   │
│ confidence      │
└─────────────────┘
```

### 8.2 Core Tables

#### corporation (기업 마스터)
| Column | Type | Description |
|--------|------|-------------|
| corp_id | VARCHAR(20) PK | Customer number |
| corp_name | VARCHAR(200) | Company name |
| corp_reg_no | VARCHAR(14) | Corporate registration |
| biz_no | VARCHAR(12) | Business registration |
| industry_code | VARCHAR(10) | Industry classification |
| ceo_name | VARCHAR(100) | CEO name |
| address | TEXT | Business address |
| founded_date | DATE | Foundation date |
| is_corporation | BOOLEAN | Corporation flag |

#### rkyc_signal (시그널)
| Column | Type | Description |
|--------|------|-------------|
| signal_id | UUID PK | Signal identifier |
| corp_id | VARCHAR FK | Company reference |
| signal_type | ENUM | DIRECT/INDUSTRY/ENVIRONMENT |
| event_type | ENUM | 10 event categories |
| impact_direction | ENUM | RISK/OPPORTUNITY/NEUTRAL |
| impact_strength | ENUM | HIGH/MED/LOW |
| confidence | ENUM | HIGH/MED/LOW |
| title | VARCHAR(200) | Signal title |
| summary | TEXT | Full narrative |
| event_signature | VARCHAR(64) | SHA256 for dedup |
| signal_status | ENUM | NEW/REVIEWED/DISMISSED |
| detected_at | TIMESTAMP | Detection time |
| reviewed_at | TIMESTAMP | Review time |
| dismiss_reason | TEXT | Dismissal reason |

#### rkyc_evidence (근거)
| Column | Type | Description |
|--------|------|-------------|
| evidence_id | UUID PK | Evidence identifier |
| signal_id | UUID FK | Signal reference |
| evidence_type | ENUM | INTERNAL_FIELD/DOC/EXTERNAL/CORP_PROFILE |
| ref_type | ENUM | SNAPSHOT_KEYPATH/DOC_PAGE/URL/PROFILE_KEYPATH |
| ref_value | TEXT | Reference path/URL |
| snippet | VARCHAR(400) | Evidence excerpt |
| meta | JSONB | Additional metadata |

#### rkyc_signal_index (Dashboard 전용 - 조인 금지)
| Column | Type | Description |
|--------|------|-------------|
| index_id | UUID PK | Index identifier |
| signal_id | UUID | Signal reference |
| corp_id | VARCHAR | Company (denormalized) |
| corp_name | VARCHAR | Company name (denormalized) |
| industry_code | VARCHAR | Industry (denormalized) |
| ... | ... | All signal fields duplicated |

**Critical**: This table is denormalized for dashboard performance. JOIN queries are forbidden.

#### rkyc_corp_profile (기업 프로필)
| Column | Type | Description |
|--------|------|-------------|
| profile_id | UUID PK | Profile identifier |
| corp_id | VARCHAR FK | Company reference |
| business_summary | TEXT | Business description |
| revenue_krw | BIGINT | Annual revenue |
| export_ratio_pct | DECIMAL | Export percentage |
| country_exposure | JSONB | {country: percentage} |
| key_materials | TEXT[] | Material types |
| key_customers | TEXT[] | Key clients |
| overseas_operations | TEXT[] | Overseas entities |
| profile_confidence | ENUM | HIGH/MED/LOW |
| field_confidences | JSONB | Per-field confidence |
| field_provenance | JSONB | Per-field source tracking |
| source_urls | TEXT[] | Attributed URLs |
| is_fallback | BOOLEAN | Using industry default |
| search_failed | BOOLEAN | Perplexity failed |
| validation_warnings | TEXT[] | Validation issues |
| fetched_at | TIMESTAMP | Collection time |
| expires_at | TIMESTAMP | TTL expiration |

### 8.3 Enum Definitions

```sql
-- Signal Types
CREATE TYPE signal_type_enum AS ENUM ('DIRECT', 'INDUSTRY', 'ENVIRONMENT');

-- Event Types (10)
CREATE TYPE event_type_enum AS ENUM (
  'KYC_REFRESH', 'INTERNAL_RISK_GRADE_CHANGE', 'OVERDUE_FLAG_ON',
  'LOAN_EXPOSURE_CHANGE', 'COLLATERAL_CHANGE', 'OWNERSHIP_CHANGE',
  'GOVERNANCE_CHANGE', 'FINANCIAL_STATEMENT_UPDATE',
  'INDUSTRY_SHOCK', 'POLICY_REGULATION_CHANGE'
);

-- Impact
CREATE TYPE impact_direction_enum AS ENUM ('RISK', 'OPPORTUNITY', 'NEUTRAL');
CREATE TYPE impact_strength_enum AS ENUM ('HIGH', 'MED', 'LOW');
CREATE TYPE confidence_level_enum AS ENUM ('HIGH', 'MED', 'LOW');

-- Signal Status
CREATE TYPE signal_status_enum AS ENUM ('NEW', 'REVIEWED', 'DISMISSED');

-- Job Status
CREATE TYPE job_status_enum AS ENUM ('QUEUED', 'RUNNING', 'DONE', 'FAILED');

-- Progress Steps (9)
CREATE TYPE progress_step_enum AS ENUM (
  'SNAPSHOT', 'DOC_INGEST', 'PROFILING', 'EXTERNAL',
  'UNIFIED_CONTEXT', 'SIGNAL', 'VALIDATION', 'INDEX', 'INSIGHT'
);

-- Document Types
CREATE TYPE doc_type_enum AS ENUM (
  'BIZ_REG', 'REGISTRY', 'SHAREHOLDERS', 'AOI', 'FIN_STATEMENT'
);

-- Evidence Types
CREATE TYPE evidence_type_enum AS ENUM (
  'INTERNAL_FIELD', 'DOC', 'EXTERNAL', 'CORP_PROFILE'
);
```

---

## 9. API Specification

### 9.1 API Overview

| Category | Endpoints | Status |
|----------|-----------|--------|
| Corporations | 5 | ✅ Complete |
| Signals | 5 | ✅ Complete |
| Jobs | 3 | ✅ Complete |
| Dashboard | 1 | ✅ Complete |
| Documents | 8 | ✅ Complete |
| Profiles | 4 | ✅ Complete |
| Admin | 4 | ✅ Complete |
| **Total** | **30** | |

### 9.2 Corporation Endpoints

#### GET /api/v1/corporations
List corporations with filtering and pagination.

**Query Parameters**:
| Param | Type | Description |
|-------|------|-------------|
| corp_name | string | Partial match search |
| industry_code | string | Exact match |
| limit | int | Results per page (default: 50) |
| offset | int | Pagination offset |

**Response**: `CorporationListResponse`
```json
{
  "total": 6,
  "items": [
    {
      "corp_id": "8001-3719240",
      "corp_name": "엠케이전자",
      "biz_no": "135-81-06406",
      "industry_code": "C26",
      "ceo_name": "현기진",
      "created_at": "2026-01-19T10:00:00Z"
    }
  ]
}
```

#### GET /api/v1/corporations/{corp_id}
Get corporation details.

#### GET /api/v1/corporations/{corp_id}/snapshot
Get latest Internal Snapshot.

#### POST /api/v1/corporations
Create new corporation.

#### PATCH /api/v1/corporations/{corp_id}
Update corporation.

### 9.3 Signal Endpoints

#### GET /api/v1/signals
List signals with comprehensive filtering.

**Query Parameters**:
| Param | Type | Description |
|-------|------|-------------|
| signal_type | enum | DIRECT/INDUSTRY/ENVIRONMENT |
| event_type | enum | 10 event types |
| impact_direction | enum | RISK/OPPORTUNITY/NEUTRAL |
| impact_strength | enum | HIGH/MED/LOW |
| signal_status | enum | NEW/REVIEWED/DISMISSED |
| corp_id | string | Filter by company |
| industry_code | string | Filter by industry |
| limit | int | 1-1000 (default: 50) |
| offset | int | Pagination offset |

#### GET /api/v1/signals/{signal_id}
Get signal basic info.

#### GET /api/v1/signals/{signal_id}/detail
Get signal with all evidence.

**Response**: `SignalDetailResponse`
```json
{
  "signal_id": "00000001-0001-0001-0001-000000000001",
  "corp_id": "8001-3719240",
  "corp_name": "엠케이전자",
  "signal_type": "DIRECT",
  "event_type": "INTERNAL_RISK_GRADE_CHANGE",
  "impact_direction": "RISK",
  "impact_strength": "HIGH",
  "confidence": "HIGH",
  "title": "내부 신용등급 하락",
  "summary": "내부 신용등급이 A에서 B+로 하향 조정됨...",
  "signal_status": "NEW",
  "detected_at": "2026-01-19T09:00:00Z",
  "evidences": [
    {
      "evidence_id": "...",
      "evidence_type": "INTERNAL_FIELD",
      "ref_type": "SNAPSHOT_KEYPATH",
      "ref_value": "/credit/loan_summary/risk_grade_internal",
      "snippet": "risk_grade_internal: B+ (이전: A)"
    }
  ]
}
```

#### PATCH /api/v1/signals/{signal_id}/status
Change signal status.

**Request**:
```json
{
  "status": "REVIEWED"
}
```

#### POST /api/v1/signals/{signal_id}/dismiss
Dismiss signal with reason.

**Request**:
```json
{
  "reason": "중복 시그널 - 이전 분석에서 검토 완료"
}
```

### 9.4 Job Endpoints

#### POST /api/v1/jobs/analyze/run
Trigger analysis for corporation.

**Request**:
```json
{
  "corp_id": "8001-3719240"
}
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "QUEUED",
  "message": "분석 작업이 시작되었습니다."
}
```

#### GET /api/v1/jobs/{job_id}
Get job status with progress.

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_type": "ANALYZE",
  "corp_id": "8001-3719240",
  "status": "RUNNING",
  "progress": {
    "step": "SIGNAL",
    "percent": 60
  },
  "queued_at": "2026-01-19T10:00:00Z",
  "started_at": "2026-01-19T10:00:05Z"
}
```

#### GET /api/v1/jobs
List jobs with filters.

### 9.5 Dashboard Endpoint

#### GET /api/v1/dashboard/summary
Get aggregated statistics (single query, no N+1).

**Response**:
```json
{
  "total_signals": 29,
  "new_signals": 25,
  "risk_signals": 15,
  "opportunity_signals": 10,
  "by_type": {
    "DIRECT": 17,
    "INDUSTRY": 7,
    "ENVIRONMENT": 5
  },
  "by_status": {
    "NEW": 25,
    "REVIEWED": 3,
    "DISMISSED": 1
  },
  "generated_at": "2026-01-19T10:30:00Z"
}
```

### 9.6 Profile Endpoints

#### GET /api/v1/corporations/{corp_id}/profile
Get corporation business profile.

#### GET /api/v1/corporations/{corp_id}/profile/detail
Get profile with full provenance tracking.

**Response** (excerpt):
```json
{
  "profile_id": "...",
  "corp_id": "8001-3719240",
  "business_summary": "반도체 부품 제조업체...",
  "revenue_krw": 120000000000,
  "export_ratio_pct": 45.0,
  "country_exposure": {
    "중국": 35,
    "미국": 25,
    "일본": 15
  },
  "profile_confidence": "HIGH",
  "field_provenance": {
    "revenue_krw": {
      "source_url": "https://dart.fss.or.kr/...",
      "excerpt": "2025년 매출액 1,200억원",
      "confidence": "HIGH",
      "extraction_date": "2026-01-15"
    }
  },
  "is_expired": false
}
```

#### GET /api/v1/corporations/{corp_id}/profile/queries
Get conditional ENVIRONMENT query selection.

**Response**:
```json
{
  "corp_id": "8001-3719240",
  "profile_confidence": "HIGH",
  "selected_queries": [
    "FX_RISK", "TRADE_BLOC", "GEOPOLITICAL",
    "SUPPLY_CHAIN", "REGULATION", "CYBER_TECH"
  ],
  "query_details": [
    {
      "category": "FX_RISK",
      "conditions_met": ["export_ratio_pct >= 30%"]
    }
  ],
  "skipped_queries": ["ENERGY_SECURITY", "FOOD_SECURITY"]
}
```

#### POST /api/v1/corporations/{corp_id}/profile/refresh
Force profile refresh (expires existing, triggers regeneration).

### 9.7 Admin Endpoints

#### GET /api/v1/admin/circuit-breaker/status
Get all Circuit Breaker states.

#### GET /api/v1/admin/circuit-breaker/status/{provider}
Get specific provider status.

#### POST /api/v1/admin/circuit-breaker/reset
Reset Circuit Breaker(s).

#### GET /api/v1/admin/health/llm
Get LLM provider health summary.

---

## 10. Frontend Specification

### 10.1 Page Structure

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | SignalInbox | Main dashboard, signal list |
| `/briefing` | DailyBriefingPage | Executive daily summary |
| `/corporations` | CorporationSearch | Company search |
| `/signals/direct` | DirectSignalPage | DIRECT signals filter |
| `/signals/industry` | IndustrySignalPage | INDUSTRY signals filter |
| `/signals/environment` | EnvironmentSignalPage | ENVIRONMENT signals filter |
| `/signals/:id` | SignalDetailPage | Signal detail + evidence |
| `/corporates/:id` | CorporateDetailPage | Company profile + report |
| `/analytics` | AnalyticsStatusPage | System analytics |
| `/reports` | ReportsPage | Report generation |

### 10.2 Key Components

#### Signal Components
- `SignalCard`: Individual signal display with impact badges
- `SignalDetailPanel`: Sidebar panel for quick review
- `SignalFilters`: Multi-filter UI (type, status, impact)

#### Dashboard Components
- `GravityGrid`: Custom physics-based card layout
- `LevitatingCard`: Animated hover effect
- `KPI Cards`: Statistics display

#### Report Components
- `ReportDocument`: Printable report template
- `PDFExportModal`: Export settings
- `ShareLinkModal`: Link generation

### 10.3 State Management

**TanStack Query Configuration**:
- Stale time: 5 min (corporations), 1 min (signals)
- Automatic refetch on window focus
- Optimistic updates for status changes
- Query invalidation after mutations

### 10.4 Demo Mode

**Environment Variable**: `VITE_DEMO_MODE=true`

**DemoPanel Component**:
- Corporation selector dropdown
- "분석 실행 (시연용)" button
- Job status visualization (QUEUED → RUNNING → DONE)
- 2-second polling interval for status updates

---

## 11. Security & Compliance

### 11.1 Security Architecture (2-Track LLM)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PUBLIC DATA (Track 1)                        │
│  ├─ News articles, DART filings                                 │
│  ├─ Policy/regulation documents                                 │
│  ├─ Industry reports                                            │
│  └─ Processed by: Claude, GPT-5, Perplexity (External LLM)     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  INTERNAL DATA (Track 2)                        │
│  ├─ KYC information                                             │
│  ├─ Credit/loan data                                            │
│  ├─ Collateral information                                      │
│  └─ Processed by: Internal LLM (MVP: GPT-3.5, Future: On-prem) │
└─────────────────────────────────────────────────────────────────┘
```

**Data Classification**:
| Class | Data Types | LLM Track |
|-------|------------|-----------|
| PUBLIC | News, DART, policy, industry | External |
| INTERNAL | KYC, loans, collateral, trading | Internal |
| SEMI_PUBLIC | Financial statements | Situational |

### 11.2 Internal LLM Roadmap

| Phase | Timeline | Implementation |
|-------|----------|----------------|
| Phase 1: MVP | Current | External APIs + interface abstraction |
| Phase 2: Pilot | 3-6 months | Azure OpenAI, AWS Bedrock |
| Phase 3: Production | 1+ year | On-premise Llama, Solar |

### 11.3 Audit Trail

**LLM Audit Log** (`rkyc_llm_audit_log`):
- Every LLM call logged with trace ID
- Provider, model, operation type
- Token counts (input/output)
- Data classification
- PII flag
- Success/failure status
- Response time

### 11.4 Security Controls

| Control | Implementation |
|---------|----------------|
| API Key Isolation | Worker-only LLM access |
| SQL Injection Prevention | Parameterized queries + escape functions |
| Path Traversal Prevention | Corp ID validation |
| File Upload Security | Type whitelist, size limit, hash dedup |
| CORS | Configured for specific domains |
| Authentication | Out of scope (PRD 2.3) |

---

## 12. Anti-Hallucination Framework

### 12.1 4-Layer Defense Model

```
┌─────────────────────────────────────────────────────────────────┐
│              Layer 1: SOURCE VERIFICATION                       │
│  ├─ PerplexityResponseParser: Domain credibility scoring        │
│  ├─ Official sources (DART, IR): HIGH confidence                │
│  ├─ News sources: MED confidence                                │
│  └─ Inferred data: LOW confidence                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│            Layer 2: EXTRACTION GUARDRAILS                       │
│  ├─ LLM Prompt: "Return null if unknown, never guess"          │
│  ├─ Structured output schema enforcement                        │
│  └─ Confidence-tagged fields                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Layer 3: VALIDATION LAYER                          │
│  ├─ CorpProfileValidator: Range/consistency checks              │
│  ├─ Numeric bounds (0-100% for ratios)                          │
│  ├─ Ratio sum validation (export + domestic = 100)              │
│  └─ Required field enforcement                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               Layer 4: AUDIT TRAIL                              │
│  ├─ ProvenanceTracker: Per-field source attribution             │
│  ├─ source_url, excerpt, confidence, extraction_date            │
│  ├─ raw_search_result preserved                                 │
│  └─ is_fallback flag for industry defaults                      │
└─────────────────────────────────────────────────────────────────┘
```

### 12.2 Guardrails: Forbidden Expressions

| Forbidden | Replacement |
|-----------|-------------|
| "~일 것이다" | "~로 추정됨" |
| "반드시" | "가능성이 높음" |
| "즉시 조치 필요" | "검토 권고" |
| "100%" | "높은 확률로" |
| "확실히", "틀림없이" | "상당한 가능성으로" |
| "명백히" | "검토 결과에 따르면" |
| "의심의 여지 없이" | "현재 정보에 따르면" |

**Implementation**: Regex-based replacement in VALIDATION stage.

### 12.3 Evidence Requirements

**Rule**: Every signal MUST have ≥1 evidence entry.

**Evidence Types**:
- `INTERNAL_FIELD`: From snapshot (JSON Pointer)
- `DOC`: From document (page reference)
- `EXTERNAL`: From web (URL)
- `CORP_PROFILE`: From business profile (field path)

**Validation**: Signals without evidence are rejected during pipeline.

### 12.4 Deduplication

**Intra-batch**: Remove duplicates within same analysis run.

**Cross-DB**:
- SHA256 `event_signature` check
- 30-day window for similarity > 85%
- Same corporation + event type

---

## 13. Performance & Reliability

### 13.1 Performance Targets

| Metric | Target | Implementation |
|--------|--------|----------------|
| API Response (P50) | < 200ms | Denormalized indexes |
| API Response (P99) | < 1s | Query optimization |
| Pipeline Execution | < 3 min | 9-stage parallelization |
| Embedding Batch | 100/request | OpenAI batch limit |
| Dashboard Load | < 500ms | Single-query aggregation |

### 13.2 Reliability Patterns

| Pattern | Implementation |
|---------|----------------|
| Fallback Chain | Claude → GPT-5 → Gemini |
| Circuit Breaker | Per-provider state machine |
| Graceful Degradation | Layer 4: Never fail |
| Retry with Backoff | Exponential (1s → 2s → 4s) |
| Non-fatal Stages | DOC_INGEST, PROFILING |

### 13.3 Celery Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Concurrency | 2 workers | Long-running tasks |
| Hard Timeout | 10 min | Maximum execution |
| Soft Timeout | 9 min | Graceful shutdown |
| Prefetch Multiplier | 1 | Prevent task starvation |
| Result Expiration | 1 hour | Memory management |

### 13.4 Database Optimization

| Optimization | Implementation |
|--------------|----------------|
| Connection Pooling | Transaction mode (pgbouncer) |
| Statement Cache | Disabled (`statement_cache_size=0`) |
| Denormalized Index | `rkyc_signal_index` (no JOINs) |
| Vector Index | HNSW (m=16, ef_construction=64) |
| Batch Inserts | Signals + evidence in transaction |

---

## 14. Deployment Architecture

### 14.1 Infrastructure

```
┌───────────────────────────────────────────────────────────────┐
│                         VERCEL                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    Frontend                              │  │
│  │  - React 18 + TypeScript + Vite                         │  │
│  │  - Auto-deploy on git push                              │  │
│  │  - Edge CDN                                             │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                        RAILWAY                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │   Backend API   │  │     Worker      │  │     Redis     │  │
│  │   (FastAPI)     │  │    (Celery)     │  │    (Queue)    │  │
│  │   uvicorn       │  │   solo pool     │  │   7.x        │  │
│  └─────────────────┘  └─────────────────┘  └───────────────┘  │
└───────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                       SUPABASE                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                PostgreSQL 15+                            │  │
│  │  - Region: ap-northeast-1 (Tokyo)                       │  │
│  │  - pgvector extension                                   │  │
│  │  - Transaction pooler (port 6543)                       │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

### 14.2 Environment Variables

#### Backend API (Railway)
```env
DATABASE_URL=postgresql://postgres.[ref]:[pwd]@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_ANON_KEY=[key]
SECRET_KEY=[random]
CORS_ORIGINS=https://rkyc-wine.vercel.app,http://localhost:3000
```

#### Worker (Railway)
```env
DATABASE_URL=[same as above]
CELERY_BROKER_URL=redis://[redis-host]:6379/0
CELERY_RESULT_BACKEND=redis://[redis-host]:6379/1
ANTHROPIC_API_KEY=[key]
OPENAI_API_KEY=[key]
GOOGLE_API_KEY=[key]
PERPLEXITY_API_KEY=[key]
```

#### Frontend (Vercel)
```env
VITE_API_URL=https://rkyc-production.up.railway.app
VITE_DEMO_MODE=true
```

### 14.3 Deployment Process

| Component | Trigger | Process |
|-----------|---------|---------|
| Frontend | Git push to main | Auto-deploy via Vercel |
| Backend | Git push to main | Auto-deploy via Railway |
| Worker | Git push to main | Auto-deploy via Railway |
| Database | Manual | SQL migrations via Supabase console |

---

## 15. Roadmap & Future Enhancements

### 15.1 Phase 1: MVP (Current) ✅

| Feature | Status |
|---------|--------|
| Signal detection pipeline | ✅ Complete |
| Corporation management | ✅ Complete |
| Evidence-grounded analysis | ✅ Complete |
| Corp Profiling (anti-hallucination) | ✅ Complete |
| Consensus Engine | ✅ Complete |
| Circuit Breaker | ✅ Complete |
| Dashboard & reporting | ✅ Complete |

### 15.2 Phase 2: Pilot (Planned)

| Feature | Description | Priority |
|---------|-------------|----------|
| Real-time notifications | WebSocket/SSE for new signals | P1 |
| Batch processing | Scheduled analysis for all corps | P1 |
| Advanced filtering | Date range, confidence level | P2 |
| Export improvements | Excel, customizable formats | P2 |
| User feedback loop | Signal accuracy tracking | P1 |

### 15.3 Phase 3: Production (Future)

| Feature | Description | Priority |
|---------|-------------|----------|
| On-premise LLM | Internal data processing | P0 |
| Portfolio analytics | Cross-company risk aggregation | P1 |
| ML signal scoring | Historical accuracy-based ranking | P2 |
| API integrations | Core banking system connection | P1 |
| Multi-tenancy | Bank-specific configurations | P2 |

### 15.4 Known Issues & Technical Debt

| Issue | Severity | Description |
|-------|----------|-------------|
| BUG-001 | P1 | Korean compound stopwords not handled in Consensus Engine |
| DEBT-001 | P2 | Cache eviction policy needs specification (LRU vs FIFO) |
| DEBT-002 | P3 | AWS SDK v2 deprecation warning |

---

## 16. Appendix

### 16.1 Seed Data (6 Companies, 29 Signals)

| Company | corp_id | Industry | Signals |
|---------|---------|----------|---------|
| 엠케이전자 | 8001-3719240 | C26 (Electronics) | 5 (D:3, I:1, E:1) |
| 동부건설 | 8000-7647330 | F41 (Construction) | 6 (D:4, I:1, E:1) |
| 전북식품 | 4028-1234567 | C10 (Food) | 5 (D:3, I:1, E:1) |
| 광주정밀기계 | 6201-2345678 | C29 (Machinery) | 4 (D:2, I:1, E:1) |
| 삼성전자 | 4301-3456789 | C21 (Pharma) | 5 (D:3, I:1, E:1) |
| 휴림로봇 | 6701-4567890 | D35 (Utilities) | 4 (D:2, I:1, E:1) |

**Signal Distribution**: DIRECT (17), INDUSTRY (7), ENVIRONMENT (5)

### 16.2 API Response Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | Success | Normal response |
| 400 | Bad Request | Invalid parameters, file type |
| 404 | Not Found | Corp/Signal not found |
| 409 | Conflict | Duplicate document hash |
| 422 | Validation Error | Schema validation failed |
| 500 | Server Error | Unexpected exception |

### 16.3 Database Migration Files

| File | Description |
|------|-------------|
| schema_v2.sql | Base schema (PRD 14章) |
| seed_v2.sql | Initial data (6 corps, 29 signals) |
| migration_v3_signal_status.sql | Signal status enum |
| migration_v5_vector.sql | pgvector for embeddings |
| migration_embedding_dimension.sql | 2000-dim upgrade |
| migration_v6_security_architecture.sql | External intel tables |
| migration_v7_corp_profile.sql | Corp profiling tables |

### 16.4 ADR Summary

| ADR | Decision |
|-----|----------|
| ADR-001 | 3-tier architecture with Worker-only LLM |
| ADR-002 | Multi-provider LLM with fallback chain |
| ADR-003 | Supabase PostgreSQL (Tokyo) |
| ADR-004 | Celery + Redis 8-stage pipeline |
| ADR-005 | Signal state machine + guardrails |
| ADR-006 | Vision LLM for document processing |
| ADR-007 | pgvector for similarity search |
| ADR-008 | 2-Track LLM security architecture |

### 16.5 Glossary

| Term | Definition |
|------|------------|
| rKYC | Really Know Your Customer |
| DIRECT Signal | Risk signal directly impacting specific company |
| INDUSTRY Signal | Sector-wide risk signal |
| ENVIRONMENT Signal | Macro/external risk signal |
| Evidence | Mandatory source attribution for signals |
| Internal Snapshot | Versioned internal data per company |
| Corp Profile | Business intelligence for signal grounding |
| Consensus Engine | Multi-source result merger |
| Circuit Breaker | Provider failure protection pattern |
| Guardrails | LLM output quality controls |

---

**Document End**

*Last Updated: 2026-01-20*
*Version: 2.0*
*Status: Production Ready*
