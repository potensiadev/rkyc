# ADR-002: LLM Provider 선택 및 Fallback 전략

## 상태
Accepted

## 날짜
2025-01-XX

## 컨텍스트
rKYC 시스템은 기업 리스크 시그널 추출을 위해 LLM을 사용한다.
단일 LLM 제공자에 의존할 경우 장애 시 전체 시스템 중단 위험이 있으며,
각 제공자의 강점을 활용하여 분석 품질을 높일 필요가 있다.

### 요구사항
1. 고품질 한국어 분석 능력
2. 높은 가용성 (SLA 99.9% 이상)
3. 외부 정보 검색 기능
4. 비용 효율성
5. Fallback 메커니즘

## 결정
**Multi-Provider 전략을 채택하고, litellm을 통해 통합 인터페이스를 구현한다.**

### Primary Provider: Claude Opus 4.5
```python
model = "claude-opus-4-5-20251101"
```
- 역할: 시그널 추출, 인사이트 생성
- 선택 이유:
  - 한국어 분석 능력 우수
  - 긴 컨텍스트 지원 (200K tokens)
  - 구조화된 출력 (JSON mode) 안정적

### Fallback Chain
```
Claude Opus 4.5 → GPT-5.2 Pro → Gemini 3 Pro Preview
```

| 순서 | Provider | Model ID | 역할 |
|-----|----------|----------|------|
| 1 | Anthropic | claude-opus-4-5-20251101 | Primary |
| 2 | OpenAI | gpt-5.2-pro-2025-12-11 | 1st Fallback |
| 3 | Google | gemini/gemini-3-pro-preview | 2nd Fallback |

### External Search: Perplexity
```python
model = "perplexity/sonar-pro"
```
- 역할: 실시간 외부 정보 검색
- 파이프라인 위치: EXTERNAL 단계
- 특징: 웹 검색 + LLM 요약 통합

### Embedding: OpenAI
```python
model = "text-embedding-3-large"
```
- 역할: 인사이트 메모리 벡터화
- 차원: 2000 (pgvector 최대 지원)
- 용도: 유사 케이스 검색

## 결과

### 긍정적 결과
1. **고가용성**: Primary 장애 시 자동 Fallback
2. **최적화**: 각 작업에 최적의 모델 배정
3. **비용 효율**: 임베딩은 저비용 모델 사용
4. **추상화**: litellm으로 Provider 교체 용이

### 부정적 결과
1. **복잡성**: 4개 Provider 관리 필요
2. **비용 관리**: 다중 과금 체계 추적 필요
3. **일관성**: Provider 간 출력 품질 차이 가능

### Fallback 트리거 조건
```python
FALLBACK_TRIGGERS = [
    "rate_limit_exceeded",
    "api_connection_error",
    "timeout_error",
    "server_error_5xx",
    "content_policy_violation"
]
```

### 재시도 정책
```python
RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 1.0,  # seconds
    "exponential_base": 2,
    "max_delay": 60.0
}
```

## 대안 검토

### 대안 1: 단일 Provider (Claude Only)
- 장점: 구현 단순, 일관된 출력
- 단점: SPOF(Single Point of Failure)
- **기각 사유**: 가용성 요구사항 미충족

### 대안 2: 로드 밸런싱 (균등 분배)
- 장점: 부하 분산
- 단점: 품질 일관성 저하, 비용 예측 어려움
- **기각 사유**: Primary 품질 우선 정책과 충돌

### 대안 3: 자체 호스팅 LLM (Llama, Mistral)
- 장점: 비용 절감, 데이터 프라이버시
- 단점: 인프라 관리 부담, 품질 열세
- **기각 사유**: 초기 단계에서 운영 복잡성 과다

## 구현 예시

```python
from litellm import completion

async def call_llm_with_fallback(prompt: str, context: str) -> str:
    models = [
        "claude-opus-4-5-20251101",
        "gpt-5.2-pro-2025-12-11",
        "gemini/gemini-3-pro-preview"
    ]

    for model in models:
        try:
            response = await completion(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"{context}\n\n{prompt}"}
                ],
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            continue

    raise AllProvidersFailedError("All LLM providers exhausted")
```

## 비용 추정 (월간)

| Provider | 예상 호출 | 단가 | 월 비용 |
|----------|----------|------|---------|
| Claude Opus 4.5 | 10,000 | $15/1M input | ~$200 |
| GPT-5.2 Pro (Fallback) | 500 | $10/1M input | ~$10 |
| Perplexity | 5,000 | $5/1K req | ~$25 |
| Embedding | 20,000 | $0.13/1M | ~$3 |
| **Total** | | | **~$238** |

## 참조
- PRD LLM Integration Guide - Section 3.1 Provider 설정
- litellm 공식 문서: https://docs.litellm.ai/
