# rKYC Development Plan

## 프로젝트 현황

### 완료된 작업
- [x] Frontend 구현 및 Vercel 배포
- [x] UI 컴포넌트 (shadcn/ui)
- [x] 페이지 라우팅 구조
- [x] Mock 데이터 연동
- [x] PRD 분석 및 문서화
- [x] ADR 작성 (5개)
- [x] **Backend API (FastAPI)** ✅ 세션 2 완료
- [x] **Database (Supabase PostgreSQL)** ✅ 세션 2 완료
- [x] **Railway 배포** ✅ 세션 3 완료
- [x] **Frontend-Backend 연동** ✅ 세션 3 완료
- [x] **Demo Mode UI (PRD 5.4)** ✅ 세션 4 완료
- [x] **Job Trigger API** ✅ 세션 4 완료

### 구현 대기
- [ ] Worker (Celery + Redis + LLM)
- [ ] 시그널 상태 관리 API (PATCH /signals/{id}/status)

---

## Phase 1: 인프라 및 기본 설정 ✅ 완료

### 1.1 Supabase 프로젝트 설정 ✅
- [x] Supabase 프로젝트 생성 (Tokyo 리전)
- [x] pgvector extension 활성화
- [x] Connection pooling 설정 (port 6543, Transaction mode)
- [ ] Row Level Security 정책 초안

### 1.2 Backend 프로젝트 초기화 ✅
- [x] FastAPI 프로젝트 구조 생성
- [x] pip 의존성 설정 (requirements.txt)
- [x] 환경 변수 설정 (.env.example)
- [x] **pgbouncer 호환 설정** (`statement_cache_size=0`)
- [ ] Docker 개발 환경 구성

### 1.3 Database 스키마 적용 ✅
- [x] schema_v2.sql 실행 (PRD 14장 기준)
- [x] seed_v2.sql 실행 (6개 기업 + 29개 시그널)
- [ ] 마이그레이션 도구 설정 (Alembic)

---

## Phase 2: 핵심 CRUD API ✅ 기본 구현 완료

### 2.1 기업 관리 API ✅
```
GET    /api/v1/corporations           # ✅ 목록 (페이지네이션, 필터)
GET    /api/v1/corporations/{id}      # ✅ 상세
POST   /api/v1/corporations           # ✅ 생성
PATCH  /api/v1/corporations/{id}      # ✅ 수정
DELETE /api/v1/corporations/{id}      # ⏳ 삭제 (soft delete) - 미구현
```

### 2.2 시그널 관리 API (부분 완료)
```
GET    /api/v1/signals                # ✅ 목록 (필터: corp_id, signal_type, event_type, impact 등)
GET    /api/v1/signals/{id}           # ✅ 상세
PATCH  /api/v1/signals/{id}/status    # ⏳ 상태 변경 - 미구현
POST   /api/v1/signals/{id}/dismiss   # ⏳ 기각 (사유 포함) - 미구현
```

### 2.3 분석 작업 API ✅ 세션 4 완료
```
POST   /api/v1/jobs/analyze/run       # ✅ 분석 트리거 (Demo Mode)
GET    /api/v1/jobs/{job_id}          # ✅ 작업 상태 조회
GET    /api/v1/jobs                   # ✅ 작업 목록 조회
```
- Worker 미구현 상태에서는 Job이 QUEUED 상태로 유지됨
- Worker 구현 후 실제 LLM 분석 실행 가능

---

## Phase 3: Railway 배포 및 Frontend 연동 ✅ 완료

### 3.1 Railway 배포 ✅
- [x] Procfile, railway.toml, runtime.txt 생성
- [x] 환경변수 설정 (DATABASE_URL, SUPABASE_*, SECRET_KEY, CORS_ORIGINS)
- [x] 배포 완료: https://rkyc-production.up.railway.app

### 3.2 Frontend API 클라이언트 ✅
- [x] `src/lib/api.ts` - fetch 기반 API 클라이언트
- [x] `src/hooks/useApi.ts` - TanStack Query 훅 + 데이터 변환
- [x] SignalInbox, CorporationSearch 페이지 API 전환

