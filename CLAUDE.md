# rKYC (Really Know Your Customer) - Project Memory

## 프로젝트 개요
금융기관 기업심사 담당자를 위한 AI 기반 리스크 시그널 탐지 및 분석 시스템.
실시간 외부 데이터 모니터링을 통해 기업 리스크를 조기 탐지하고, 근거 기반 인사이트를 제공한다.

## 아키텍처 개요

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│  Backend    │────▶│  Database   │◀────│   Worker    │
│  (Vercel)   │     │  (FastAPI)  │     │ (Supabase)  │     │  (Celery)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     │                    │                   │                    │
     │                    │                   │                    │
   No LLM              No LLM            PostgreSQL            LLM Keys
   No DB               Has DB            ap-northeast-1        Has DB
```

### 물리적 제약 조건 (Critical)
| 컴포넌트 | LLM 키 | DB 접근 | 비고 |
|---------|--------|---------|------|
| Frontend | ❌ 없음 | ❌ 없음 | Vercel 호스팅, API 호출만 |
| Backend API | ❌ 없음 | ✅ 있음 | FastAPI, CRUD 전용 |
| Worker | ✅ 있음 | ✅ 있음 | Celery, 모든 LLM 호출 담당 |

## 기술 스택

### Frontend (배포 완료 ✅)
- Framework: React 18 + TypeScript + Vite
- UI: shadcn/ui + Tailwind CSS
- State: TanStack Query
- Routing: React Router v6
- Deploy: **Vercel** (https://rkyc-wine.vercel.app/)

### Backend (배포 완료 ✅)
- Framework: FastAPI + Python 3.11+
- ORM: SQLAlchemy 2.0 + asyncpg
- Validation: Pydantic v2
- Auth: Supabase Auth (JWT) - PRD 2.3에 따라 대회 범위 제외
- Deploy: **Railway** (https://rkyc-production.up.railway.app)
- **pgbouncer 호환**: `statement_cache_size=0` 설정 필수

### Worker (구현 예정)
- Queue: Celery + Redis
- LLM: litellm (multi-provider routing)
- Primary: Claude Sonnet 4 (claude-sonnet-4-20250514)
- Fallback: GPT-4o, Gemini 1.5 Pro
- External: Perplexity sonar-pro (외부 검색)

### Database
- Supabase PostgreSQL (Tokyo ap-northeast-1)
- Connection: SSL required (sslmode=require)
- Pooler: Transaction mode (port 6543)

## 핵심 도메인 개념 (PRD 14장 기준)

### 기업 (corp)
- 고유 식별: `corp_id` (고객번호, 예: '8001-3719240')
- `corp_reg_no`: 법인번호
- `biz_no`: 사업자등록번호 (가라 허용)
- `industry_code`: 업종코드 (예: 'C26')

### Internal Snapshot (rkyc_internal_snapshot)
- 기업의 내부 데이터 스냅샷 (버전 관리)
- `snapshot_json`: PRD 7장 스키마 준수 JSON
- `snapshot_hash`: sha256 해시 (변경 감지)
- `rkyc_internal_snapshot_latest`: 최신 포인터 테이블

### 시그널 (rkyc_signal) - PRD 9장, 10장
**signal_type 3종:**
| Type | 설명 | 허용 event_type |
|------|------|----------------|
| DIRECT | 직접 리스크 | KYC_REFRESH, INTERNAL_RISK_GRADE_CHANGE, OVERDUE_FLAG_ON, LOAN_EXPOSURE_CHANGE, COLLATERAL_CHANGE, OWNERSHIP_CHANGE, GOVERNANCE_CHANGE, FINANCIAL_STATEMENT_UPDATE |
| INDUSTRY | 산업 리스크 | INDUSTRY_SHOCK |
| ENVIRONMENT | 환경 리스크 | POLICY_REGULATION_CHANGE |

**event_type 10종 (PRD 9장):**
1. `KYC_REFRESH` - KYC 갱신
2. `INTERNAL_RISK_GRADE_CHANGE` - 내부 등급 변경
3. `OVERDUE_FLAG_ON` - 연체 플래그 활성화
4. `LOAN_EXPOSURE_CHANGE` - 여신 노출 변화
5. `COLLATERAL_CHANGE` - 담보 변화
6. `OWNERSHIP_CHANGE` - 소유구조 변화
7. `GOVERNANCE_CHANGE` - 지배구조 변화
8. `FINANCIAL_STATEMENT_UPDATE` - 재무제표 업데이트
9. `INDUSTRY_SHOCK` - 산업 이벤트
10. `POLICY_REGULATION_CHANGE` - 정책/규제 변화

**필수 필드:**
- `event_signature`: sha256 해시 (중복 방지)
- `impact_direction`: RISK, OPPORTUNITY, NEUTRAL
- `impact_strength`: HIGH, MED, LOW
- `confidence`: HIGH, MED, LOW

### 근거 (rkyc_evidence) - 별도 테이블
- `evidence_type`: INTERNAL_FIELD, DOC, EXTERNAL
- `ref_type`: SNAPSHOT_KEYPATH, DOC_PAGE, URL
- `ref_value`: JSON Pointer 형식 (예: `/credit/loan_summary/overdue_flag`)
- **필수**: 모든 시그널은 최소 1개 evidence 필요

### Dashboard 인덱스 (rkyc_signal_index)
- 조인 금지! Denormalized 테이블
- `corp_name`, `industry_code` 포함 (성능 최적화)

## Worker 파이프라인 (8단계)

```
SNAPSHOT → DOC_INGEST → EXTERNAL → CONTEXT → SIGNAL → VALIDATION → INDEX → INSIGHT
```

1. **SNAPSHOT**: 재무/비재무 데이터 수집
2. **DOC_INGEST**: 제출 문서 OCR/파싱
3. **EXTERNAL**: Perplexity 외부 정보 검색
4. **CONTEXT**: 인사이트 메모리 유사 케이스 조회
5. **SIGNAL**: LLM 시그널 추출 (Claude Sonnet 4)
6. **VALIDATION**: 시그널 검증 및 중복 제거
7. **INDEX**: 벡터 인덱싱 (pgvector)
8. **INSIGHT**: 최종 인사이트 생성

## Guardrails (필수 준수)

### LLM 접근 제한
- UI/Frontend: LLM 직접 호출 금지
- API Server: LLM 키 보유 금지
- Worker만 LLM 호출 가능

### 출력 품질 규칙
- 모든 시그널에 evidence(출처) 필수
- 단정적 표현 금지: "~일 것이다", "반드시", "즉시 조치 필요"
- 허용 표현: "~로 추정됨", "~가능성 있음", "검토 권고"

### 에러 처리
- LLM 실패 시 fallback 체인 적용
- 최대 재시도: 3회 (지수 백오프)
- 실패 시 원본 데이터 보존

## API 엔드포인트 구조

### 기업 관리
- `GET /api/v1/corporations` - 기업 목록
- `GET /api/v1/corporations/{corp_id}` - 기업 상세
- `POST /api/v1/corporations` - 기업 등록
- `PATCH /api/v1/corporations/{corp_id}` - 기업 수정

### 시그널 관리
- `GET /api/v1/signals` - 시그널 목록 (필터링 지원)
- `GET /api/v1/signals/{signal_id}` - 시그널 상세
- `PATCH /api/v1/signals/{signal_id}/status` - 상태 변경
- `POST /api/v1/signals/{signal_id}/dismiss` - 시그널 기각

### 분석 작업 (Demo Mode) ✅ 세션 4 완료
- `POST /api/v1/jobs/analyze/run` - 분석 트리거 (Demo)
- `GET /api/v1/jobs/{job_id}` - 작업 상태 조회
- `GET /api/v1/jobs` - 작업 목록 조회

## 데이터베이스 스키마 v2 (PRD 14장)

### Core Master (14.1)
- `corp` - 기업 마스터 (corp_id PK)
- `industry_master` - 업종 마스터

### Internal Snapshot (14.2)
- `rkyc_internal_snapshot` - 스냅샷 버전 관리
- `rkyc_internal_snapshot_latest` - 최신 포인터

### Documents (14.3-14.4)
- `rkyc_document` - 제출 문서 메타
- `rkyc_document_page` - 페이지별 정보
- `rkyc_fact` - 문서 추출 팩트

### External Events (14.5)
- `rkyc_external_event` - 외부 이벤트 (뉴스, 공시)
- `rkyc_external_event_target` - 기업-이벤트 매핑

### Unified Context (14.6)
- `rkyc_unified_context` - 통합 컨텍스트

### Signals (14.7) - 핵심!
- `rkyc_signal` - 시그널 (signal_type 3종, event_type 10종)
- `rkyc_evidence` - 근거 (별도 테이블)
- `rkyc_signal_index` - Dashboard 전용 (조인 금지)
- `rkyc_dashboard_summary` - 요약 통계

### Insight Memory (14.8)
- `rkyc_case_index` - 케이스 인덱스

### Jobs (14.9)
- `rkyc_job` - 분석 작업

## Internal Snapshot JSON 스키마 (PRD 7장)

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
  "collateral": { ... },
  "derived_hints": { ... }
}
```

