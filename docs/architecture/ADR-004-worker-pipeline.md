# ADR-004: Worker 파이프라인 설계

## 상태
Accepted

## 날짜
2025-01-XX

## 컨텍스트
rKYC 시스템의 핵심 기능인 기업 리스크 분석은 다단계 처리가 필요하다.
각 단계는 외부 API 호출, LLM 처리, 데이터베이스 작업을 포함하며,
전체 파이프라인은 수 분에서 수십 분까지 소요될 수 있다.

### 요구사항
1. 장시간 작업의 비동기 처리
2. 단계별 진행 상태 추적
3. 실패 시 재시도 및 복구
4. 작업 우선순위 지원
5. 수평 확장 가능

## 결정
**Celery + Redis 기반 8단계 파이프라인을 구현한다.**

### 파이프라인 단계
```
SNAPSHOT → DOC_INGEST → EXTERNAL → CONTEXT → SIGNAL → VALIDATION → INDEX → INSIGHT
```

| 단계 | 설명 | LLM 사용 | 예상 시간 |
|-----|------|---------|----------|
| SNAPSHOT | 재무/비재무 데이터 수집 | ❌ | 5-10s |
| DOC_INGEST | 문서 OCR/파싱 | ❌ | 10-60s |
| EXTERNAL | 외부 정보 검색 (Perplexity) | ✅ | 5-15s |
| CONTEXT | 인사이트 메모리 조회 | ❌ | 1-3s |
| SIGNAL | 시그널 추출 (Claude) | ✅ | 10-30s |
| VALIDATION | 시그널 검증/중복 제거 | ✅ | 5-10s |
| INDEX | 벡터 인덱싱 | ❌ | 2-5s |
| INSIGHT | 최종 인사이트 생성 | ✅ | 10-20s |

**총 예상 시간: 48-153초**

## 결과

### 긍정적 결과
1. **가시성**: 각 단계별 진행 상태 UI 표시 가능
2. **재시도**: 실패한 단계만 선택적 재시도
3. **확장성**: Worker 인스턴스 추가로 처리량 증가
4. **디버깅**: 단계별 로그/결과 추적 용이

### 부정적 결과
1. **복잡성**: 8개 단계 각각 에러 핸들링 필요
2. **Redis 의존**: 메시지 브로커 장애 시 작업 중단
3. **상태 관리**: 단계 간 데이터 전달 로직 필요

### 작업 상태 정의
```python
class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### 파이프라인 단계 상세
```python
class PipelineStep(Enum):
    SNAPSHOT = "snapshot"       # 데이터 수집
    DOC_INGEST = "doc_ingest"  # 문서 처리
    EXTERNAL = "external"       # 외부 검색
    CONTEXT = "context"         # 컨텍스트 조회
    SIGNAL = "signal"           # 시그널 추출
    VALIDATION = "validation"   # 검증
    INDEX = "index"             # 인덱싱
    INSIGHT = "insight"         # 인사이트 생성
```

## Celery 구성

### Task 정의
```python
from celery import Celery, chain

app = Celery('rkyc_worker', broker='redis://localhost:6379/0')

@app.task(bind=True, max_retries=3)
def run_analysis_pipeline(self, job_id: str, corp_id: str):
    """메인 파이프라인 실행"""
    pipeline = chain(
        collect_snapshot.s(job_id, corp_id),
        ingest_documents.s(),
        search_external.s(),
        fetch_context.s(),
        extract_signals.s(),
        validate_signals.s(),
        index_vectors.s(),
        generate_insight.s()
    )
    return pipeline.apply_async()
```

### 재시도 정책
```python
@app.task(
    bind=True,
    autoretry_for=(LLMProviderError, DatabaseConnectionError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3
)
def extract_signals(self, context: dict):
    """시그널 추출 (자동 재시도)"""
    try:
        return llm_service.extract_signals(context)
    except ContentPolicyError:
        # 재시도 불가 에러는 즉시 실패
        raise Reject(reason="Content policy violation")
```

### 우선순위 큐
```python
app.conf.task_queues = [
    Queue('high', routing_key='high'),
    Queue('default', routing_key='default'),
    Queue('low', routing_key='low'),
]

# 긴급 분석 요청
trigger_analysis.apply_async(
    args=[job_id, corp_id],
    queue='high'
)
```

## 진행 상태 추적

### DB 업데이트
```python
async def update_job_progress(
    job_id: str,
    step: PipelineStep,
    status: JobStatus,
    metadata: dict = None
):
    await db.execute(
        """
        UPDATE analysis_jobs
        SET pipeline_step = $2,
            status = $3,
            metadata = COALESCE(metadata, '{}'::jsonb) || $4::jsonb,
            updated_at = NOW()
        WHERE id = $1
        """,
        job_id, step.value, status.value, json.dumps(metadata or {})
    )
```

### Realtime 알림 (Supabase)
```javascript
// Frontend에서 실시간 구독
supabase
  .channel('job_progress')
  .on('postgres_changes', {
    event: 'UPDATE',
    schema: 'public',
    table: 'analysis_jobs',
    filter: `id=eq.${jobId}`
  }, (payload) => {
    updateProgress(payload.new.pipeline_step);
  })
  .subscribe();
```

## 대안 검토

### 대안 1: 단일 트랜잭션 처리
- 장점: 구현 단순, 원자성 보장
- 단점: 타임아웃 위험, 진행 상태 불명
- **기각 사유**: 장시간 작업에 부적합

### 대안 2: AWS Step Functions
- 장점: 상태 머신 시각화, 내장 재시도
- 단점: AWS 종속, 비용, 한국 리전 지원 제한
- **기각 사유**: 벤더 종속 최소화 방침

### 대안 3: Temporal Workflow
- 장점: 강력한 워크플로우 엔진
- 단점: 학습 곡선, 인프라 복잡
- **기각 사유**: 초기 단계에 과도한 복잡성

### 대안 4: Background Tasks (FastAPI)
- 장점: 별도 인프라 불필요
- 단점: 스케일링 어려움, 재시작 시 작업 손실
- **기각 사유**: 프로덕션 수준 안정성 부족

## 모니터링

### Flower 대시보드
```bash
celery -A rkyc_worker flower --port=5555
```

### Prometheus 메트릭
```python
from prometheus_client import Counter, Histogram

pipeline_step_duration = Histogram(
    'pipeline_step_duration_seconds',
    'Time spent in each pipeline step',
    ['step']
)

pipeline_failures = Counter(
    'pipeline_failures_total',
    'Total pipeline failures',
    ['step', 'error_type']
)
```

## 참조
- PRD Full-Stack Spec v0.2 - Section 5.1 Worker 파이프라인
- Celery 공식 문서: https://docs.celeryq.dev/