### 3.3 CORS 및 환경변수 ✅
- [x] Railway CORS_ORIGINS에 Vercel 도메인 추가
- [x] Vercel 환경변수: VITE_API_URL, VITE_DEMO_MODE

### 참고: 인증 (PRD 2.3에 따라 대회 범위 제외)
- ~~JWT 검증 미들웨어~~
- ~~사용자 세션 관리~~
- ~~역할 정의 (admin, analyst, viewer)~~

---

## Phase 4: Worker 파이프라인

### 4.1 Celery 설정
- [ ] Redis 브로커 연결
- [ ] 우선순위 큐 구성 (high, default, low)
- [ ] 재시도 정책 설정

### 4.2 파이프라인 단계 구현
```python
# 8단계 파이프라인
SNAPSHOT   → 재무/비재무 데이터 수집
DOC_INGEST → 문서 OCR/파싱
EXTERNAL   → Perplexity 외부 검색
CONTEXT    → 인사이트 메모리 조회
SIGNAL     → LLM 시그널 추출
VALIDATION → 검증 및 중복 제거
INDEX      → 벡터 인덱싱
INSIGHT    → 최종 인사이트 생성
```

### 4.3 LLM 연동
- [ ] litellm 설정
- [ ] Claude Sonnet 4 (Primary)
- [ ] Fallback 체인 (GPT-4o → Gemini)
- [ ] Perplexity (외부 검색)
- [ ] Embedding (text-embedding-3-small)

---

## Phase 5: Frontend 연동 ✅ 완료

### 5.1 API 클라이언트 ✅
- [x] Mock → 실제 API 전환
- [x] TanStack Query 설정
- [x] 에러 핸들링 (로딩/에러 상태 UI)

### 5.2 실시간 업데이트 (미구현 - 향후)
- [ ] Supabase Realtime 구독
- [ ] 시그널 상태 변경 알림
- [ ] 분석 진행 상태 표시

---

## Phase 6: 테스트 및 검증

### 6.1 Unit Tests
- [ ] API 엔드포인트 테스트
- [ ] 서비스 레이어 테스트
- [ ] Worker 태스크 테스트

### 6.2 Integration Tests
- [ ] DB 연동 테스트
- [ ] LLM 호출 테스트 (Mock)
- [ ] 파이프라인 E2E 테스트

### 6.3 Guardrails 검증
- [ ] Evidence 필수 검증
- [ ] 금지 표현 필터 테스트
- [ ] 중복 시그널 탐지 테스트

---

## Phase 7: 배포

### 7.1 Backend 배포 ✅ 완료
- [x] Railway 설정 (Nixpacks 빌드)
- [x] 환경 변수 구성
- [x] 도메인: https://rkyc-production.up.railway.app

### 7.2 Frontend 배포 ✅ 완료
- [x] Vercel 설정
- [x] 환경 변수 구성 (VITE_API_URL, VITE_DEMO_MODE)
- [x] 도메인: https://rkyc-wine.vercel.app

### 7.3 Worker 배포 (미구현)
- [ ] Redis 인스턴스 (Railway/Upstash)
- [ ] Worker 컨테이너 배포
- [ ] 스케일링 설정

### 7.4 모니터링 (미구현)
- [ ] Sentry 에러 추적
- [ ] Flower 대시보드
- [ ] 로깅 구성

---

## 기술 스택 상세

### Backend
| 항목 | 기술 | 버전 |
|-----|------|------|
| Framework | FastAPI | 0.109+ |
| Python | Python | 3.11+ |
| ORM | SQLAlchemy | 2.0+ |
| Async DB | asyncpg | latest |
| Validation | Pydantic | 2.0+ |
| Testing | pytest | latest |

### Worker
| 항목 | 기술 | 버전 |
|-----|------|------|
| Queue | Celery | 5.3+ |
| Broker | Redis | 7.0+ |
| LLM | litellm | latest |
| OCR | pytesseract | latest |

