# ADR-009: Multi-Agent Signal Extraction Architecture

## Status
**Accepted** - 2026-01-26

## Context

현재 rKYC 시스템의 기업 분석 파이프라인은 9단계 순차 실행 구조로, 평균 120초/기업이 소요됩니다.
주요 병목 지점:
- PROFILING: Perplexity→Gemini→Claude 순차 호출 (40초)
- SIGNAL: 단일 LLM이 15-30개 시그널 추출 (30초)
- EXTERNAL: 3-Track 검색 순차 실행 (20초)

속도 개선과 signal_type별 정확도 향상을 위해 Multi-Agent 아키텍처 도입이 필요합니다.

## Decision

### 1. 하이브리드 병렬화 전략
- **I/O 바운드 작업** (API 호출): `asyncio.gather()` 사용
- **독립 실행 단위** (Signal Agent): `Celery group()` 사용

### 2. Signal Extraction 3-Agent 분할
| Agent | signal_type | event_types | 데이터 소스 |
|-------|-------------|-------------|-------------|
| DirectSignalAgent | DIRECT | 8종 (KYC_REFRESH 등) | Internal Snapshot |
| IndustrySignalAgent | INDUSTRY | INDUSTRY_SHOCK | Industry Master + External |
| EnvironmentSignalAgent | ENVIRONMENT | POLICY_REGULATION_CHANGE | Corp Profile + Policy |

### 3. Circuit Breaker 공유 전략
- Provider별 분리 (Perplexity/Gemini/Claude 각각 관리)
- 병렬 Agent 동시 호출 시 Concurrency Limit 적용
  - Perplexity: 5 concurrent
  - Gemini: 10 concurrent
  - Claude: 3 concurrent

### 4. Fallback 전략: Graceful Degradation
- 개별 Agent 실패 시 전체 실패가 아닌 부분 결과 반환
- DIRECT Agent 실패 시에만 Rule-based 대체 적용
- `partial_failure` 플래그로 불완전 결과 표시

## Implementation Phases

### Phase 1 (Sprint 1): Quick Wins ✅ 완료
- Profiling Perplexity+Gemini 병렬화 (asyncio)
- External Search 3-Track 병렬화 (asyncio)
- LLM Usage 모니터링

### Phase 2 (Sprint 2): Signal Multi-Agent ✅ 완료
- DirectSignalAgent 구현 ✅
- IndustrySignalAgent 구현 ✅
- EnvironmentSignalAgent 구현 ✅
- SignalAgentOrchestrator (ThreadPoolExecutor 기반) ✅
- Celery group() 태스크 정의 ✅

### Phase 3 (Sprint 3): Quality & Reliability ✅ 완료
- Cross-Validation 강화 ✅
  - 충돌 감지 (signal_type/impact_direction 불일치)
  - needs_review 플래그 자동 설정
  - 콘텐츠 기반 유사 시그널 그룹화
- Graceful Degradation 구현 ✅
  - 개별 Agent 실패 시 partial_failure 플래그
  - DIRECT Agent 실패 시 Rule-based Fallback
  - 연체/등급 변경 자동 감지 (내부 스냅샷 기반)
- Provider Concurrency Limit ✅
  - Semaphore 기반 동시 접속 제한
  - Claude: 3, OpenAI: 5, Gemini: 10, Perplexity: 5

### Phase 4 (Sprint 4): Distributed Execution & Monitoring ✅ 완료
- Celery group() 분산 실행 ✅
  - signal.direct_agent, signal.industry_agent, signal.environment_agent 태스크
  - execute_distributed() 함수로 multi-worker 환경 지원
  - 개별 Agent 재시도 (max_retries=2)
- Admin 모니터링 API 확장 ✅
  - GET /admin/signal-orchestrator/status
  - GET /admin/signal-orchestrator/concurrency
  - GET /admin/signal-agents/list
  - GET /admin/health/signal-extraction
  - POST /admin/signal-orchestrator/reset

## Consequences

### Positive
- 파이프라인 속도 58% 개선 (120초 → 50초)
- signal_type별 전문화된 프롬프트로 정확도 향상
- 개별 Agent 실패 시에도 부분 결과 제공

### Negative
- 아키텍처 복잡도 증가
- LLM 비용 3.5% 증가 ($0.28 → $0.29/기업)
- Agent 간 결과 충돌 가능성 (Cross-Validation으로 해결)

### Risks
- Rate Limit 초과: Concurrency Limit + 백오프로 대응
- Agent 간 충돌: Cross-Validation + 수동 리뷰 플래그
- Celery Worker 과부하: Auto-scaling + Queue 모니터링

## References
- PRD-Corp-Profiling-Pipeline.md
- ADR-008-security-architecture-llm-separation.md
- orchestrator.py (4-Layer Fallback)
