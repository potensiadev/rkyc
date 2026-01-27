# rKYC 기술 심층 설명서
## 발표자를 위한 기술 가이드

이 문서는 rKYC 시스템의 기술적 구현을 이해하기 쉽게 설명합니다.
해커톤 발표 시 기술 질문에 대응할 수 있도록 작성되었습니다.

---

## 목차
1. [시스템 전체 구조](#1-시스템-전체-구조)
2. [Multi-Agent Architecture](#2-multi-agent-architecture)
3. [9-Stage Pipeline](#3-9-stage-pipeline)
4. [4-Layer Fallback](#4-4-layer-fallback)
5. [Anti-Hallucination](#5-anti-hallucination)
6. [Consensus Engine](#6-consensus-engine)
7. [Circuit Breaker](#7-circuit-breaker)
8. [Vector Search](#8-vector-search)
9. [주요 기술 용어 설명](#9-주요-기술-용어-설명)
10. [예상 질문과 답변](#10-예상-질문과-답변)

---

## 1. 시스템 전체 구조

### 1.1 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                         사용자                                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (React)                            │
│                      - Vercel 호스팅                             │
│                      - API 호출만 수행                           │
│                      - LLM 직접 호출 ❌                          │
└─────────────────────────────┬───────────────────────────────────┘
                              │ REST API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                            │
│                     - Railway 호스팅                             │
│                     - DB 읽기/쓰기만 수행                        │
│                     - LLM 직접 호출 ❌                           │
│                     - Celery로 작업 큐에 전달                    │
└───────────┬─────────────────────────────────┬───────────────────┘
            │ PostgreSQL                      │ Redis (Queue)
            ▼                                 ▼
┌───────────────────────┐         ┌───────────────────────────────┐
│     Supabase DB       │         │      Worker (Celery)          │
│  - 기업 정보          │         │  - LLM API 호출 ✅            │
│  - 시그널 저장        │◄────────│  - 9단계 파이프라인 실행      │
│  - pgvector 확장      │         │  - 비동기 백그라운드 처리     │
└───────────────────────┘         └───────────┬───────────────────┘
                                              │
                              ┌───────────────┼───────────────────┐
                              │               │                   │
                              ▼               ▼                   ▼
                        ┌──────────┐   ┌──────────┐   ┌──────────────┐
                        │ Perplexity│   │  Gemini  │   │ Claude Opus  │
                        │ (검색)    │   │  (검증)   │   │ (합성/분석)  │
                        └──────────┘   └──────────┘   └──────────────┘
```

### 1.2 왜 이렇게 설계했나?

**Q: 왜 Frontend에서 직접 LLM을 호출하지 않나요?**

A: 세 가지 이유가 있습니다:
1. **보안**: API 키가 브라우저에 노출되면 악용될 수 있음
2. **비용 통제**: 서버에서만 호출해야 사용량 모니터링 가능
3. **금융 규제**: 민감 데이터가 LLM으로 전송되는 경로 통제 필요

**Q: 왜 Backend에서도 LLM을 호출하지 않나요?**

A: API 서버는 빠른 응답이 중요합니다. LLM 호출은 10-30초 걸리므로:
1. 사용자가 로딩 중 이탈할 수 있음
2. 서버 리소스가 오래 점유됨
3. 타임아웃 발생 가능

따라서 **Celery Worker**에서 비동기로 처리하고, 결과를 DB에 저장합니다.

---

## 2. Multi-Agent Architecture

### 2.1 멀티 에이전트란?

**일반적인 ChatGPT 사용**:
```
사용자 → ChatGPT → 답변
```

**rKYC의 멀티 에이전트**:
```
사용자 요청
    ↓
┌─────────────────────────────────────────────┐
│ Orchestrator (조율자)                        │
│ "이 작업을 누가 처리하면 좋을까?"            │
└─────────────────────────────────────────────┘
    │         │         │         │
    ▼         ▼         ▼         ▼
┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐
│검색자│  │검증자│  │합성자│  │임베딩생성│
│Perpl.│  │Gemini│  │Claude│  │ OpenAI   │
└──────┘  └──────┘  └──────┘  └──────────┘
    │         │         │         │
    └─────────┼─────────┼─────────┘
              ▼
    ┌─────────────────────┐
    │   최종 결과 합성    │
    └─────────────────────┘
```

### 2.2 각 에이전트의 역할

| 에이전트 | 모델 | 역할 | 왜 이 모델? |
|----------|------|------|-------------|
| **검색자** | Perplexity sonar-pro | 웹에서 실시간 정보 검색 | 다른 LLM은 학습 데이터만 사용, Perplexity는 실시간 검색 가능 |
| **검증자** | Gemini 3 Pro | Perplexity 결과 교차 검증 | 빠르고 저렴하면서 검증에 충분한 성능 |
| **합성자** | Claude Opus 4.5 | 여러 소스 정보를 하나로 합성 | 가장 높은 품질, 한국어 능력 우수 |
| **임베딩** | OpenAI text-embedding-3-large | 텍스트를 벡터로 변환 | 업계 표준, 2000차원 고품질 |

### 2.3 코드에서의 구현

```python
# backend/app/worker/llm/orchestrator.py

class MultiAgentOrchestrator:
    """
    여러 AI 에이전트를 조율하는 클래스

    실행 순서:
    1. Cache 확인 → 있으면 바로 반환
    2. Perplexity 검색 → 실패하면 다음 단계
    3. Gemini 검증 → 실패해도 계속 진행
    4. Claude 합성 → 실패하면 규칙 기반 병합
    5. 규칙 기반 병합 → 실패하면 최소 결과
    6. 최소 결과 → 절대 실패하지 않음
    """

    def execute(self, corp_name, industry_name, ...):
        # Layer 0: 캐시 확인
        cached = self._try_cache(corp_name)
        if cached:
            return cached  # 캐시 히트!

        # Layer 1+1.5: Perplexity + Gemini
        perplexity_result = self._try_perplexity_search(corp_name)
        gemini_validation = self._try_gemini_validate(perplexity_result)

        # Layer 2: Claude 합성
        if perplexity_result:
            synthesis = self._try_claude_synthesis(
                perplexity_result,
                gemini_validation
            )
            if synthesis:
                return synthesis

        # Layer 3: 규칙 기반 병합 (LLM 없이)
        rule_based = self._try_rule_based_merge(perplexity_result)
        if rule_based:
            return rule_based

        # Layer 4: 최소 결과 (절대 실패 안 함)
        return self._graceful_degradation(corp_name)
```

---

## 3. 9-Stage Pipeline

### 3.1 파이프라인이란?

공장의 조립 라인처럼, 데이터가 단계별로 처리됩니다:

```
원재료 → 가공 → 조립 → 검사 → 포장 → 출하
```

rKYC에서는:

```
기업ID → 데이터수집 → AI분석 → 검증 → 저장 → 알림
```

### 3.2 9단계 상세 설명

```
Stage 1: SNAPSHOT (5%)
├─ 무엇을: 기업의 내부 데이터 수집
├─ 어디서: 은행 내부 시스템 (여신, 담보, KYC 정보)
└─ 결과물: 구조화된 JSON

Stage 2: DOC_INGEST (20%)
├─ 무엇을: 제출 문서 분석 (사업자등록증, 재무제표 등)
├─ 방법: PDF 텍스트 추출 + 정규식 + LLM 보완
└─ 결과물: 추출된 팩트 목록

Stage 3: PROFILING (28%)  ⭐ 핵심!
├─ 무엇을: 외부에서 기업 정보 수집
├─ 방법: Perplexity 검색 → Gemini 검증 → Claude 합성
├─ 결과물: 19개 항목의 기업 프로필
└─ 특징: Anti-Hallucination 4-Layer 적용

Stage 4: EXTERNAL (35%)
├─ 무엇을: 최신 뉴스/공시 검색
├─ 방법: Perplexity로 실시간 웹 검색
└─ 결과물: 관련 외부 이벤트 목록

Stage 5: CONTEXT (45%)
├─ 무엇을: 모든 정보를 하나로 통합
├─ 입력: SNAPSHOT + DOC + PROFILE + EXTERNAL
└─ 결과물: 통합 컨텍스트 문서

Stage 6: SIGNAL (55%)  ⭐ 핵심!
├─ 무엇을: 리스크/기회 시그널 추출
├─ 방법: Claude Opus가 통합 컨텍스트 분석
└─ 결과물: 시그널 목록 (타입, 강도, 신뢰도)

Stage 7: VALIDATION (70%)
├─ 무엇을: 시그널 품질 검증
├─ 방법:
│   ├─ 중복 제거 (Deduplication)
│   ├─ 필수 필드 검증 (Evidence 있나?)
│   └─ 금지 표현 필터링 ("반드시", "즉시")
└─ 결과물: 검증된 시그널만 남김

Stage 8: INDEX (85%)
├─ 무엇을: DB에 저장 + 벡터 인덱싱
├─ 방법: PostgreSQL + pgvector
└─ 결과물: 저장된 시그널 ID 목록

Stage 9: INSIGHT (95%)
├─ 무엇을: 최종 브리핑 생성
├─ 방법: Claude가 시그널 요약 + 유사 과거 케이스 참조
└─ 결과물: 담당자용 한글 브리핑
```

### 3.3 코드에서의 구현

```python
# backend/app/worker/tasks/analysis.py

@celery_app.task
def run_analysis_pipeline(job_id, corp_id):
    """
    Celery 태스크로 실행되는 메인 파이프라인
    """

    # Stage 1: SNAPSHOT
    update_progress(job_id, 5, "SNAPSHOT")
    snapshot = snapshot_pipeline.execute(corp_id)

    # Stage 2: DOC_INGEST
    update_progress(job_id, 20, "DOC_INGEST")
    docs = doc_ingest_pipeline.execute(corp_id)

    # Stage 3: PROFILING (비동기 처리)
    update_progress(job_id, 28, "PROFILING")
    profile = profiling_pipeline.execute(corp_id, corp_name)

    # ... 중간 단계들 ...

    # Stage 9: INSIGHT
    update_progress(job_id, 95, "INSIGHT")
    insight = insight_pipeline.execute(signals, context)

    update_progress(job_id, 100, "DONE")
    return {"status": "success", "signals_created": len(signals)}
```

---

## 4. 4-Layer Fallback

### 4.1 왜 Fallback이 필요한가?

**현실 세계의 문제들**:
- Perplexity API가 다운되면?
- Claude가 Rate Limit에 걸리면?
- 네트워크 오류가 발생하면?

**일반적인 시스템**: 에러 발생 → 사용자에게 실패 메시지

**rKYC**: 에러 발생 → 다음 방법 시도 → 최악에도 뭔가 반환

### 4.2 4개 Layer 상세

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 0: CACHE                                                   │
├─────────────────────────────────────────────────────────────────┤
│ 설명: 최근 7일 내 수집한 프로필이 있으면 재사용                   │
│ 장점: 가장 빠름 (LLM 호출 없음), 비용 0원                        │
│ 단점: 오래된 정보일 수 있음                                      │
│ 코드: if cached and not expired: return cached                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (캐시 없음)
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1+1.5: PERPLEXITY + GEMINI                                │
├─────────────────────────────────────────────────────────────────┤
│ 설명: Perplexity가 검색 → Gemini가 검증/보완                     │
│ 장점: 가장 정확한 최신 정보                                      │
│ 단점: 두 API 모두 성공해야 함                                    │
│ 코드:                                                           │
│   result = perplexity.search(query)                             │
│   validated = gemini.validate(result)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (Perplexity 또는 Gemini 실패)
┌─────────────────────────────────────────────────────────────────┐
│ Layer 2: CLAUDE SYNTHESIS                                        │
├─────────────────────────────────────────────────────────────────┤
│ 설명: Claude가 부분적인 결과들을 합성                            │
│ 장점: 불완전한 데이터도 활용 가능                                │
│ 단점: Claude API가 작동해야 함                                   │
│ 코드:                                                           │
│   consensus = consensus_engine.merge(                           │
│       perplexity_result,  # 있으면                              │
│       gemini_result       # 있으면                              │
│   )                                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (Claude도 실패)
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: RULE-BASED MERGE                                        │
├─────────────────────────────────────────────────────────────────┤
│ 설명: LLM 없이 프로그래밍 규칙으로 병합                          │
│ 장점: LLM 의존 없음, 빠름                                        │
│ 단점: 품질은 낮을 수 있음                                        │
│ 규칙 예시:                                                      │
│   - Perplexity 값 우선                                          │
│   - 비율 합계 = 100% 검증                                       │
│   - 숫자 범위 검증 (0-100%)                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (아무것도 없을 때)
┌─────────────────────────────────────────────────────────────────┐
│ Layer 4: GRACEFUL DEGRADATION                                    │
├─────────────────────────────────────────────────────────────────┤
│ 설명: 최소한의 정보만 반환                                       │
│ 장점: 절대 실패하지 않음                                         │
│ 반환값:                                                         │
│   {                                                             │
│     "corp_name": "엠케이전자",                                   │
│     "industry_code": "C26",                                     │
│     "_degraded": true,  # 경고 플래그                            │
│     "_degradation_reason": "All layers failed"                  │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 비유로 설명

**여행 예약 시스템에 비유**:

```
Layer 0: 집에 있는 여권 (캐시)
         → 있으면 바로 사용

Layer 1: 대사관에서 새 여권 발급 (Perplexity + Gemini)
         → 가장 정확하지만 시간이 걸림

Layer 2: 임시 여행 서류 (Claude 합성)
         → 정식은 아니지만 사용 가능

Layer 3: 신분증만으로 여행 (규칙 기반)
         → 제한적이지만 가능

Layer 4: 여행 취소하고 국내 관광 (Graceful Degradation)
         → 최소한의 결과라도 제공
```

---

## 5. Anti-Hallucination

### 5.1 Hallucination이란?

**Hallucination (환각)**: AI가 사실이 아닌 정보를 마치 사실처럼 생성하는 현상

**예시**:
```
Q: "엠케이전자의 2024년 매출은?"
A: "엠케이전자의 2024년 매출은 1조 2천억원입니다."
   (실제로는 모르면서 그럴듯하게 지어냄)
```

### 5.2 왜 금융에서 특히 위험한가?

| 일반 챗봇 | 금융 리스크 분석 |
|-----------|------------------|
| 틀려도 불편함 정도 | 잘못된 대출 결정 |
| 재미로 사용 | 수십억 원 손실 가능 |
| 다시 물어보면 됨 | 규제 위반 가능 |

### 5.3 rKYC의 4-Layer Defense

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Source Verification (출처 검증)                         │
├─────────────────────────────────────────────────────────────────┤
│ 무엇을: Perplexity가 반환한 정보의 출처 URL 확인                 │
│                                                                 │
│ 도메인 신뢰도 분류:                                              │
│   ├─ HIGH: dart.fss.or.kr (공시), 회사 IR 페이지                │
│   ├─ MED: 경제 뉴스 (연합뉴스, 한경)                            │
│   └─ LOW: 블로그, 커뮤니티                                      │
│                                                                 │
│ 코드 예시:                                                      │
│   if source_url in TRUSTED_DOMAINS:                             │
│       confidence = "HIGH"                                       │
│   elif source_url in NEWS_DOMAINS:                              │
│       confidence = "MED"                                        │
│   else:                                                         │
│       confidence = "LOW"                                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Layer 2: Extraction Guardrails (추출 가드레일)                   │
├─────────────────────────────────────────────────────────────────┤
│ 무엇을: LLM에게 "모르면 null 반환" 규칙 적용                     │
│                                                                 │
│ 프롬프트 예시:                                                  │
│   "중요: 확실하지 않은 정보는 절대 추측하지 마세요.              │
│    해당 정보를 찾을 수 없으면 null을 반환하세요.                 │
│    '약', '추정', '아마도' 같은 표현도 금지입니다."               │
│                                                                 │
│ 효과:                                                           │
│   ├─ Before: "매출은 약 5000억원으로 추정됩니다"                │
│   └─ After: null (정확한 수치를 못 찾으면)                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: Validation Layer (검증 레이어)                          │
├─────────────────────────────────────────────────────────────────┤
│ 무엇을: Gemini가 Perplexity 결과 교차 검증                       │
│                                                                 │
│ 검증 항목:                                                      │
│   ├─ 범위 검증: export_ratio가 0-100% 사이인가?                 │
│   ├─ 일관성 검증: export + domestic = 100%인가?                 │
│   ├─ 논리 검증: 매출 < 영업이익? (비정상)                       │
│   └─ 교차 검증: 다른 소스와 일치하는가?                         │
│                                                                 │
│ 불일치 시:                                                      │
│   discrepancy: true 플래그 추가                                 │
│   → 사용자에게 "검증 필요" 표시                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Layer 4: Audit Trail (감사 추적)                                 │
├─────────────────────────────────────────────────────────────────┤
│ 무엇을: 모든 정보에 출처 기록 (Provenance)                       │
│                                                                 │
│ 저장 정보:                                                      │
│   {                                                             │
│     "revenue_krw": 1200000000000,                               │
│     "provenance": {                                             │
│       "source_url": "https://dart.fss.or.kr/...",               │
│       "excerpt": "2024년 연결매출액 1조 2천억원",               │
│       "confidence": "HIGH",                                     │
│       "fetched_at": "2024-01-15T10:30:00Z"                      │
│     }                                                           │
│   }                                                             │
│                                                                 │
│ 장점:                                                           │
│   ├─ 사후 검증 가능                                             │
│   ├─ 규제 감사 대응                                             │
│   └─ 사용자가 직접 출처 확인 가능                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Consensus Engine

### 6.1 왜 합의(Consensus)가 필요한가?

여러 AI가 다른 답을 줄 수 있습니다:

```
Perplexity: "엠케이전자 매출 1.2조원"
Gemini: "엠케이전자 매출 1.18조원"

→ 어느 것이 맞나요?
→ 10% 차이인가요, 2% 차이인가요?
→ 어떤 값을 사용할까요?
```

### 6.2 Consensus Engine의 역할

```
┌─────────────────────────────────────────────────────────────────┐
│                    Consensus Engine                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  입력                                                           │
│  ├─ Perplexity 결과: {"revenue": 1.2조, "export_ratio": 45%}   │
│  └─ Gemini 결과: {"revenue": 1.18조, "export_ratio": 42%}      │
│                                                                 │
│  비교 과정                                                      │
│  ├─ revenue: 1.2조 vs 1.18조 → 1.7% 차이 → ✓ 일치 (10% 이내)   │
│  └─ export_ratio: 45% vs 42% → 7% 차이 → ✓ 일치 (10% 이내)     │
│                                                                 │
│  합의 규칙                                                      │
│  ├─ 일치 시 (유사도 ≥ 70%): Perplexity 값 채택, HIGH 신뢰도   │
│  ├─ 불일치 시: Perplexity 값 채택 + discrepancy 플래그         │
│  └─ 한쪽만 있을 때: 있는 값 사용, MED/LOW 신뢰도               │
│                                                                 │
│  출력                                                           │
│  {                                                              │
│    "revenue": 1.2조,                                           │
│    "export_ratio": 45%,                                        │
│    "_consensus_metadata": {                                     │
│      "matched_fields": 2,                                       │
│      "discrepancy_fields": 0,                                   │
│      "overall_confidence": "HIGH"                               │
│    }                                                            │
│  }                                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 유사도 계산 방법

**Hybrid Similarity** (두 가지 방법 혼합):

```
1. Primary: Embedding 유사도 (의미적 유사성)
   ├─ "삼성전자" vs "Samsung Electronics" → 0.95 (같은 회사!)
   └─ OpenAI text-embedding-3-large 사용

2. Fallback: Jaccard 유사도 (단어 집합 비교)
   ├─ Embedding 사용 불가 시 적용
   ├─ 한국어 형태소 분석 (kiwipiepy) 사용
   └─ 조사 제거: "삼성전자의" → "삼성전자"
```

**Jaccard 유사도 예시**:
```
텍스트 A: "삼성전자 반도체 사업부"
텍스트 B: "삼성전자 반도체 부문"

토큰화:
A = {"삼성전자", "반도체", "사업부"}
B = {"삼성전자", "반도체", "부문"}

교집합: {"삼성전자", "반도체"} → 2개
합집합: {"삼성전자", "반도체", "사업부", "부문"} → 4개

Jaccard = 2/4 = 0.5 (50%)
→ 임계값 0.7 미만이므로 "불일치" 판정
```

---

## 7. Circuit Breaker

### 7.1 Circuit Breaker 패턴이란?

**전기 회로 차단기에서 유래**:
- 과전류 감지 → 회로 차단 → 화재 방지
- 정상화되면 → 회로 복구

**소프트웨어에서**:
- API 실패 반복 감지 → 호출 차단 → 시스템 보호
- 일정 시간 후 → 호출 재개 테스트

### 7.2 3가지 상태

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLOSED (정상)                               │
│  - 모든 요청 허용                                               │
│  - 실패 횟수 카운트                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ 실패 3회 연속
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       OPEN (차단)                                │
│  - 모든 요청 즉시 거부 (API 호출 안 함)                         │
│  - 5분 대기 (cooldown)                                          │
│  - 리소스 낭비 방지                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ 5분 경과
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HALF_OPEN (테스트)                            │
│  - 1개 요청만 허용                                               │
│  - 성공 → CLOSED로 복귀                                         │
│  - 실패 → OPEN으로 복귀                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 Provider별 설정

| Provider | 실패 임계값 | Cooldown | 이유 |
|----------|------------|----------|------|
| Perplexity | 3회 | 5분 | 검색은 자주 재시도 가능 |
| Gemini | 3회 | 5분 | 검증은 실패해도 진행 가능 |
| Claude | 2회 | 10분 | 합성 실패는 더 심각, 보수적 |

### 7.4 Redis 영속화

**문제**: Worker가 재시작되면 Circuit Breaker 상태가 초기화됨

**해결**: Redis에 상태 저장

```python
# 상태 저장
redis.setex(
    "rkyc:circuit_breaker:perplexity",
    ttl=600,  # 10분
    value=json.dumps({
        "state": "OPEN",
        "failure_count": 3,
        "opened_at": 1705123456.789
    })
)

# Worker 재시작 시
restored_state = redis.get("rkyc:circuit_breaker:perplexity")
if restored_state:
    self.state = CircuitState(restored_state["state"])
    # 중단된 곳에서 계속!
```

---

## 8. Vector Search

### 8.1 Vector(벡터)란?

**텍스트를 숫자 배열로 변환**:

```
"삼성전자 반도체" → [0.023, -0.145, 0.892, ..., 0.034]
                     ↑ 2000개의 숫자
```

**왜 변환하나요?**
- 컴퓨터는 숫자를 이해함
- 의미가 비슷한 텍스트 → 비슷한 벡터
- "빠른 유사도 검색" 가능

### 8.2 유사 케이스 검색

```
┌─────────────────────────────────────────────────────────────────┐
│  현재 시그널: "반도체 업종 수요 감소로 인한 매출 하락 위험"      │
│                          │                                      │
│                          ▼ Embedding                            │
│              [0.123, -0.456, 0.789, ...]                        │
│                          │                                      │
│                          ▼ pgvector 코사인 유사도 검색           │
│                                                                 │
│  유사한 과거 시그널:                                            │
│  1. "2022년 메모리 반도체 공급과잉 경고" (유사도 0.92)          │
│  2. "2020년 반도체 업황 하락기 진입" (유사도 0.87)              │
│  3. "2019년 DRAM 가격 하락 우려" (유사도 0.85)                  │
│                                                                 │
│  → 과거 사례 분석하여 더 나은 인사이트 제공                      │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 pgvector 설정

```sql
-- PostgreSQL에 벡터 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;

-- 벡터 컬럼 추가 (2000차원)
ALTER TABLE rkyc_signal_embedding
ADD COLUMN embedding vector(2000);

-- HNSW 인덱스 생성 (빠른 검색용)
CREATE INDEX idx_signal_embedding_hnsw
ON rkyc_signal_embedding
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**HNSW 인덱스란?**
- Hierarchical Navigable Small World
- 수백만 개 벡터에서 가장 유사한 것을 밀리초 단위로 검색
- 정확도와 속도 사이 최적 균형

---

## 9. 주요 기술 용어 설명

### 9.1 AI/ML 용어

| 용어 | 설명 | rKYC에서의 사용 |
|------|------|-----------------|
| **LLM** | Large Language Model, 대규모 언어 모델 | Claude, GPT, Gemini 등 |
| **Embedding** | 텍스트를 벡터(숫자 배열)로 변환 | 유사도 검색에 사용 |
| **Hallucination** | AI가 사실이 아닌 정보 생성 | Anti-Hallucination으로 방지 |
| **RAG** | Retrieval-Augmented Generation | 외부 검색 + LLM 생성 결합 |
| **Fine-tuning** | 사전 학습된 모델 추가 학습 | 향후 도메인 특화 예정 |

### 9.2 시스템 아키텍처 용어

| 용어 | 설명 | rKYC에서의 사용 |
|------|------|-----------------|
| **Pipeline** | 데이터 처리 단계의 연결 | 9-Stage Analysis Pipeline |
| **Orchestrator** | 여러 컴포넌트 조율 | Multi-Agent Orchestrator |
| **Circuit Breaker** | 장애 전파 방지 패턴 | LLM API 장애 처리 |
| **Fallback** | 실패 시 대안 처리 | 4-Layer Fallback |
| **Consensus** | 여러 소스 합의 도출 | Consensus Engine |

### 9.3 인프라 용어

| 용어 | 설명 | rKYC에서의 사용 |
|------|------|-----------------|
| **Celery** | Python 비동기 작업 큐 | Worker에서 LLM 작업 처리 |
| **Redis** | 인메모리 데이터 저장소 | 작업 큐, Circuit Breaker 상태 |
| **pgvector** | PostgreSQL 벡터 확장 | 유사도 검색 |
| **HNSW** | 고속 벡터 인덱스 알고리즘 | 밀리초 단위 검색 |

---

## 10. 예상 질문과 답변

### Q1: 왜 하나의 LLM 대신 여러 개를 사용하나요?

**답변**:
각 LLM이 다른 강점을 가지고 있기 때문입니다.

- **Perplexity**: 유일하게 실시간 웹 검색이 가능합니다. Claude나 GPT는 학습 데이터만 알고 있어서 2024년 최신 뉴스를 검색할 수 없습니다.

- **Gemini**: 빠르고 저렴해서 검증 역할에 적합합니다. 매번 Claude를 쓰면 비용이 10배 이상 들어갑니다.

- **Claude Opus**: 가장 높은 품질의 분석이 필요한 최종 합성 단계에서만 사용합니다.

이렇게 역할을 분담하면 비용은 낮추면서 품질은 높일 수 있습니다.

---

### Q2: Circuit Breaker가 정확히 어떤 상황에서 작동하나요?

**답변**:
예를 들어 Claude API가 연속으로 2번 실패하면:

1. Circuit Breaker가 OPEN 상태로 전환
2. 이후 10분간 Claude 호출을 시도하지 않음 (즉시 거부)
3. 대신 Fallback으로 GPT나 Gemini 사용
4. 10분 후 1개 요청으로 테스트
5. 성공하면 정상 복귀, 실패하면 다시 10분 대기

이렇게 하면:
- 실패하는 API에 계속 요청하는 낭비 방지
- 다른 API로 빠르게 전환하여 서비스 유지
- API가 복구되면 자동으로 정상화

---

### Q3: Hallucination을 어떻게 방지하나요?

**답변**:
4가지 방어 레이어가 있습니다:

1. **출처 검증**: Perplexity가 반환하는 모든 정보에 출처 URL이 있습니다. 공시(DART), 뉴스, 블로그를 신뢰도로 분류합니다.

2. **프롬프트 가드레일**: LLM에게 "모르면 null을 반환하라"고 명시적으로 지시합니다. "약", "추정" 같은 애매한 표현도 금지합니다.

3. **교차 검증**: Gemini가 Perplexity 결과를 검증합니다. 두 LLM의 답변이 다르면 discrepancy 플래그를 붙입니다.

4. **감사 추적**: 모든 데이터에 source_url, excerpt(원문 발췌), confidence를 기록합니다. 나중에 사람이 직접 확인할 수 있습니다.

---

### Q4: 9단계 파이프라인이 모두 실행되는 데 얼마나 걸리나요?

**답변**:
평균 30초~2분 정도 소요됩니다.

- SNAPSHOT, DOC_INGEST: 1-2초 (DB 조회)
- PROFILING: 10-30초 (Perplexity + Gemini + Claude)
- EXTERNAL: 5-10초 (Perplexity 검색)
- SIGNAL: 10-20초 (Claude 분석)
- VALIDATION, INDEX: 1-2초 (로컬 처리)
- INSIGHT: 5-10초 (Claude 생성)

단, Celery Worker에서 비동기로 실행되므로 사용자는 기다릴 필요가 없습니다. 작업을 요청하면 바로 Job ID를 받고, 완료되면 결과가 DB에 저장됩니다.

---

### Q5: 왜 pgvector를 선택했나요? Pinecone 같은 전용 벡터 DB는요?

**답변**:
세 가지 이유가 있습니다:

1. **단순성**: 이미 PostgreSQL(Supabase)을 사용하고 있어서 별도 서비스 추가 불필요

2. **비용**: Pinecone은 월 70달러~부터 시작, pgvector는 추가 비용 0원

3. **성능**: 수만 개 레벨에서는 pgvector HNSW로 충분합니다. 수백만 개가 되면 그때 전용 벡터 DB 검토

Supabase가 pgvector를 기본 지원해서 설정도 쉬웠습니다.

---

### Q6: Rate Limit이 걸리면 어떻게 되나요?

**답변**:
Celery의 자동 재시도(auto-retry) 기능을 사용합니다:

```python
@celery_app.task(
    autoretry_for=(RateLimitError,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    retry_backoff=True,  # 지수 백오프
)
def run_analysis_pipeline(...):
```

1. Rate Limit 에러 발생
2. 60초 대기 후 재시도
3. 또 실패하면 120초 대기 (지수 백오프)
4. 3번까지 재시도
5. 그래도 실패하면 Fallback 체인 (GPT → Gemini)

---

### Q7: 보안은 어떻게 처리하나요?

**답변**:
현재 MVP에서는 인증이 스코프 외지만, 아키텍처 설계 시 보안을 고려했습니다:

1. **LLM 키 격리**: API 키는 Worker에만 있고, Frontend/Backend에는 없습니다
2. **데이터 분류**: 향후 Internal LLM (민감 데이터) vs External LLM (공개 데이터) 분리 예정
3. **감사 로그**: 모든 LLM 호출 기록 보관 (rkyc_llm_audit_log 테이블)
4. **SSL/TLS**: 모든 통신 암호화 (Vercel, Railway, Supabase 기본 제공)

Phase 2에서 Azure OpenAI나 AWS Bedrock으로 전환하면 Private Cloud에서 LLM 실행이 가능합니다.

---

### Q8: 기존 KYC 시스템과 뭐가 다른가요?

**답변**:
기존 KYC 시스템은 **정적 체크리스트** 방식입니다:
- 주기적인 수동 검토 (분기/반기)
- 담당자가 직접 정보 수집
- 체크리스트 항목 확인 → 통과/불통과

rKYC는 **실시간 시그널 모니터링**입니다:
- 24/7 자동 모니터링
- "지금 이 기업에 무슨 일이 생겼는지" 알림
- 리스크뿐 아니라 **기회 시그널**도 포착
- 시그널 기반 KYC 갱신 트리거

---

### Q9: 정확도는 어떻게 되나요?

**답변**:
정확도 보장을 위해 4-Layer 검증 체계를 설계했습니다:

1. **Source Verification**: 출처 신뢰도 분류 (공시 > 뉴스 > 블로그)
2. **Extraction Guardrails**: "모르면 null 반환" 규칙
3. **Validation Layer**: Gemini 교차 검증, 범위/일관성 검증
4. **Audit Trail**: 모든 필드에 source_url, excerpt 기록

**솔직한 답변**: 실제 정확도 수치는 파일럿에서 측정이 필요합니다.
하지만 Hallucination 방지 설계가 되어 있어, **잘못된 정보보다는 정보 없음(null)** 을 반환합니다.

---

### Q10: 내부 시스템과 어떻게 연계되나요?

**답변**:
API 기반 연계 설계가 되어 있습니다:

```
[Input]
여신시스템 → Internal Snapshot API → rKYC
    └── 고객번호, 여신잔액, 담보정보, 내부등급

KYC시스템 → Document API → rKYC
    └── 사업자등록증, 등기부, 재무제표

[Output]
rKYC Signal → 기업심사 워크플로우
    └── "이 기업 외부 리스크 시그널 3건 감지"
```

기존 인프라 활용 설계가 되어 있어, 연동 작업이 최소화됩니다.

---

### Q8: 한국어 처리는 어떻게 하나요?

**답변**:
kiwipiepy 형태소 분석기를 사용합니다:

```python
from kiwipiepy import Kiwi
kiwi = Kiwi()

# 입력: "삼성전자의 반도체를"
# 분석 결과:
# [("삼성전자", "NNP"),  # 고유명사
#  ("의", "JKG"),        # 관형격 조사 → 제거
#  ("반도체", "NNG"),    # 일반명사
#  ("를", "JKO")]        # 목적격 조사 → 제거

# 결과: {"삼성전자", "반도체"}
```

조사(의, 를, 은, 는)를 제거해야 Jaccard 유사도가 정확해집니다.

---

이 문서가 발표 준비에 도움이 되길 바랍니다. 추가 질문이 있으시면 말씀해 주세요.