### Database
| 항목 | 기술 | 설정 |
|-----|------|------|
| Provider | Supabase | Pro Plan 권장 |
| Engine | PostgreSQL | 15+ |
| Region | Tokyo | ap-northeast-1 |
| Vector | pgvector | 0.5+ |

---

## 의존성 관리

### requirements.txt (Backend)
```
fastapi>=0.109.0
uvicorn>=0.27.0
sqlalchemy>=2.0.0
asyncpg>=0.29.0
pydantic>=2.0.0
python-jose>=3.3.0
python-multipart>=0.0.6
httpx>=0.26.0
```

### requirements.txt (Worker)
```
celery>=5.3.0
redis>=5.0.0
litellm>=1.0.0
openai>=1.0.0
anthropic>=0.18.0
numpy>=1.26.0
```

---

## 환경 변수

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbG...

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET=your-secret-key
```

### Worker (.env)
```bash
# Database
DATABASE_URL=postgresql://...

# Redis
CELERY_BROKER_URL=redis://localhost:6379/0

# LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
GOOGLE_API_KEY=...
```

---

## 위험 요소 및 완화 방안

| 위험 | 영향 | 완화 방안 |
|-----|------|----------|
| LLM API 장애 | 분석 중단 | Fallback 체인 구현 |
| DB 연결 풀 고갈 | API 응답 지연 | Connection pooling |
| Worker 메모리 부족 | 작업 실패 | 작업 크기 제한, 모니터링 |
| 과도한 LLM 비용 | 예산 초과 | 일일 한도 설정, 캐싱 |

---

## 다음 단계 (세션 5에서)

### 우선순위 1: 시그널 상태 관리 API
1. PATCH /signals/{id}/status 구현
2. POST /signals/{id}/dismiss 구현

### 우선순위 2: Worker 기초
1. Celery + Redis 설정
2. LLM API 키 설정 (Anthropic, OpenAI 등)
3. 분석 파이프라인 구현

### 우선순위 3: Railway 재배포
1. Backend Job API 배포
2. Vercel VITE_DEMO_MODE=true 설정

---

## 세션 로그

### 세션 1 (2025-12-31)
- PRD 분석 및 문서화
- ADR 5개 작성
- schema_v2.sql, seed_v2.sql 작성

### 세션 2 (2025-12-31)
- Supabase 프로젝트 설정 (Tokyo)
- FastAPI Backend 구현
- 기업/시그널 CRUD API
- pgbouncer 호환 이슈 해결

### 세션 3 (2025-12-31)
- Railway 배포 완료 (https://rkyc-production.up.railway.app)
- Frontend API 클라이언트 구현 (src/lib/api.ts, src/hooks/useApi.ts)
- SignalInbox, CorporationSearch 페이지 API 전환
- CORS 설정 및 Vercel 환경변수 구성
- Frontend-Backend 연동 완료

### 세션 4 (2025-12-31)
- **Demo Mode UI 구현** (PRD 5.4.2 기반)
  - `src/components/demo/DemoPanel.tsx` 생성
  - SignalInbox 페이지에 DemoPanel 통합
  - VITE_DEMO_MODE 환경변수로 표시 제어
- **Job Trigger API 구현**
  - `backend/app/models/job.py` - Job 모델 (rkyc_job 테이블)
  - `backend/app/schemas/job.py` - Pydantic 스키마
  - `backend/app/api/v1/endpoints/jobs.py` - API 엔드포인트
  - POST /api/v1/jobs/analyze/run (분석 트리거)
  - GET /api/v1/jobs/{job_id} (상태 조회)
  - GET /api/v1/jobs (목록 조회)
- **Frontend Job 훅 추가**
  - `useAnalyzeJob`, `useJobStatus` 훅 구현
  - Job 상태 폴링 (QUEUED/RUNNING 시 2초 간격)
- **현재 상태**: Worker 미구현으로 Job이 QUEUED 상태 유지

---

*Last Updated: 2025-12-31 (세션 4 완료 - Demo Mode UI 및 Job API)*
