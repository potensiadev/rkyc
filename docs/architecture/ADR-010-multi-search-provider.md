# ADR-010: Multi-Search Provider Architecture (검색 내장 LLM 2-Track)

## Status
Accepted

## Date
2026-01-27

## Context

### Problem Statement
현재 Corp Profiling Pipeline은 Perplexity API에 100% 의존하고 있습니다:

| 파일 | Perplexity 언급 횟수 | 역할 |
|------|---------------------|------|
| orchestrator.py | 61회 | Layer 1 Primary Search |
| consensus_engine.py | 22회 | Source 우선순위 |
| corp_profiling.py | 17회 | 프로필 검색 |

**Single Point of Failure 위험**:
1. Perplexity API 장애 시 전체 Corp Profiling 파이프라인 중단
2. Rate Limit 도달 시 서비스 불가
3. Gemini는 "검증자" 역할만 수행 → **검색 기능도 활용 가능!**

### 사용 가능한 LLM 검색 기능

| LLM | 검색 기능 | 비고 |
|-----|----------|------|
| **Perplexity** | ✅ 실시간 검색 + AI 요약 | Primary |
| **Gemini** | ✅ Google Search Grounding | Fallback |
| OpenAI | ❌ API에서 검색 불가 | 분석/합성 전용 |
| Claude | ❌ API에서 검색 불가 | 분석/합성 전용 |

## Decision

**검색 내장 LLM 2-Track** 아키텍처를 도입합니다.
- 외부 검색 API(Tavily, Brave 등) 추가 없이 기존 LLM만 활용
- Perplexity 실패 시 Gemini Grounding으로 자동 fallback

### New Architecture
```
Search Request
      │
      ▼
┌─────────────────────────────────────────┐
│     MultiSearchManager (2-Track)        │
│  ┌─────────────────────────────────────┐│
│  │ 검색 내장 LLM만 사용:               ││
│  │ 1. Perplexity (Primary)            ││
│  │    - 실시간 검색 + AI 요약          ││
│  │    - citations 자동 포함            ││
│  │                                     ││
│  │ 2. Gemini Grounding (Fallback)     ││
│  │    - Google Search 기반             ││
│  │    - GOOGLE_API_KEY 활용            ││
│  └─────────────────────────────────────┘│
│                                         │
│  Circuit Breaker: Provider별 상태 관리   │
└─────────────────────────────────────────┘
      │
      ▼
   SearchResult → Claude/OpenAI로 분석/합성
```

### Search Providers (2개만)

| Provider | 역할 | 특징 |
|----------|------|------|
| **Perplexity** | Primary | 실시간 검색 + AI 요약, citations 자동 |
| **Gemini Grounding** | Fallback | Google Search 기반, GOOGLE_API_KEY 활용 |

### Implementation Details

#### 1. search_providers.py
```python
class MultiSearchManager:
    """검색 요청을 우선순위에 따라 여러 Provider에 시도"""

    async def search(self, query: str) -> SearchResult:
        for provider in self.get_available_providers():
            try:
                result = await provider.execute_with_circuit_breaker(query)
                return result
            except (CircuitOpenError, Exception):
                continue
        raise AllProvidersFailedError("All search providers failed")
```

#### 2. Orchestrator Integration
```python
def _safe_perplexity_search(self, corp_name, industry_name):
    # 1차: Perplexity 직접 시도
    try:
        result = self._perplexity_search_fn(corp_name, industry_name)
        if result and not result.get("error"):
            return result
    except Exception:
        pass

    # 2차: MultiSearchManager Fallback
    if self._use_multi_search and self._multi_search_manager:
        search_result = await self._multi_search_manager.search(query)
        return {
            "content": search_result.content,
            "citations": search_result.citations,
            "source": f"MULTI_SEARCH_{search_result.provider.value.upper()}",
        }
```

#### 3. Configuration
```python
# config.py (추가 API 키 불필요!)
SEARCH_PROVIDER_PRIORITY: str = Field(default="perplexity,gemini_grounding")
MULTI_SEARCH_PARALLEL_MODE: bool = Field(default=False)

# 필요한 API 키 (이미 사용 중):
# - PERPLEXITY_API_KEY
# - GOOGLE_API_KEY (Gemini Grounding용)
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/search-providers/status` | GET | Perplexity/Gemini 상태 조회 |
| `/admin/search-providers/health` | GET | 건강 상태 요약 |

### Risk Levels

| Level | Condition | Recommendation |
|-------|-----------|----------------|
| Critical | Perplexity + Gemini 모두 불가 | API 키 확인 필요 |
| Medium | Perplexity만 가용 | Gemini Grounding 자동 fallback 준비 |
| Low | 2개 Provider 모두 가용 | ✅ 정상 |

## Consequences

### Positive
1. **고가용성**: Perplexity 장애 시 Gemini로 자동 fallback
2. **추가 비용 없음**: 기존 API 키만 활용 (Perplexity + Google)
3. **단순함**: 2개 Provider만 관리
4. **모니터링**: `/admin/search-providers/health`로 상태 파악

### Negative
1. **검색 옵션 제한**: 2개 Provider만 사용 가능
2. **Gemini Grounding 품질**: Perplexity 대비 요약 품질 차이 가능

### Neutral
1. **응답 시간**: Fallback 시 약간의 지연 가능

## 사용 중인 LLM 정리

| LLM | 용도 | API 키 |
|-----|------|--------|
| **Perplexity** | 검색 (Primary) | PERPLEXITY_API_KEY |
| **Gemini** | 검색 Fallback + 검증 | GOOGLE_API_KEY |
| **Claude** | 분석/합성 (Primary) | ANTHROPIC_API_KEY |
| **OpenAI** | 분석/합성 Fallback | OPENAI_API_KEY |

## References
- [Perplexity API](https://docs.perplexity.ai/)
- [Gemini Grounding](https://ai.google.dev/gemini-api/docs/grounding)
