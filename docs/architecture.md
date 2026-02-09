# rKYC (Really Know Your Customer) 아키텍처

## 시스템 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              rKYC System                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐               │
│  │   Frontend   │─────▶│   Backend    │─────▶│   Worker     │               │
│  │   (Vercel)   │      │  (Railway)   │      │  (Railway)   │               │
│  │              │      │              │      │              │               │
│  │  React 18    │      │  FastAPI     │      │  Celery      │               │
│  │  TypeScript  │      │  Python      │      │  + Redis     │               │
│  │  TanStack    │      │  SQLAlchemy  │      │              │               │
│  └──────────────┘      └──────────────┘      └──────────────┘               │
│         │                     │                     │                        │
│         │                     │                     │                        │
│         │              ┌──────▼──────┐       ┌──────▼──────┐                │
│         │              │  Supabase   │       │  LLM APIs   │                │
│         │              │ PostgreSQL  │       │             │                │
│         │              │  (Tokyo)    │       │ Claude      │                │
│         │              └─────────────┘       │ GPT-5.2     │                │
│         │                                    │ Gemini 3    │                │
│         │                                    │ Perplexity  │                │
│         └────────────────────────────────────┴─────────────┘                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 컴포넌트별 역할

| 컴포넌트 | 역할 | LLM 키 | DB 접근 |
|---------|------|--------|---------|
| **Frontend** | UI/UX, 사용자 인터랙션 | ❌ | ❌ |
| **Backend API** | REST API, CRUD, Job 관리 | ❌ | ✅ |
| **Worker** | 분석 파이프라인, LLM 호출 | ✅ | ✅ |

---

## 분석 파이프라인 (9단계)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Analysis Pipeline                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │ SNAPSHOT │──▶│DOC_INGEST│──▶│PROFILING │──▶│ EXTERNAL │──▶│ CONTEXT  │  │
│  │          │   │          │   │          │   │          │   │          │  │
│  │내부 데이터│   │문서 파싱 │   │기업 프로 │   │뉴스/공시 │   │통합 컨텍│  │
│  │  수집    │   │PDF→Text │   │파일링    │   │  검색    │   │스트 구성│  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘  │
│                                      │                                       │
│                                      ▼                                       │
│                              ┌──────────────┐                               │
│                              │ Perplexity + │                               │
│                              │   Gemini     │                               │
│                              │  Grounding   │                               │
│                              └──────────────┘                               │
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐                 │
│  │  SIGNAL  │──▶│VALIDATION│──▶│  INDEX   │──▶│ INSIGHT  │                 │
│  │          │   │          │   │          │   │          │                 │
│  │3-Agent   │   │Anti-     │   │pgvector  │   │AI 인사이│                 │
│  │병렬 추출 │   │Hallucin. │   │임베딩    │   │트 생성   │                 │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 파이프라인 단계별 설명

| 단계 | 이름 | 역할 | 주요 기능 |
|------|------|------|----------|
| 1 | **SNAPSHOT** | 내부 데이터 수집 | Internal Snapshot에서 재무/비재무 데이터 로드 |
| 2 | **DOC_INGEST** | 문서 분석 | PDF 텍스트 파싱 + 정규식 + LLM 보완 |
| 3 | **PROFILING** | 기업 프로파일링 | Perplexity + Gemini로 외부 정보 수집 |
| 4 | **EXTERNAL** | 외부 검색 | 뉴스/공시/규제 정보 실시간 검색 |
| 5 | **CONTEXT** | 컨텍스트 구성 | 내부+외부 데이터 통합 컨텍스트 생성 |
| 6 | **SIGNAL** | 시그널 추출 | 3-Agent 병렬 분석으로 시그널 생성 |
| 7 | **VALIDATION** | 검증 | Anti-Hallucination 5-Layer 검증 |
| 8 | **INDEX** | 인덱싱 | pgvector 임베딩 저장 |
| 9 | **INSIGHT** | 인사이트 생성 | 최종 AI 리스크/기회 분석 리포트 |

---

## Multi-Agent Signal Extraction 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   Signal Agent Orchestrator                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        병렬 실행 (ThreadPoolExecutor)                 │    │
│  │                                                                       │    │
│  │   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐         │    │
│  │   │   DIRECT    │      │  INDUSTRY   │      │ ENVIRONMENT │         │    │
│  │   │   Agent     │      │   Agent     │      │   Agent     │         │    │
│  │   │             │      │             │      │             │         │    │
│  │   │ 8 event     │      │ 1 event     │      │ 1 event     │         │    │
│  │   │  types      │      │  type       │      │  type       │         │    │
│  │   └──────┬──────┘      └──────┬──────┘      └──────┬──────┘         │    │
│  │          │                    │                    │                 │    │
│  └──────────┼────────────────────┼────────────────────┼─────────────────┘    │
│             │                    │                    │                      │
│             ▼                    ▼                    ▼                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        중복 제거 (Deduplication)                      │    │
│  │                    event_signature 기반 해시 비교                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Cross-Validation (충돌 감지)                      │    │
│  │           - signal_type 불일치 감지                                   │    │
│  │           - impact_direction 불일치 감지                              │    │
│  │           - needs_review 플래그 자동 설정                             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      최종 시그널 병합 및 반환                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 서브 에이전트 상세 역할