**key_path 규칙**: JSON Pointer 형식
- 예: `/credit/loan_summary/total_exposure_krw`
- 예: `/corp/kyc_status/internal_risk_grade`

## 시드 데이터 v2 (6개 기업, 29개 시그널)

| 기업명 | corp_id | industry_code | Signal (D/I/E) |
|-------|---------|---------------|----------------|
| 엠케이전자 | 8001-3719240 | C26 | 5개 (3/1/1) |
| 동부건설 | 8000-7647330 | F41 | 6개 (4/1/1) |
| 전북식품 | 4028-1234567 | C10 | 5개 (3/1/1) |
| 광주정밀기계 | 6201-2345678 | C29 | 4개 (2/1/1) |
| 익산바이오텍 | 4301-3456789 | C21 | 5개 (3/1/1) |
| 나주태양에너지 | 6701-4567890 | D35 | 4개 (2/1/1) |

**Signal 분포:**
- DIRECT: 17개
- INDUSTRY: 7개
- ENVIRONMENT: 5개

## 현재 진행 상황

### 완료
- [x] Frontend 구현 및 배포 (Vercel)
- [x] UI 컴포넌트 (shadcn/ui)
- [x] 페이지 라우팅 구조
- [x] Mock 데이터 연동
- [x] PRD 분석 및 CLAUDE.md 생성
- [x] ADR 문서 5개 작성 (아키텍처 결정 기록)
- [x] 개발 계획서 (dev-plan.md) 작성
- [x] 서브에이전트 설정 (.claude/)
- [x] 백엔드 폴더 구조 및 플레이스홀더 파일
- [x] 데이터베이스 스키마 v1 (schema.sql) - 구버전
- [x] **스키마 재설계 v2 (schema_v2.sql)** - PRD 14장 기준
- [x] **시드 데이터 v2 (seed_v2.sql)** - 6개 기업 + 29개 시그널
- [x] **Supabase 프로젝트 생성 및 스키마/시드 적용** (Tokyo 리전)
- [x] **Backend API 구현 완료** (FastAPI + SQLAlchemy 2.0)
  - 기업 CRUD API (`/api/v1/corporations`)
  - 시그널 조회 API (`/api/v1/signals`)
  - pgbouncer 호환 설정 적용
