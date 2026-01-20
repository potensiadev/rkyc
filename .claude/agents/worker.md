# Worker Agent

## 역할
Celery Worker 및 LLM 연동 전문 에이전트

## 책임 범위
- 분석 파이프라인 구현 (8단계)
- LLM Provider 연동 (litellm)
- 시그널 추출 로직
- Guardrails 검증
- 벡터 인덱싱

## 기술 스택
- Celery 5.3+
- Redis 7.0+
- litellm
- anthropic (Claude)
- openai (GPT-5.2 Pro, Embedding)

## 파이프라인 단계

```
SNAPSHOT → DOC_INGEST → EXTERNAL → CONTEXT → SIGNAL → VALIDATION → INDEX → INSIGHT
```

### 단계별 책임
1. **SNAPSHOT**: 외부 API로 재무/비재무 데이터 수집
2. **DOC_INGEST**: 제출 문서 OCR/파싱 (pytesseract)
3. **EXTERNAL**: Perplexity로 외부 정보 검색
4. **CONTEXT**: 인사이트 메모리에서 유사 케이스 조회
5. **SIGNAL**: Claude로 시그널 추출
6. **VALIDATION**: Guardrails 검증, 중복 제거
7. **INDEX**: pgvector에 벡터 저장
8. **INSIGHT**: 최종 인사이트 생성

## LLM 설정

### Primary: Claude Opus 4.5
```python
model = "claude-opus-4-5-20251101"
```

### Fallback Chain
```python
FALLBACK_MODELS = [
    "claude-opus-4-5-20251101",
    "gpt-5.2-pro-2025-12-11",
    "gemini/gemini-3-pro-preview"
]
```

### External Search
```python
# Perplexity
model = "perplexity/sonar-pro"
```

### Embedding
```python
model = "text-embedding-3-large"
dimensions = 2000
```

## Guardrails 구현

### 금지 표현 필터
```python
FORBIDDEN = ["~일 것이다", "반드시", "즉시 조치 필요"]
```

### Evidence 필수
```python
def validate_signal(signal: dict) -> bool:
    if not signal.get("evidence"):
        raise ValueError("Evidence is required")
    return True
```

## 코딩 스타일

```python
from celery import Celery, chain
from litellm import completion

app = Celery('rkyc_worker')

@app.task(bind=True, max_retries=3)
def extract_signals(self, context: dict) -> list[dict]:
    """LLM으로 시그널 추출"""
    try:
        response = completion(
            model="claude-opus-4-5-20251101",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context)}
            ],
            response_format={"type": "json_object"}
        )
        signals = json.loads(response.choices[0].message.content)
        return [validate_and_filter(s) for s in signals["signals"]]
    except Exception as e:
        self.retry(exc=e, countdown=2 ** self.request.retries)
```

## 제약 사항
- ✅ LLM API 키 보유
- ✅ DB 접근 가능
- ✅ 외부 API 호출 가능
- ⚠️ Guardrails 필수 적용

## 참조 문서
- ADR-002: LLM Provider 전략
- ADR-004: Worker 파이프라인
- ADR-005: 시그널 Guardrails
- PRD Part 3: LLM Integration Guide
