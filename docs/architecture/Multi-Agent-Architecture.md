# rKYC Multi-Agent 아키텍처

> 작성일: 2026-02-09
> 관련 ADR: ADR-009, ADR-010

## 개요

rKYC 시스템은 기업 리스크 분석을 위해 **Multi-Agent 아키텍처**를 채택하고 있습니다. 이 문서는 전체 아키텍처 구조와 각 Agent의 역할을 설명합니다.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            9-Stage Pipeline                                  │
│  SNAPSHOT → DOC_INGEST → PROFILING → EXTERNAL → CONTEXT → SIGNAL →          │
│  VALIDATION → INDEX → INSIGHT                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
           ┌────────▼────────┐        ┌─────────▼─────────┐
           │ Corp Profiling  │        │ Signal Extraction │
           │   Orchestrator  │        │   Orchestrator    │
           │   (4-Layer)     │        │   (3-Agent)       │
           └────────┬────────┘        └─────────┬─────────┘
                    │                           │
```

---

## 1. Corp Profiling Orchestrator (4-Layer Fallback)

**파일**: `backend/app/worker/llm/orchestrator.py`

Corp Profiling Pipeline은 기업의 외부 정보를 수집하고 프로필을 생성합니다. 4-Layer Fallback 아키텍처로 **절대 실패하지 않는** 설계를 채택했습니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MultiAgentOrchestrator                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 0: CACHE                                                 │
│     └── 캐시된 프로필 조회 (TTL 7일)                              │
│                                                                 │
│  Layer 1: PERPLEXITY Search (Primary)                           │
│     └── 실시간 외부 검색 (sonar-pro)                              │
│                                                                 │
│  Layer 1.5: GEMINI Grounding (Fallback)                         │
│     └── Perplexity 실패 시 Google Search 기반 검색                │
│                                                                 │
│  Layer 2: OpenAI Validation                                     │
│     └── 검색 결과 검증 + Consensus Engine                         │
│                                                                 │
│  Layer 3: RULE_BASED Merge                                      │
│     └── LLM 없이 소스 우선순위 기반 결정론적 병합                    │
│                                                                 │
│  Layer 4: GRACEFUL_DEGRADATION                                  │
│     └── 최소 프로필 반환 + _degraded 플래그                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.1 Layer별 상세

| Layer | 이름 | 설명 | 실패 시 |
|-------|------|------|---------|
| 0 | Cache | 7일 TTL 캐시 조회 | Layer 1로 진행 |
| 1 | Perplexity | 실시간 검색 (Primary) | Layer 1.5로 진행 |
| 1.5 | Gemini Grounding | Google Search 기반 Fallback | Layer 2로 진행 |
| 2 | OpenAI Validation | 검색 결과 검증 + Consensus | Layer 3로 진행 |
| 3 | Rule-Based Merge | 결정론적 병합 | Layer 4로 진행 |
| 4 | Graceful Degradation | 최소 프로필 반환 | 항상 성공 |

### 1.2 핵심 컴포넌트

| 컴포넌트 | 파일 | 역할 |
|----------|------|------|
| **CircuitBreakerManager** | `circuit_breaker.py` | Provider별 장애 격리 |
| **ConsensusEngine** | `consensus_engine.py` | 다중 소스 결과 병합 |
| **MultiSearchManager** | `search_providers.py` | 검색 내장 LLM 2-Track |
| **GeminiAdapter** | `gemini_adapter.py` | Gemini Validation/Enrichment |

### 1.3 Circuit Breaker 설정

| Provider | failure_threshold | cooldown |
|----------|-------------------|----------|
| Perplexity | 3회 | 5분 |
| Gemini | 3회 | 5분 |
| Claude | 2회 | 10분 |

---

## 2. Signal Extraction Orchestrator (3-Agent 병렬)

**파일**: `backend/app/worker/pipelines/signal_agents/orchestrator.py`

Signal Extraction Pipeline은 3개의 전문화된 Agent를 **병렬 실행**하여 시그널을 추출합니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                  SignalAgentOrchestrator                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ DirectSignal    │  │ IndustrySignal  │  │ EnvironmentSignal│ │
│  │    Agent        │  │    Agent        │  │     Agent        │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤  │
│  │ Type: DIRECT    │  │ Type: INDUSTRY  │  │ Type: ENVIRONMENT│ │
│  │ Events: 8종     │  │ Events: 1종     │  │ Events: 1종      │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │           │
│           └────────────────────┼────────────────────┘           │
│                                │                                 │
│                    ThreadPoolExecutor (3 workers)               │
│                                │                                 │
│                    ┌───────────▼───────────┐                    │
│                    │   Deduplication       │                    │
│                    │  (event_signature)    │                    │
│                    └───────────┬───────────┘                    │
│                                │                                 │
│                    ┌───────────▼───────────┐                    │
│                    │  Cross-Validation     │                    │
│                    │  (conflict detection) │                    │
│                    └───────────┬───────────┘                    │
│                                │                                 │
│                    ┌───────────▼───────────┐                    │
│                    │  Graceful Degradation │                    │
│                    │  (Rule-based Fallback)│                    │
│                    └───────────────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.1 실행 흐름

1. **병렬 실행**: 3개 Agent가 ThreadPoolExecutor로 동시 실행
2. **Deduplication**: `event_signature` 해시 기반 중복 제거
3. **Cross-Validation**: signal_type/impact_direction 충돌 감지
4. **Graceful Degradation**: DIRECT Agent 실패 시 Rule-based Fallback

### 2.2 Orchestrator 설정

```python
SignalAgentOrchestrator(
    parallel_mode=True,           # 병렬 실행 활성화
    max_workers=3,                # 3개 Agent
    enable_concurrency_limit=True, # Provider 동시성 제한
    agent_timeout=30.0,           # Agent별 타임아웃 30초
)
```

---

## 3. Sub-Agent 상세

### 3.1 BaseSignalAgent (추상 클래스)

**파일**: `backend/app/worker/pipelines/signal_agents/base.py`

모든 Signal Agent의 공통 기능을 제공하는 추상 베이스 클래스입니다.

| 메서드 | 역할 |
|--------|------|
| `execute()` | LLM 호출 및 시그널 추출 |
| `_enrich_signal()` | 검증 + 메타데이터 추가 |
| `_detect_number_hallucination()` | 숫자 Hallucination 탐지 |
| `_validate_evidence_sources()` | Evidence URL 검증 |
| `_validate_entity_attribution()` | Entity Confusion 방지 |
| `_compute_signature()` | 중복 방지용 해시 계산 |
| `get_system_prompt()` | Agent별 시스템 프롬프트 (추상) |
| `get_user_prompt()` | Agent별 유저 프롬프트 (추상) |
| `get_relevant_events()` | 관련 이벤트 추출 (추상) |

### 3.2 DirectSignalAgent

**파일**: `backend/app/worker/pipelines/signal_agents/direct_agent.py`

| 항목 | 값 |
|------|-----|
| **signal_type** | DIRECT |
| **event_types** | 8종 |
| **데이터 소스** | Internal Snapshot, 직접 뉴스 |
| **신뢰도** | HIGH (내부 데이터 우선) |

**허용 event_types (8종)**:
- `KYC_REFRESH` - KYC 갱신
- `INTERNAL_RISK_GRADE_CHANGE` - 내부 등급 변경
- `OVERDUE_FLAG_ON` - 연체 플래그 활성화
- `LOAN_EXPOSURE_CHANGE` - 여신 노출 변화
- `COLLATERAL_CHANGE` - 담보 변화
- `OWNERSHIP_CHANGE` - 소유구조 변화
- `GOVERNANCE_CHANGE` - 지배구조 변화
- `FINANCIAL_STATEMENT_UPDATE` - 재무제표 업데이트

### 3.3 IndustrySignalAgent

**파일**: `backend/app/worker/pipelines/signal_agents/industry_agent.py`

| 항목 | 값 |
|------|-----|
| **signal_type** | INDUSTRY |
| **event_types** | 1종 (INDUSTRY_SHOCK) |
| **데이터 소스** | Industry Master, External Events |
| **필수 조건** | "{corp_name}에 미치는 영향" 문장 포함 |

**INDUSTRY_SHOCK 판단 기준**:
- 산업 전체에 적용되는 이벤트
- 다수 기업에 영향을 미치는 사건
- 발표 주체가 정부, 협회 등 공신력 있는 기관

### 3.4 EnvironmentSignalAgent

**파일**: `backend/app/worker/pipelines/signal_agents/environment_agent.py`

| 항목 | 값 |
|------|-----|
| **signal_type** | ENVIRONMENT |
| **event_types** | 1종 (POLICY_REGULATION_CHANGE) |
| **데이터 소스** | Corp Profile, Policy Events |
| **특징** | 조건부 쿼리 선택 (11개 카테고리) |

**쿼리 카테고리 (11종)**:

| 카테고리 | 활성화 조건 |
|----------|------------|
| FX_RISK | export_ratio >= 30% |
| TRADE_BLOC | export_ratio >= 30% |
| GEOPOLITICAL | country_exposure에 중국/미국 |
| SUPPLY_CHAIN | country_exposure 또는 key_materials |
| REGULATION | country_exposure에 중국/미국 |
| COMMODITY | key_materials 존재 |
| PANDEMIC_HEALTH | overseas_operations 존재 |
| POLITICAL_INSTABILITY | overseas_operations 존재 |
| CYBER_TECH | 업종 C26/C21 |
| ENERGY_SECURITY | 업종 D35 |
| FOOD_SECURITY | 업종 C10 |

---

## 4. Anti-Hallucination 5-Layer Defense

모든 시그널은 저장 전 5-Layer 검증을 통과해야 합니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                   Anti-Hallucination Defense                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: Soft Guardrails                                       │
│     └── LLM 프롬프트에서 금지 표현 권고                            │
│                                                                 │
│  Layer 2: Number Validation                                     │
│     └── 50%+ 극단적 수치는 입력 데이터에서 검증                     │
│                                                                 │
│  Layer 3: Evidence Validation                                   │
│     └── URL은 실제 검색 결과에서만 허용                            │
│     └── SNAPSHOT_KEYPATH는 실제 존재 확인                         │
│                                                                 │
│  Layer 4: Entity Confusion Prevention                           │
│     └── 극단적 이벤트(상장폐지 등)는 기업명 필수                     │
│     └── Evidence snippet에서 기업명 확인                          │
│                                                                 │
│  Layer 5: Gemini Grounding Fact-Check                           │
│     └── Google Search로 사실 확인                                 │
│     └── FALSE 판정 시 시그널 거부                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.1 금지 표현 목록

다음 표현이 포함된 시그널은 즉시 거부됩니다:

- **추정 표현**: "추정됨", "전망", "예상", "것으로 보인다"
- **불확실 표현**: "약", "대략", "정도", "내외", "가량"
- **단정 표현**: "반드시", "즉시", "확실히", "무조건"
- **예측 표현**: "~할 것이다", "~일 것이다"

### 4.2 retrieval_confidence 체계

| 레벨 | 설명 | 요구사항 |
|------|------|----------|
| `VERBATIM` | 원문 그대로 복사 | 필수 우선 |
| `PARAPHRASED` | 명확성을 위해 다듬음 | 허용 |
| `INFERRED` | 문맥에서 추론 | `confidence_reason` 필수 |

---

## 5. Concurrency Control

### 5.1 ProviderConcurrencyLimiter

**파일**: `backend/app/worker/pipelines/signal_agents/orchestrator.py`

Semaphore 기반으로 Provider별 동시 요청 수를 제한합니다.

| Provider | Limit | 용도 |
|----------|-------|------|
| Perplexity | 5 | 외부 검색 |
| Gemini | 10 | Validation/Grounding |
| Claude | 3 | Synthesis |
| OpenAI | 5 | Validation |

### 5.2 사용 예시

```python
limiter = get_concurrency_limiter()