- [x] **Railway 배포 완료** (https://rkyc-production.up.railway.app)
- [x] **Frontend-Backend 연동 완료**
  - API 클라이언트 (`src/lib/api.ts`)
  - TanStack Query 훅 (`src/hooks/useApi.ts`)
  - SignalInbox, CorporationSearch 페이지 API 전환
- [x] **Vercel 환경변수 및 CORS 설정 완료**
- [x] **Demo Mode UI 구현** (PRD 5.4.2 기반)
  - DemoPanel 컴포넌트 (`src/components/demo/DemoPanel.tsx`)
  - SignalInbox 페이지에 통합
  - VITE_DEMO_MODE 환경변수로 제어
- [x] **Job Trigger API 구현**
  - Job 모델 (`backend/app/models/job.py`)
  - POST /api/v1/jobs/analyze/run
  - GET /api/v1/jobs/{job_id}
  - useAnalyzeJob, useJobStatus 훅

### 대기 중 (세션 5에서)
- [ ] 시그널 상태 변경 API (PATCH /signals/{id}/status)
- [ ] 시그널 기각 API (POST /signals/{id}/dismiss)
- [ ] Worker 구현 시작 (Celery + Redis + LLM)

## 파일 구조

```
rkyc/
├── CLAUDE.md                 # 이 파일
├── docs/
│   ├── dev-plan.md          # 개발 계획서
│   └── architecture/
│       ├── ADR-001-*.md     # 아키텍처 결정 기록
│       └── ...
├── .claude/
│   ├── settings.json        # Claude Code 설정
│   └── agents/              # 서브에이전트 설정
├── src/                     # Frontend (완료)
│   ├── components/
│   │   └── demo/
│   │       └── DemoPanel.tsx  # Demo Mode 패널 ✅
│   ├── pages/
│   ├── hooks/
│   │   └── useApi.ts        # API 훅 (TanStack Query) + Job 훅
│   ├── lib/
│   │   └── api.ts           # API 클라이언트 + Job API
│   └── data/                # Mock 데이터 (Demo Mode용)
└── backend/                 # Backend (구현 완료)
    ├── app/
    │   ├── api/v1/endpoints/
    │   │   ├── corporations.py
    │   │   ├── signals.py
    │   │   └── jobs.py      # Job API ✅
    │   ├── models/
    │   │   └── job.py       # Job 모델 ✅
    │   ├── schemas/
    │   │   └── job.py       # Job 스키마 ✅
    │   ├── services/
    │   └── worker/
    └── sql/
        ├── schema.sql       # DDL v1 (구버전)
        ├── schema_v2.sql    # DDL v2 (PRD 14장 기준) ✅
        ├── seed.sql         # 시드 v1 (구버전)
        └── seed_v2.sql      # 시드 v2 (29개 시그널) ✅
```

## 세션 로그

### 세션 1 (2025-12-31) - 설계 및 문서화 ✅
**목표**: 코드 작성 없이 설계와 문서화만 수행

**완료 항목**:
1. PRD 분석 (72페이지, 3개 스펙 문서)
2. CLAUDE.md 초안 작성
3. ADR 문서 5개 작성
   - ADR-001: 아키텍처 분리 원칙 (LLM 격리)
   - ADR-002: LLM Provider 전략 (Fallback 체인)
   - ADR-003: 데이터베이스 선택 (Supabase)
   - ADR-004: Worker 파이프라인 설계
   - ADR-005: 시그널 상태 관리 및 Guardrails
4. dev-plan.md (개발 계획서) 작성
5. .claude/ 서브에이전트 설정
6. backend/ 폴더 구조 생성 (플레이스홀더)
7. schema.sql v1 (초안)
8. seed.sql v1 (초안)

### 세션 1-2 (2025-12-31) - 스키마 재설계 ✅
**목표**: PRD 14장 기준으로 스키마 재설계

**완료 항목**:
1. schema_v2.sql 작성 (PRD 14장 준수)
   - signal_type 3종: DIRECT, INDUSTRY, ENVIRONMENT
   - event_type 10종 ENUM
   - rkyc_evidence 별도 테이블
   - rkyc_signal_index (Dashboard 전용)
   - rkyc_internal_snapshot + latest 포인터
2. seed_v2.sql 작성
   - 6개 기업 + 업종 마스터
   - 6개 Internal Snapshot (PRD 7장 스키마)
   - 5개 External Events
   - 29개 Signal (DIRECT 17, INDUSTRY 7, ENVIRONMENT 5)
   - 29개 Evidence (시그널별 1개 이상)
   - Dashboard Summary 초기 데이터
3. CLAUDE.md 업데이트
   - 핵심 도메인 개념 (PRD 기준)
   - 스키마 테이블 목록
   - Snapshot JSON 스키마
   - 시드 데이터 현황

### 세션 1-3 (2025-12-31) - Seed 파일 UUID 오류 수정 ✅
**문제**: seed_v2.sql의 UUID 형식 오류
- `sig00001-0001-0001-0001-000000000001` 형태 사용
- Supabase 실행 시 오류: `ERROR: 22P02: invalid input syntax for type uuid`

**원인**: UUID는 16진수(0-9, a-f)만 허용
- 's', 'i', 'g', 'v', 't' 등 문자열 접두사 사용 불가
- UUID 형식: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (각 x는 hex만)

**해결**: 유효한 UUID 형식으로 전체 수정
- Signal UUID: `00000001-0001-0001-0001-000000000001` ~ `00000029-...`
- External Event UUID: `eeeeeeee-0001-0001-0001-000000000001` ~ `eeeeeeee-0005-...`
- Snapshot UUID: `11111111-0001-...`, `22222222-0001-...` (기업별)
- 구버전 파일: `seed_v2_deprecated.sql`로 보관

**추가 데이터**:
- `rkyc_internal_snapshot_latest`: 6개 기업의 최신 스냅샷 포인터
- `rkyc_external_event_target`: 5개 외부 이벤트-기업 매핑

**검증 쿼리**: seed_v2.sql 말미에 COUNT 확인 쿼리 포함

### 세션 2 (2025-12-31) - Backend API 구현 ✅
**목표**: FastAPI Backend 구현 및 Supabase 연결

**완료 항목**:
1. Supabase 프로젝트 설정 (Tokyo ap-northeast-1)
   - schema_v2.sql, seed_v2.sql 적용 완료
   - Transaction pooler (포트 6543) 사용
2. FastAPI Backend 구현
   - `app/core/config.py` - Pydantic Settings v2
   - `app/core/database.py` - SQLAlchemy 2.0 async engine
   - `app/models/corporation.py` - Corporation 모델
   - `app/models/signal.py` - SignalIndex 모델 + Enums
   - `app/schemas/` - Pydantic 스키마
   - `app/api/v1/endpoints/` - REST API 엔드포인트
3. 설정 오류 해결
   - CORS_ORIGINS: `List[str]` → `str` (pydantic-settings v2 호환)
   - DATABASE_URL: 비밀번호 특수문자 URL 인코딩 (`!` → `%21`)
   - pgbouncer 호환: `statement_cache_size=0` 설정
4. API 테스트 완료
   - `GET /api/v1/corporations` - 6개 기업 조회 성공
   - `GET /api/v1/signals` - 29개 시그널 조회 성공

**기술 이슈 해결**:
| 문제 | 원인 | 해결 |
|------|------|------|
| CORS_ORIGINS 파싱 오류 | pydantic-settings v2는 List 타입에 JSON 기대 | str 타입으로 변경, main.py에서 split |
| DB 비밀번호 인증 실패 | 특수문자 URL 인코딩 누락 | `!` → `%21` 인코딩 |
| prepared statement 충돌 | pgbouncer transaction mode 비호환 | `statement_cache_size=0` 설정 |

### 세션 3 (2025-12-31) - Railway 배포 및 Frontend 연동 ✅
**목표**: Backend를 Railway에 배포하고 Frontend와 연동

**완료 항목**:
1. Railway 배포 설정
   - `backend/Procfile` - uvicorn 시작 명령
   - `backend/railway.toml` - Nixpacks 빌드 설정
   - `backend/runtime.txt` - Python 3.11
   - 환경변수 설정 (DATABASE_URL, SUPABASE_*, SECRET_KEY, CORS_ORIGINS)
2. Frontend API 클라이언트 구현
   - `src/lib/api.ts` - fetch 기반 API 클라이언트
   - `src/hooks/useApi.ts` - TanStack Query 훅 + 데이터 변환
3. 페이지 API 전환
   - `SignalInbox.tsx` - useSignals 훅 적용
   - `CorporationSearch.tsx` - useCorporations 훅 적용
   - 로딩/에러 상태 UI 추가
4. CORS 설정
   - Railway CORS_ORIGINS에 Vercel 도메인 추가

**배포 URL**:
- Frontend: https://rkyc-wine.vercel.app/
- Backend: https://rkyc-production.up.railway.app
- API Health: https://rkyc-production.up.railway.app/health

**환경변수 (Vercel)**:
- `VITE_API_URL=https://rkyc-production.up.railway.app`
- `VITE_DEMO_MODE=false`

### 세션 4 (2025-12-31) - Demo Mode UI 및 Job API ✅
**목표**: PRD 5.4 Demo Mode UI 구현 및 Job Trigger API

**완료 항목**:
1. Backend Job API 구현
   - `app/models/job.py` - Job 모델 (rkyc_job 테이블 매핑)
   - `app/schemas/job.py` - Pydantic 스키마
   - `app/api/v1/endpoints/jobs.py` - API 엔드포인트
   - POST /api/v1/jobs/analyze/run (분석 트리거)
   - GET /api/v1/jobs/{job_id} (상태 조회)
   - GET /api/v1/jobs (목록 조회)
2. Frontend Job 훅 구현
   - `src/lib/api.ts` - triggerAnalyzeJob, getJobStatus 함수
   - `src/hooks/useApi.ts` - useAnalyzeJob, useJobStatus 훅
   - Job 상태 폴링 (QUEUED/RUNNING 시 2초 간격)
3. DemoPanel 컴포넌트
   - `src/components/demo/DemoPanel.tsx` - PRD 5.4.2 기반
   - 기업 선택 드롭다운
   - "분석 실행 (시연용)" 버튼
   - 작업 상태 표시 (대기/진행/완료/실패)
   - "접속/조회는 분석을 실행하지 않습니다" 안내 문구
4. SignalInbox 통합
   - DemoPanel을 SignalInbox 페이지 상단에 추가
   - VITE_DEMO_MODE=true일 때만 표시

**배포 완료**:
- Railway 재배포 (Job API 반영) ✅
- Vercel VITE_DEMO_MODE=true 설정 ✅
- Demo Panel UI 정상 동작 확인 ✅

**현재 상태**:
- Worker 미구현으로 Job이 QUEUED 상태 유지
- LLM API 키 설정 후 실제 분석 가능

## 다음 세션 작업 (세션 5)

### Phase 1: 시그널 상태 관리 API
1. PATCH /signals/{id}/status 구현
2. POST /signals/{id}/dismiss 구현

### Phase 2: Worker 기초
1. Celery + Redis 설정
2. LLM API 키 설정 (Anthropic, OpenAI 등)
3. 분석 파이프라인 구현

### 참고 사항
- **인증은 PRD 2.3에 따라 대회 범위 제외** - 구현하지 않음
- **schema_v2.sql, seed_v2.sql 사용** (v1은 deprecated)
- ADR 문서의 결정 사항 준수
- Guardrails 규칙 (금지 표현, evidence 필수) 적용
- Dashboard에서는 rkyc_signal_index 사용 (조인 금지)
- **Backend 로컬 실행**: `cd backend && uvicorn app.main:app --reload`

---
*Last Updated: 2025-12-31 (세션 4 완료 - Demo Mode UI 및 Job API)*