#### 1. DirectSignalAgent (DIRECT)

| 항목 | 설명 |
|------|------|
| **역할** | 기업 직접 영향 시그널 추출 |
| **Signal Type** | `DIRECT` |
| **Event Types** | 8종 |
| **데이터 소스** | Internal Snapshot + 직접 관련 뉴스 |
| **신뢰도** | 내부 데이터 기반 HIGH confidence |

**처리하는 이벤트 유형:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    DIRECT Event Types (8종)                      │
├─────────────────────────────────────────────────────────────────┤
│  KYC_REFRESH              │ KYC 갱신 필요                        │
│  INTERNAL_RISK_GRADE_CHANGE│ 내부 신용등급 변경                   │
│  OVERDUE_FLAG_ON          │ 연체 플래그 활성화                    │
│  LOAN_EXPOSURE_CHANGE     │ 여신 노출 변화 (증감 20%+)            │
│  COLLATERAL_CHANGE        │ 담보 가치/상태 변화                   │
│  OWNERSHIP_CHANGE         │ 소유구조 변경 (5%+ 지분)              │
│  GOVERNANCE_CHANGE        │ 지배구조 변경 (대표이사, 이사회)       │
│  FINANCIAL_STATEMENT_UPDATE│ 재무제표 업데이트                    │
└─────────────────────────────────────────────────────────────────┘
```

**분석 포커스:**
- 연체, 등급, 담보, 여신 변화 (Internal Snapshot)
- 기업 직접 관련 뉴스/공시
- 오너 리스크, 경영진 변동

---

#### 2. IndustrySignalAgent (INDUSTRY)

| 항목 | 설명 |
|------|------|
| **역할** | 산업/업종 영향 시그널 추출 |
| **Signal Type** | `INDUSTRY` |
| **Event Types** | 1종 (`INDUSTRY_SHOCK`) |
| **데이터 소스** | 업종 뉴스, 시장 동향 |
| **특징** | `{corp_name}에 미치는 영향` 문장 필수 |

**처리하는 이벤트 유형:**
```
┌─────────────────────────────────────────────────────────────────┐
│                   INDUSTRY Event Type (1종)                      │
├─────────────────────────────────────────────────────────────────┤
│  INDUSTRY_SHOCK           │ 업종 전반에 영향을 미치는 이벤트      │
│                           │                                      │
│  예시:                                                           │
│  - 반도체 수출규제 강화                                           │
│  - 자동차 업계 파업                                               │
│  - 원자재 가격 급등                                               │
│  - 신규 경쟁자 시장 진입                                          │
│  - 기술 패러다임 변화                                             │
└─────────────────────────────────────────────────────────────────┘
```

**분석 포커스:**
- 업종 전체에 영향을 미치는 시장 변화
- 공급망 이슈 (Supply Chain Disruption)
- 경쟁 구도 변화
- 수요 트렌드 변화

---

#### 3. EnvironmentSignalAgent (ENVIRONMENT)

| 항목 | 설명 |
|------|------|
| **역할** | 거시환경/정책 영향 시그널 추출 |
| **Signal Type** | `ENVIRONMENT` |
| **Event Types** | 1종 (`POLICY_REGULATION_CHANGE`) |
| **데이터 소스** | 정책/규제/거시경제 뉴스 |
| **특징** | Corp Profile 기반 조건부 쿼리 선택 |

**처리하는 이벤트 유형:**
```
┌─────────────────────────────────────────────────────────────────┐
│                ENVIRONMENT Event Type (1종)                      │
├─────────────────────────────────────────────────────────────────┤
│  POLICY_REGULATION_CHANGE │ 정책/규제 변화                       │
│                           │                                      │
│  11개 카테고리:                                                   │
│  ├── FX_RISK              │ 환율 리스크 (수출비중 30%+)          │
│  ├── TRADE_BLOC           │ 무역 블록 (미국/중국 노출)           │
│  ├── GEOPOLITICAL         │ 지정학 리스크                        │
│  ├── SUPPLY_CHAIN         │ 글로벌 공급망 이슈                   │
│  ├── REGULATION           │ 산업 규제 변화                       │
│  ├── COMMODITY            │ 원자재 가격/수급                     │
│  ├── PANDEMIC_HEALTH      │ 팬데믹/보건 이슈                     │
│  ├── POLITICAL_INSTABILITY│ 정치 불안정                         │
│  ├── CYBER_TECH           │ 사이버/기술 리스크 (C26, C21)        │
│  ├── ENERGY_SECURITY      │ 에너지 안보 (D35)                   │
│  └── FOOD_SECURITY        │ 식량 안보 (C10)                     │
└─────────────────────────────────────────────────────────────────┘
```

**조건부 쿼리 선택 로직:**
| 조건 | 활성화되는 쿼리 |
|------|----------------|
| `export_ratio >= 30%` | FX_RISK, TRADE_BLOC |
| 중국 노출 | GEOPOLITICAL, SUPPLY_CHAIN, REGULATION |
| 미국 노출 | GEOPOLITICAL, REGULATION, TRADE_BLOC |
| `key_materials` 존재 | COMMODITY, SUPPLY_CHAIN |
| `overseas_operations` 존재 | GEOPOLITICAL, PANDEMIC_HEALTH, POLITICAL_INSTABILITY |
| 업종 C26/C21 | CYBER_TECH |
| 업종 D35 | ENERGY_SECURITY |
| 업종 C10 | FOOD_SECURITY |

---

### Orchestrator 핵심 기능

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SignalAgentOrchestrator Features                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. 병렬 실행                                                                │
│     └── ThreadPoolExecutor로 3-Agent 동시 실행                              │
│     └── 예상 속도: 30초 → 12초 (60% 단축)                                   │
│                                                                              │
│  2. 중복 제거 (Deduplication)                                                │
│     └── event_signature (SHA256 해시) 기반                                  │
│     └── 동일 이벤트 여러 Agent가 감지해도 1개만 저장                         │
│                                                                              │
│  3. Cross-Validation                                                         │
│     └── signal_type 불일치 감지                                             │
│     └── impact_direction 불일치 감지                                        │
│     └── needs_review 플래그 자동 설정                                       │
│                                                                              │
│  4. Graceful Degradation                                                     │
│     └── Agent 실패 시 다른 Agent 결과만으로 진행                            │
│     └── partial_failure 플래그로 추적                                       │
│     └── DIRECT Agent 실패 시 Rule-based Fallback                            │
│                                                                              │
│  5. Concurrency Limit                                                        │
│     └── Provider별 동시 요청 제한                                           │
│     └── Claude: 3, OpenAI: 5, Gemini: 10, Perplexity: 5                     │
│                                                                              │
│  6. Celery Distributed Execution (선택)                                      │
│     └── celery.group()으로 Multi-worker 분산 실행                           │
│     └── 개별 Agent 재시도 지원 (max_retries=2)                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Corp Profiling Pipeline (4-Layer Fallback)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Corp Profiling 4-Layer Fallback                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Layer 0: Cache                                                              │
│     └── TTL 7일 내 캐시 히트 → 즉시 반환                                    │
│                │                                                             │
│                ▼ (캐시 미스)                                                 │
│  Layer 1+1.5: Perplexity + Gemini                                           │
│     ├── Perplexity sonar-pro (Primary Search)                               │
│     └── Gemini Grounding (Validation + Enrichment)                          │
│                │                                                             │
│                ▼ (실패 시)                                                   │
│  Layer 2: Claude Synthesis                                                   │
│     └── Consensus Engine 또는 Claude 합성                                   │
│                │                                                             │
│                ▼ (실패 시)                                                   │
│  Layer 3: Rule-Based Merge                                                   │
│     └── 소스 우선순위 기반 결정론적 병합                                    │
│                │                                                             │
│                ▼ (실패 시)                                                   │
│  Layer 4: Graceful Degradation                                               │
│     └── 최소 프로필 + _degraded 플래그                                      │
│     └── 기존 프로필에서 안전한 필드 복사                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## LLM Multi-Provider 전략

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM Fallback Chain                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐                                                         │
│  │    Primary     │  Claude Opus 4.5                                        │
│  │                │  claude-opus-4-5-20251101                                │
│  └───────┬────────┘                                                         │
│          │ 실패 시                                                           │
│          ▼                                                                   │
│  ┌────────────────┐                                                         │
│  │   Fallback 1   │  GPT-5.2 Pro                                            │
│  │                │  gpt-5.2-pro-2025-12-11                                  │
│  └───────┬────────┘                                                         │
│          │ 실패 시                                                           │
│          ▼                                                                   │
│  ┌────────────────┐                                                         │
│  │   Fallback 2   │  Gemini 3 Pro Preview                                   │
│  │                │  gemini/gemini-3-pro-preview                             │
│  └────────────────┘                                                         │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                         검색 내장 LLM 2-Track                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐      ┌────────────────┐                                 │
│  │    Primary     │      │    Fallback    │                                 │
│  │   Perplexity   │─────▶│     Gemini     │                                 │
│  │   sonar-pro    │실패시│   Grounding    │                                 │
│  └────────────────┘      └────────────────┘                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Anti-Hallucination 5-Layer Defense

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Anti-Hallucination Defense                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Layer 1 ─── Soft Guardrails ────── LLM 프롬프트 권고                        │
│      │       "당신은 사서입니다. 분석가가 아닙니다."                         │
│      │       "I don't know는 유효한 답변입니다."                             │
│      ▼                                                                       │
│  Layer 2 ─── Number Validation ──── 50%+ 극단적 수치 검증                    │
│      │       입력 데이터에 없는 극단적 수치 → 거부                           │
│      │       30%+ 수치 → needs_review 플래그                                 │
│      ▼                                                                       │
│  Layer 3 ─── Evidence Validation ── URL/Keypath 실존 검증                    │
│      │       Evidence URL이 실제 검색 결과에 있는지 확인                     │
│      │       SNAPSHOT_KEYPATH가 실제 존재하는지 확인                         │
│      ▼                                                                       │
│  Layer 4 ─── Entity Confusion ───── 기업명 일치 검증                         │
│      │       극단적 이벤트(상장폐지, 부도) 시 기업명 필수 확인               │
│      │       다른 기업명 감지 시 Entity Confusion 경고                       │
│      ▼                                                                       │
│  Layer 5 ─── Gemini Fact-Check ──── Google Search 팩트체크                   │
│              Gemini 2.0 Flash + Google Search Grounding                      │
│              FALSE 판정 → 시그널 거부                                        │
│              VERIFIED/PARTIAL → 통과                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 데이터베이스 스키마 (핵심 테이블)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Database Schema                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐     ┌─────────────────────┐     ┌─────────────────┐        │
│  │    corp     │────▶│ rkyc_internal_      │     │ rkyc_corp_      │        │
│  │  (기업 마스터)│     │     snapshot        │     │    profile      │        │
│  └─────────────┘     │  (내부 스냅샷)       │     │ (외부 프로파일) │        │
│         │            └─────────────────────┘     └─────────────────┘        │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                        rkyc_signal                               │        │
│  │  ┌─────────────┬─────────────┬─────────────┐                    │        │
│  │  │   DIRECT    │  INDUSTRY   │ ENVIRONMENT │  signal_type       │        │
│  │  │  (8 types)  │ (1 type)    │  (1 type)   │                    │        │
│  │  └─────────────┴─────────────┴─────────────┘                    │        │
│  └──────────────────────────┬──────────────────────────────────────┘        │
│                             │                                                │
│                             ▼                                                │
│  ┌─────────────────────┐   ┌─────────────────────┐                          │
│  │   rkyc_evidence     │   │  rkyc_signal_index  │                          │
│  │    (근거 데이터)     │   │  (Dashboard 전용)   │                          │
│  └─────────────────────┘   └─────────────────────┘                          │
│                                                                              │
│  ┌─────────────────────┐                                                    │
│  │     rkyc_job        │  분석 작업 관리                                     │
│  │  QUEUED → RUNNING   │                                                    │
│  │  → DONE / FAILED    │                                                    │
│  └─────────────────────┘                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Signal Type & Event Type 요약

| Signal Type | Event Types | Agent | 설명 |
|-------------|-------------|-------|------|
| **DIRECT** | 8종 | DirectSignalAgent | 기업 직접 리스크 |
| **INDUSTRY** | 1종 (INDUSTRY_SHOCK) | IndustrySignalAgent | 산업/업종 리스크 |
| **ENVIRONMENT** | 1종 (POLICY_REGULATION_CHANGE) | EnvironmentSignalAgent | 환경/정책 리스크 |

---

## 기술 스택 요약

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, TypeScript, Vite, TanStack Query, shadcn/ui, Tailwind CSS |
| **Backend** | FastAPI, Python 3.11+, SQLAlchemy 2.0, Pydantic v2 |
| **Worker** | Celery, Redis, litellm |
| **Database** | Supabase PostgreSQL, pgvector |
| **LLM** | Claude Opus 4.5, GPT-5.2 Pro, Gemini 3 Pro, Perplexity sonar-pro |
| **Deploy** | Vercel (Frontend), Railway (Backend + Worker) |

---

## 배포 URL

| 컴포넌트 | URL |
|---------|-----|
| Frontend | https://rkyc-wine.vercel.app |
| Backend API | https://rkyc-production.up.railway.app |
| Health Check | https://rkyc-production.up.railway.app/health |