# 슬롯 획득 (30초 타임아웃)
if limiter.acquire("perplexity", timeout=30.0):
    try:
        result = call_perplexity_api()
    finally:
        limiter.release("perplexity")
```

---

## 6. Celery 분산 실행

Multi-worker 환경에서 3-Agent를 분산 실행할 수 있습니다.

### 6.1 태스크 등록

```python
# Celery 태스크 (자동 등록)
@celery_app.task(name="signal.direct_agent", bind=True, max_retries=2)
def direct_agent_task(self, context: dict) -> dict:
    agent = DirectSignalAgent()
    signals = agent.execute(context)
    return {"agent": "direct", "status": "success", "signals": signals}
```

### 6.2 group() 실행

```python
from celery import group

# 3-Agent 병렬 실행
job = group(
    celery_app.signature("signal.direct_agent", args=[context]),
    celery_app.signature("signal.industry_agent", args=[context]),
    celery_app.signature("signal.environment_agent", args=[context]),
)

result = job.apply_async()
signals = result.get(timeout=120)  # 최대 2분 대기
```

### 6.3 분산 실행 함수

```python
from app.worker.pipelines.signal_agents.orchestrator import execute_distributed

# 자동으로 group() 생성 및 후처리
signals, metadata = execute_distributed(context, timeout=120.0)
```

---

## 7. 성능 개선 (ADR-009 기준)

| 항목 | 이전 | 이후 | 개선율 |
|------|------|------|--------|
| **전체 파이프라인** | ~120초 | ~50초 | **58%** |
| PROFILING (Layer 1+1.5) | 40초 | 30초 | 25% |
| SIGNAL 추출 | 30초 | 12초 | 60% |
| EXTERNAL (3-Track) | 20초 | 12초 | 40% |

---

## 8. Admin 모니터링 API

| Endpoint | Method | 설명 |
|----------|--------|------|
| `/admin/signal-orchestrator/status` | GET | Orchestrator 상태 조회 |
| `/admin/signal-orchestrator/concurrency` | GET | Concurrency Limiter 상태 |
| `/admin/signal-agents/list` | GET | 등록된 Agent 목록 |
| `/admin/health/signal-extraction` | GET | Signal Extraction 건강 상태 |
| `/admin/signal-orchestrator/reset` | POST | Orchestrator 리셋 |
| `/admin/circuit-breaker/status` | GET | Circuit Breaker 상태 |
| `/admin/search-providers/health` | GET | 검색 Provider 상태 |
| `/admin/llm-usage/summary` | GET | LLM 사용량 통계 |

---

## 9. 파일 구조

```
backend/app/worker/
├── llm/
│   ├── orchestrator.py           # Corp Profiling Orchestrator (4-Layer)
│   ├── circuit_breaker.py        # Circuit Breaker 패턴
│   ├── consensus_engine.py       # 다중 소스 Consensus
│   ├── search_providers.py       # Multi-Search Manager
│   ├── gemini_adapter.py         # Gemini Validation/Enrichment
│   ├── field_assignment.py       # 필드별 Provider 분담
│   ├── fact_checker.py           # Gemini Grounding Fact-Check
│   ├── usage_tracker.py          # LLM 사용량 추적
│   ├── service.py                # LLM Service (Fallback 체인)
│   └── prompts_enhanced.py       # 강화된 프롬프트
│
├── pipelines/
│   ├── signal_extraction.py      # Signal Extraction Pipeline
│   ├── signal_agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # Signal Agent Orchestrator (3-Agent)
│   │   ├── base.py               # BaseSignalAgent (추상 클래스)
│   │   ├── direct_agent.py       # DirectSignalAgent
│   │   ├── industry_agent.py     # IndustrySignalAgent
│   │   ├── environment_agent.py  # EnvironmentSignalAgent
│   │   └── rule_based_generator.py # Rule-based Fallback
│   │
│   ├── corp_profiling.py         # Corp Profiling Pipeline
│   ├── external_search.py        # External Search (3-Track)
│   └── ...
│
└── tasks/
    ├── analysis.py               # 9-Stage 메인 파이프라인
    └── profile_refresh.py        # Background Profile 갱신
```

---

## 10. 참고 문서

- [ADR-009: Multi-Agent Signal Extraction Architecture](./ADR-009-multi-agent-signal-extraction.md)
- [ADR-010: Multi-Search Provider](./ADR-010-multi-search-provider.md)
- [ADR-008: Security Architecture - LLM Separation](./ADR-008-security-architecture-llm-separation.md)
- [PRD-Corp-Profiling-Pipeline.md](../PRD/PRD-Corp-Profiling-Pipeline.md)
