# PRD: Corp Profiling Pipeline

**문서 버전**: v1.1
**작성일**: 2026-01-19
**최종 수정일**: 2026-01-19
**작성자**: PM (Claude 지원)
**검토자**: SE, CTO, CPO, TA
**상태**: Draft → CTO/Tech Lead 검토 완료 → PM 결정 대기

---

## 변경 이력

| 버전 | 일자 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| v1.0 | 2026-01-19 | 초안 작성 | PM |
| v1.1 | 2026-01-19 | CTO/Tech Lead 기술 검토 반영 | PM + CTO |

### v1.1 주요 변경 사항

| 섹션 | 변경 내용 | 우선순위 |
|------|----------|---------|
| 3.2 | Gemini 역할 재정의 (검색 → 검증/보완) | P0 |
| 3.3-3.4 | "절대 실패 방지" 범위 명확화 | P0 |
| 4.1.2 | 문자열 일치 조건 구체화 (Jaccard Similarity) | P1 |
| 4.2 | Consensus Metadata 필드 추가 | P2 |
| 9 | Circuit Breaker 상태 조회 API 추가 | P2 |
| 3.4 | 결과 매트릭스에 Cache 시나리오 추가 | P2 |
| 11 | 비용 추정 재계산 (실제 Claude 가격 반영) | P1 |
| 16 | PM 결정 필요 사항 (신규 섹션) | - |

---

## 1. 개요 (Executive Summary)

### 1.1 배경

rKYC 시스템의 ENVIRONMENT 시그널 생성을 위해서는 기업의 외부 비즈니스 정보(수출 비중, 공급망, 해외 사업 등)가 필요합니다. 현재 이 정보는 Mock 데이터로 하드코딩되어 있으며, 실제 LLM 기반 자동 수집 파이프라인이 필요합니다.

### 1.2 목표

1. **Multi-Agent 아키텍처**: Perplexity 검색 + Gemini 검증으로 정확도 향상
2. **Hallucination 방지**: Consensus Engine을 통한 교차 검증
3. **Fallback 체계**: 4-Layer Fallback으로 외부 LLM API 실패 시에도 최소한의 결과 반환
4. **Frontend 완성**: Gap 항목 모두 채워 Mock 데이터 의존 제거

### 1.3 범위

| 포함 | 제외 |
|------|------|
| Corp Profiling LLM 파이프라인 | 내부 데이터 (Snapshot) 처리 |
| Multi-Agent Consensus Engine | 실시간 주가/재무 API 연동 |
| Frontend Profile 표시 | 사용자 인증/권한 |
| Background 갱신 메커니즘 | 알림 시스템 (이메일/SMS) |

### 1.4 Fallback 범위 명확화 (v1.1 추가)

> **중요**: 본 PRD의 Fallback 체계는 **외부 LLM API 실패**에 대한 대응입니다.
>
> **커버 범위**:
> - Perplexity API 실패/타임아웃
> - Gemini API 실패/타임아웃
> - Claude API 실패/타임아웃
> - API Rate Limit 초과
>
> **커버 불가 (별도 대응 필요)**:
> - DB 연결 실패 → 인프라 모니터링 및 알림
> - Worker 프로세스 크래시 → Celery supervisor 재시작
> - 네트워크 단절 → 인프라 모니터링 및 알림
> - Redis 장애 → 인프라 모니터링 및 알림

---

## 2. 이해관계자 요구사항

### 2.1 PM (Product Manager)

| 요구사항 | 우선순위 |
|----------|---------|
| 기업 정보 자동 수집으로 운영 비용 절감 | P0 |
| Hallucination 없는 신뢰할 수 있는 정보 | P0 |
| Frontend Mock 데이터 제거 | P1 |

### 2.2 CTO (Chief Technology Officer)

| 요구사항 | 우선순위 |
|----------|---------|
| Circuit Breaker 패턴으로 장애 전파 방지 | P0 |
| 외부 LLM API 실패 시 Fallback 체계 | P0 |
| 비용 예측 가능한 Rate Limiting | P1 |

### 2.3 CPO (Chief Product Officer)

| 요구사항 | 우선순위 |
|----------|---------|
| 빠른 초기 로딩 (캐시 활용) | P0 |
| 기본 뷰 / 상세 뷰 분리 | P1 |
| Background 갱신으로 항상 최신 정보 | P1 |
| "정보 갱신" 수동 버튼 | P2 |

### 2.4 SE (Senior Engineer)

| 요구사항 | 우선순위 |
|----------|---------|
| Adapter 패턴으로 LLM 교체 용이성 | P1 |
| Structured Logging + Trace ID | P1 |
| 2-Tier Cache 전략 | P1 |

### 2.5 TA (Technical Architect)

| 요구사항 | 우선순위 |
|----------|---------|
| 확장 가능한 아키텍처 (새 LLM 추가 용이) | P1 |
| 비동기 처리 (Celery Task) | P1 |
| DB 스키마 확장성 (JSONB 활용) | P2 |

---

## 3. 시스템 아키텍처

### 3.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Corp Profiling Pipeline                               │
│                                                                             │
│  ┌─────────────┐                                                            │
│  │  Frontend   │ ◄────────────────────────────────────────────────────┐     │
│  │  (React)    │                                                      │     │
│  └──────┬──────┘                                                      │     │
│         │ GET /api/v1/corporations/{id}/profile                       │     │
│         ▼                                                             │     │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐     │     │
│  │  Backend    │────►│   Redis     │────►│  Cached Profile     │─────┘     │
│  │  (FastAPI)  │     │   Cache     │     │  (TTL: 7 days)      │           │
│  └──────┬──────┘     └─────────────┘     └─────────────────────┘           │
│         │ cache miss                                                        │
│         ▼                                                                   │
│  ┌─────────────┐                                                            │
│  │  Celery     │ ◄─── Background Task Queue                                 │
│  │  Worker     │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Corp Profiling Engine                             │   │
│  │                                                                      │   │
│  │  Layer 0: Cache Check                                                │   │
│  │      ↓                                                               │   │
│  │  Layer 1: Perplexity Search (Primary)                                │   │
│  │      ↓                                                               │   │
│  │  Layer 1.5: Gemini Validation & Enrichment                           │   │
│  │      ↓                                                               │   │
│  │  Layer 2: Claude Synthesis                                           │   │
│  │      ↓                                                               │   │
│  │  Layer 3: Rule-Based Merge (Fallback)                                │   │
│  │      ↓                                                               │   │
│  │  Layer 4: Graceful Degradation (Ultimate Fallback)                   │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────┐                                                            │
│  │  PostgreSQL │ ◄─── rkyc_corp_profile 테이블                              │
│  │  (Supabase) │                                                            │
│  └─────────────┘                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Multi-Agent 아키텍처 (v1.1 수정)

#### 3.2.1 기본 원칙

| 원칙 | 설명 |
|------|------|
| **Perplexity = Primary 검색** | 실시간 웹 검색 수행 |
| **Gemini = 검증/보완** | Perplexity 결과 검증 및 누락 필드 보완 |
| **Perplexity 우선** | 불일치 시 Perplexity 결과 채택 |
| **OpenAI 미사용** | Perplexity + Gemini + Claude만 사용 |

#### 3.2.2 LLM 역할 분담 (v1.1 수정)

| LLM | 역할 | 사용 단계 | 비고 |
|-----|------|----------|------|
| **Perplexity (sonar-pro)** | Primary 검색 | Layer 1 | 실시간 웹 검색 |
| **Gemini (gemini-3-pro)** | 검증 및 보완 | Layer 1.5 | ⚠️ 웹 검색 불가, 생성형 보완 |
| **Claude (claude-opus-4.5)** | 결과 종합 | Layer 2 | 최종 구조화 |

> **[v1.1 변경 사항]** Gemini는 실시간 웹 검색 기능이 없습니다.
>
> **Gemini 역할 변경**:
> - ~~검색자 (Layer 1 병렬 검색)~~
> - **검증자/보완자 (Layer 1.5)**
>   - Perplexity 검색 결과 신뢰도 평가
>   - 누락된 필드에 대해 생성형 보완 (출처: "Gemini 추정" 명시)

#### 3.2.3 Adapter 패턴

```python
# 추상 인터페이스
class LLMAdapter(ABC):
    @abstractmethod
    def search(self, query: str) -> dict:
        """검색 수행 (Perplexity만 실제 검색)"""
        pass

    @abstractmethod
    def validate(self, search_result: dict) -> dict:
        """결과 검증 (Gemini용)"""
        pass

    @abstractmethod
    def parse(self, response: dict) -> dict:
        """응답 파싱"""
        pass

    @abstractmethod
    def normalize(self, parsed: dict) -> UnifiedResponse:
        """통일된 스키마로 정규화"""
        pass

# 구현체
class PerplexityAdapter(LLMAdapter):
    """실시간 웹 검색 담당"""
    ...

class GeminiAdapter(LLMAdapter):
    """검증 및 생성형 보완 담당"""
    def search(self, query: str) -> dict:
        raise NotImplementedError("Gemini는 검색 불가")

    def validate(self, search_result: dict) -> dict:
        """Perplexity 결과 검증 및 보완"""
        ...
```

### 3.3 4-Layer Fallback 아키텍처 (v1.1 수정)

> **범위 명확화**: 본 Fallback 체계는 **외부 LLM API 실패**에 대한 대응입니다.
> 시스템 인프라 장애(DB, Worker)는 별도 모니터링 및 알림으로 대응합니다.

#### Layer 0: Cache Check
```
IF cached_profile exists AND age < 7 days:
    RETURN cached_profile immediately
    TRIGGER background_refresh async
```

#### Layer 1: Perplexity Search (Primary)
```
TRY:
    perplexity_result = PerplexityAdapter.search(query)
CATCH:
    circuit_breaker.record_failure("perplexity")
    → Layer 4 (Perplexity 없이는 검색 불가)
```

#### Layer 1.5: Gemini Validation & Enrichment (v1.1 신규)
```
IF perplexity_result exists:
    TRY:
        gemini_validation = GeminiAdapter.validate(perplexity_result)
        - 신뢰도 평가
        - 누락 필드 보완 (source: "GEMINI_INFERRED" 명시)
    CATCH:
        circuit_breaker.record_failure("gemini")
        → 그대로 Layer 2로 (Gemini 없이도 진행 가능)
```

#### Layer 2: Claude Synthesis
```
TRY:
    final = Claude.synthesize(perplexity_result, gemini_validation)
    confidence = "HIGH"
    RETURN final
CATCH:
    circuit_breaker.record_failure("claude")
    → Layer 3
```

#### Layer 3: Rule-Based Merge
```
LLM 없이 규칙 기반 처리:
- Perplexity 결과만 사용
- 기본 정규화 적용
confidence = "MED"
```

#### Layer 4: Graceful Degradation
```
모든 외부 LLM 실패 시:
1. DB 기존 Profile 반환 (있으면)
2. 없으면 최소 Profile 반환:
   {
     "status": "PARTIAL",
     "message": "외부 정보 수집 실패, 기본 정보만 표시",
     "corp_name": (DB),
     "industry_name": (DB)
   }
```

### 3.4 결과 보장 매트릭스 (v1.1 확장)

#### Cache 시나리오 (v1.1 추가)

| Cache 상태 | Perplexity | Gemini | Claude | 최종 결과 | Confidence |
|------------|------------|--------|--------|----------|------------|
| ✅ Fresh (<7일) | - | - | - | 캐시 반환 + Background 갱신 | **CACHED** |
| ✅ Stale (>7일) | - | - | - | 캐시 반환 + 즉시 갱신 시작 | **STALE** |

#### LLM 호출 시나리오

| Perplexity | Gemini | Claude | 최종 결과 | Confidence |
|------------|--------|--------|----------|------------|
| ✅ | ✅ | ✅ | Claude 종합 | **HIGH** |
| ✅ | ✅ | ❌ | Rule-Based (Perplexity + Gemini 보완) | MED |
| ✅ | ❌ | ✅ | Claude (Perplexity만) | MED |
| ✅ | ❌ | ❌ | Perplexity 직접 정규화 | LOW |
| ❌ | - | - | DB 기존 데이터 | STALE |
| ❌ | - | - (없음) | 최소 Profile | NONE |

> **[v1.1 변경]** Gemini가 검색자가 아닌 검증자이므로, Perplexity 실패 시 Gemini만으로는 진행 불가.

---

## 4. Consensus Engine 설계

### 4.1 불일치 처리 로직

#### 4.1.1 시나리오별 처리 (v1.1 수정)

| 시나리오 | Perplexity | Gemini 검증 | 처리 | Confidence |
|----------|------------|-------------|------|------------|
| A. 검색 성공 + 검증 일치 | ✅ 값 있음 | ✅ 일치 확인 | Perplexity 값 채택 | HIGH |
| B. 검색 성공 + 검증 불일치 | ✅ 값 있음 | ⚠️ 이견 있음 | Perplexity 값 + discrepancy 플래그 | MED |
| C. 검색 성공 + Gemini 보완 | ✅ 일부 null | ✅ 보완 제공 | Perplexity + Gemini 보완 (출처 표시) | MED |
| D. 검색 성공 + 검증 실패 | ✅ 값 있음 | ❌ 실패 | Perplexity 값만 채택 | MED |
| E. 검색 실패 | ❌ 실패 | - | Fallback 진행 | LOW/NONE |
| F. 둘 다 null | null | null | null 유지 (정보 없음 확인) | HIGH |

#### 4.1.2 "일치"의 정의 (v1.1 구체화)

| 필드 타입 | 일치 조건 | 구현 방법 |
|-----------|----------|----------|
| 숫자 (%) | 차이 ≤ 10% (예: 55% vs 60% = 일치) | `abs(a - b) / max(a, b) <= 0.1` |
| 숫자 (금액) | 차이 ≤ 20% | `abs(a - b) / max(a, b) <= 0.2` |
| 국가 코드 | 상위 3개국 중 2개 이상 동일 | `len(set(top3_a) & set(top3_b)) >= 2` |
| 리스트 | 50% 이상 항목 중복 | `len(intersection) / len(union) >= 0.5` |
| **문자열** | **Jaccard Similarity >= 0.7** | **아래 상세 참조** |

##### 문자열 일치 조건 상세 (v1.1 추가)

**정의**:
- 단어 토큰화: 공백 및 특수문자 기준 분리
- 불용어 제외: 조사, 접속사 등 (은, 는, 이, 가, 및, 등, 의, 을, 를)
- 비교 방식: Jaccard Similarity >= 0.7

**Jaccard Similarity 공식**:
```
Jaccard(A, B) = |A ∩ B| / |A ∪ B|
```

**예시**:
```
A: "반도체 소재 전문 제조업체"
B: "반도체 부품 제조 전문기업"

토큰화 (불용어 제외):
A_tokens = {"반도체", "소재", "전문", "제조업체"}
B_tokens = {"반도체", "부품", "제조", "전문기업"}

교집합: {"반도체"} = 1개
  ("전문" vs "전문기업"은 완전 일치가 아니므로 제외)
합집합: {"반도체", "소재", "전문", "제조업체", "부품", "제조", "전문기업"} = 7개

Jaccard: 1/7 = 0.14 → 불일치 판정 (< 0.7)
```

**구현 코드 예시**:
```python
import re

STOPWORDS = {"은", "는", "이", "가", "및", "등", "의", "을", "를", "로", "에", "에서"}

def tokenize(text: str) -> set:
    tokens = re.split(r'[\s,\.·]+', text)
    return {t for t in tokens if t and t not in STOPWORDS}

def jaccard_similarity(text_a: str, text_b: str) -> float:
    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b

    return len(intersection) / len(union)

def is_string_match(text_a: str, text_b: str, threshold: float = 0.7) -> bool:
    return jaccard_similarity(text_a, text_b) >= threshold
```

#### 4.1.3 필드별 비교 규칙

| 필드 | 타입 | 일치 조건 | 불일치 시 처리 |
|------|------|----------|---------------|
| export_ratio_pct | int | 차이 ≤ 10% | Perplexity 값, 범위로 표시 |
| revenue_krw | int | 차이 ≤ 20% | Perplexity 값 |
| country_exposure | dict | Top 3 중 2개 일치 | Perplexity 값 |
| key_customers | list | Jaccard >= 0.5 | 합집합 (Union) |
| key_materials | list | Jaccard >= 0.5 | 합집합 (Union) |
| competitors | list | Jaccard >= 0.5 | 합집합 (Union) |
| business_summary | str | Jaccard >= 0.7 | Perplexity 값 |

### 4.2 Consensus Metadata 저장 (v1.1 확장)

```json
{
  "perplexity_called": true,
  "gemini_called": true,
  "claude_called": true,
  "perplexity_success": true,
  "gemini_success": true,
  "claude_success": true,
  "fields_compared": 15,
  "fields_matched": 12,
  "fields_discrepancy": 3,
  "discrepancy_fields": ["export_ratio_pct", "key_customers", "competitors"],
  "overall_confidence": "MED",
  "fallback_used": null,
  "fallback_layer": null,
  "retry_count": 0,
  "error_messages": [],
  "timestamp": "2026-01-19T10:00:00Z",
  "processing_time_ms": 4520
}
```

#### v1.1 추가 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `fallback_layer` | string \| null | 사용된 Fallback Layer (예: "LAYER_3", "LAYER_4") |
| `retry_count` | int | 재시도 횟수 |
| `error_messages` | string[] | 발생한 에러 메시지 목록 |

---

## 5. Corp Profile 스키마

### 5.1 전체 스키마

```typescript
interface CorpProfile {
  // ===== 기본 정보 =====
  ceo_name: string | null;
  employee_count: number | null;
  founded_year: number | null;
  headquarters: string | null;

  // ===== 경영진 =====
  executives: Executive[];

  // ===== 사업 개요 =====
  business_summary: string | null;      // 200자 이내
  industry_overview: string | null;     // 산업 구조 설명, 300자 이내
  business_model: string | null;        // "B2B 70% / 수출 30%"

  // ===== 재무 =====
  revenue_krw: number | null;
  financial_history: FinancialSnapshot[];  // 3개년

  // ===== 수출/해외 =====
  export_ratio_pct: number | null;      // 0-100
  country_exposure: Record<string, number>;  // {"CN": 30, "US": 25}

  // ===== Value Chain =====
  key_customers: string[];
  key_materials: string[];
  competitors: Competitor[];
  macro_factors: MacroFactor[];

  // ===== 공급망 (신규) =====
  supply_chain: {
    key_suppliers: Supplier[];
    supplier_countries: Record<string, number>;
    single_source_risk: string[];
    material_import_ratio_pct: number | null;
  };

  // ===== 해외 사업 =====
  overseas_business: {
    subsidiaries: Subsidiary[];
    manufacturing_countries: string[];
  };
  overseas_operations: string[];  // 레거시 호환

  // ===== 주주 =====
  shareholders: Shareholder[];

  // ===== 메타데이터 =====
  consensus_metadata: ConsensusMetadata;
}
```

### 5.2 서브 타입 정의

```typescript
interface Executive {
  name: string;
  position: string;
  is_key_man: boolean;
}

interface FinancialSnapshot {
  year: number;
  revenue: string;
  operating_profit: string;
  net_profit: string;
  equity: string;
}

interface Competitor {
  name: string;
  market_share: string | null;
  revenue: string | null;
  note: string | null;
}

interface MacroFactor {
  category: string;        // 정책, 규제, 환경, 기술, 글로벌
  description: string;
  impact: "positive" | "negative" | "neutral";
}

interface Supplier {
  name: string;
  type: string;            // 원재료, 부품, 서비스
  share: string | null;    // 조달 비중
  location: string | null; // 국가/지역
  source: "PERPLEXITY" | "GEMINI_INFERRED";  // v1.1 추가
}

interface Subsidiary {
  name: string;
  country: string;
  type: string;            // 법인, 지사, 공장
}

interface Shareholder {
  name: string;
  ownership: string;       // "45%"
  type: string;            // 개인, 법인, 기관
}

interface ConsensusMetadata {
  perplexity_success: boolean;
  gemini_success: boolean;
  claude_success: boolean;
  overall_confidence: "HIGH" | "MED" | "LOW" | "NONE" | "STALE" | "CACHED";
  discrepancy_fields: string[];
  fallback_used: string | null;
  fallback_layer: string | null;     // v1.1 추가
  retry_count: number;               // v1.1 추가
  error_messages: string[];          // v1.1 추가
  last_updated: string;
  processing_time_ms: number;
}
```

### 5.3 DB 스키마 (PostgreSQL)

```sql
CREATE TABLE rkyc_corp_profile (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL REFERENCES corp(corp_id),

    -- 기본 정보
    ceo_name VARCHAR(100),
    employee_count INTEGER,
    founded_year INTEGER,
    headquarters VARCHAR(200),

    -- 사업 개요
    business_summary TEXT,
    industry_overview TEXT,
    business_model VARCHAR(200),

    -- 재무
    revenue_krw BIGINT,
    export_ratio_pct INTEGER CHECK (export_ratio_pct >= 0 AND export_ratio_pct <= 100),

    -- JSON 필드
    executives JSONB DEFAULT '[]',
    shareholders JSONB DEFAULT '[]',
    competitors JSONB DEFAULT '[]',
    macro_factors JSONB DEFAULT '[]',
    supply_chain JSONB DEFAULT '{}',
    overseas_business JSONB DEFAULT '{}',
    financial_history JSONB DEFAULT '[]',
    country_exposure JSONB DEFAULT '{}',
    key_customers JSONB DEFAULT '[]',
    key_materials JSONB DEFAULT '[]',
    overseas_operations JSONB DEFAULT '[]',

    -- Consensus 메타데이터
    consensus_metadata JSONB DEFAULT '{}',

    -- 타임스탬프
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_corp_profile UNIQUE (corp_id)
);

-- 인덱스
CREATE INDEX idx_corp_profile_corp_id ON rkyc_corp_profile(corp_id);
CREATE INDEX idx_corp_profile_updated ON rkyc_corp_profile(updated_at);
CREATE INDEX idx_corp_profile_confidence ON rkyc_corp_profile(
    (consensus_metadata->>'overall_confidence')
);
```

---

## 6. LLM 프롬프트 설계

### 6.1 검색 쿼리 프롬프트 (Perplexity)

```
다음 기업에 대한 비즈니스 정보를 검색하세요.

기업명: {corp_name}
업종: {industry_name}

검색할 정보:
1. 대표이사, 임직원 수, 설립연도, 본사 소재지
2. 주요 사업 내용 및 비즈니스 모델 (B2B/B2C/수출 비중)
3. 수출 비중 및 주요 수출 국가
4. 주요 고객사 및 매출 비중
5. 주요 공급업체 및 원자재 조달처
6. 경쟁사 및 시장 점유율
7. 해외 법인, 공장, 지사 현황
8. 주주 구성 및 지분율
9. 최근 3개년 재무 현황 (매출, 영업이익, 순이익)
10. 산업 동향 및 매크로 환경 요인

규칙:
- 확인된 사실만 포함하세요
- 추측하거나 가정하지 마세요
- 확인되지 않은 정보는 "정보 없음"으로 표시하세요
- 출처가 있으면 함께 제공하세요
```

### 6.2 검증/보완 프롬프트 (Gemini) - v1.1 신규

```
다음은 {corp_name}에 대한 검색 결과입니다.

## Perplexity 검색 결과
{perplexity_result}

## 요청 작업
1. 위 검색 결과의 신뢰도를 평가하세요 (각 필드별 HIGH/MED/LOW)
2. 누락된 필드가 있다면, 귀하의 지식으로 보완하세요
   - 단, 보완한 정보는 반드시 "source": "GEMINI_INFERRED"로 표시
   - 확실하지 않으면 null 유지
3. 검색 결과와 다른 정보를 알고 있다면 discrepancy로 표시하세요

## 출력 형식
{
  "validation": {
    "field_name": {"confidence": "HIGH/MED/LOW", "note": "..."}
  },
  "enrichment": {
    "field_name": {"value": "...", "source": "GEMINI_INFERRED"}
  },
  "discrepancies": [
    {"field": "...", "perplexity_value": "...", "gemini_value": "..."}
  ]
}
```

### 6.3 종합 프롬프트 (Claude)

```
다음 검색 및 검증 결과를 종합하여 {corp_name}의 비즈니스 프로파일을 JSON으로 작성하세요.

## Perplexity 검색 결과
{perplexity_result}

## Gemini 검증/보완 결과
{gemini_validation}

## 종합 규칙
1. Perplexity 검색 결과를 기본으로 사용하세요
2. Gemini가 보완한 필드는 source: "GEMINI_INFERRED"로 표시하세요
3. discrepancy가 있는 필드는 Perplexity 값 채택 + discrepancy: true 표시
4. 확인되지 않은 필드는 null로 반환하세요
5. 예시 데이터를 절대 사용하지 마세요

## 출력 스키마
{output_schema}

JSON만 출력하세요. 설명이나 주석을 포함하지 마세요.
```

### 6.4 프롬프트 금지 사항

| 금지 항목 | 이유 |
|----------|------|
| 예시 데이터 포함 | LLM이 예시를 실제로 출력할 위험 |
| industry_code 사용 | "C26" 대신 "전자부품 제조업" 사용 |
| 추측 허용 | "~일 것이다" 표현 금지 |
| 단정적 표현 | "반드시", "확실히" 금지 |

---

## 7. Frontend 통합

### 7.1 기본 뷰 vs 상세 뷰

#### 기본 뷰 (Default)
- 핵심 정보만 표시
- discrepancy, source 정보 숨김
- confidence 배지만 표시

#### 상세 뷰 (Toggle)
- 전체 정보 표시
- discrepancy 필드 하이라이트 (노란색 배경)
- source 표시 (PERPLEXITY / GEMINI_INFERRED 뱃지)
- confidence 상세 (필드별)
- Consensus metadata 패널

### 7.2 NULL 값 표시 규칙

| 데이터 상태 | Frontend 표시 |
|------------|--------------|
| null | "-" 또는 빈칸 |
| undefined | "-" 또는 빈칸 |
| 빈 문자열 "" | "-" 또는 빈칸 |
| 빈 배열 [] | 해당 섹션 숨김 |
| 빈 객체 {} | 해당 섹션 숨김 |

**금지**: "NULL", "null", "undefined", "N/A" 텍스트 직접 표시

### 7.3 로딩 상태 UX

```
Case A: 캐시 존재 (7일 이내)
┌─────────────────────────────────────┐
│  [즉시 표시] 기존 Profile           │
│                                     │
│  Background에서 갱신 중... (숨김)    │
│                                     │
│  [갱신 완료 시]                      │
│  → 변경 없음: 조용히 캐시 갱신       │
│  → 변경 있음: 토스트 "새 정보 있음"  │
└─────────────────────────────────────┘

Case B: 캐시 없음 또는 만료
┌─────────────────────────────────────┐
│  [■■□□□] 외부 정보 검색 중...       │
│  [■■■□□] 정보 분석 중...            │
│  [■■■■□] 검증 중...                 │
│  [■■■■■] 완료                       │
└─────────────────────────────────────┘
```

### 7.4 "정보 갱신" 버튼

```tsx
<Button
  onClick={handleRefresh}
  disabled={isRefreshing}
>
  {isRefreshing ? (
    <>
      <Loader2 className="animate-spin" />
      갱신 중...
    </>
  ) : (
    <>
      <RefreshCw />
      정보 갱신
    </>
  )}
</Button>
```

- 클릭 시 캐시 무효화 + 강제 재수집
- 완료 후 변경된 항목 하이라이트 (diff 표시)

### 7.5 공급망 현황 섹션 (신규)

```tsx
{/* 공급망 현황 */}
<section>
  <h2>공급망 현황</h2>

  {/* 주요 공급업체 */}
  <div>
    <h3>주요 공급업체</h3>
    <table>
      <thead>
        <tr>
          <th>업체명</th>
          <th>유형</th>
          <th>비중</th>
          <th>소재지</th>
          <th>출처</th>
        </tr>
      </thead>
      <tbody>
        {profile.supply_chain.key_suppliers.map(supplier => (
          <tr key={supplier.name}>
            <td>{supplier.name}</td>
            <td>{supplier.type}</td>
            <td>{supplier.share || "-"}</td>
            <td>{supplier.location || "-"}</td>
            <td>
              <Badge variant={supplier.source === "GEMINI_INFERRED" ? "outline" : "default"}>
                {supplier.source === "GEMINI_INFERRED" ? "추정" : "검색"}
              </Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>

  {/* ... 나머지 동일 ... */}
</section>
```

---

## 8. Background 갱신 메커니즘

### 8.1 자동 갱신 트리거

| 트리거 | 우선순위 | 실행 시점 |
|--------|---------|----------|
| 사용자 페이지 방문 | P1 | 즉시 (Background) |
| 새 시그널 감지 | P2 | 5분 내 |
| Profile 나이 > 7일 | P3 | 1시간 내 |
| 전체 기업 순환 | P4 | 야간 배치 |

### 8.2 Celery Beat 스케줄

```python
CELERY_BEAT_SCHEDULE = {
    # 만료 임박 Profile 갱신 (매시간)
    'refresh-expiring-profiles': {
        'task': 'app.worker.tasks.refresh_expiring_profiles',
        'schedule': crontab(minute=0),  # 매시 정각
    },
    # 전체 기업 순환 (야간)
    'refresh-all-profiles-nightly': {
        'task': 'app.worker.tasks.refresh_all_profiles',
        'schedule': crontab(hour=3, minute=0),  # 새벽 3시
    },
}
```

### 8.3 Rate Limiting

| 항목 | 제한 |
|------|------|
| 분당 최대 갱신 | 10개 기업 |
| 시간당 최대 갱신 | 100개 기업 |
| 일일 최대 갱신 | 500개 기업 |

---

## 9. Circuit Breaker 설정

### 9.1 설정 값

```python
CIRCUIT_BREAKER_CONFIG = {
    "perplexity": {
        "failure_threshold": 3,      # 연속 3회 실패 시 차단
        "cooldown_seconds": 300,     # 5분간 차단
        "half_open_requests": 1      # 테스트 요청 1회
    },
    "gemini": {
        "failure_threshold": 3,
        "cooldown_seconds": 300,
        "half_open_requests": 1
    },
    "claude": {
        "failure_threshold": 2,      # Claude는 더 보수적
        "cooldown_seconds": 600,     # 10분간 차단
        "half_open_requests": 1
    }
}
```

### 9.2 상태 전이

```
CLOSED (정상)
    │
    │ 연속 실패 >= threshold
    ▼
OPEN (차단)
    │
    │ cooldown 경과
    ▼
HALF_OPEN (테스트)
    │
    ├── 성공 → CLOSED
    └── 실패 → OPEN
```

### 9.3 상태 조회 API (v1.1 추가)

운영 모니터링을 위한 Circuit Breaker 상태 조회 API:

```
GET /api/v1/admin/circuit-breaker/status
```

**Response**:
```json
{
  "perplexity": {
    "state": "CLOSED",
    "failures": 0,
    "last_failure": null,
    "cooldown_remaining_sec": null
  },
  "gemini": {
    "state": "OPEN",
    "failures": 3,
    "last_failure": "2026-01-19T09:55:00Z",
    "cooldown_remaining_sec": 180
  },
  "claude": {
    "state": "HALF_OPEN",
    "failures": 2,
    "last_failure": "2026-01-19T09:50:00Z",
    "cooldown_remaining_sec": null
  }
}
```

---

## 10. Logging 및 Monitoring

### 10.1 Structured Logging

```json
{
  "trace_id": "prof-20260119-abc123",
  "corp_id": "8001-3719240",
  "corp_name": "엠케이전자",
  "stage": "SEARCH",
  "provider": "perplexity",
  "request": {
    "query": "엠케이전자 전자부품 제조업",
    "timestamp": "2026-01-19T10:00:00Z"
  },
  "response": {
    "status": "success",
    "latency_ms": 2340,
    "token_count": 1250,
    "result_count": 5
  },
  "error": null
}
```

### 10.2 메트릭

| 메트릭 | 설명 |
|--------|------|
| `corp_profile_latency_ms` | 전체 처리 시간 |
| `llm_call_success_rate` | LLM별 성공률 |
| `consensus_confidence_distribution` | Confidence 분포 |
| `cache_hit_rate` | 캐시 적중률 |
| `fallback_usage_count` | Fallback 사용 횟수 |
| `circuit_breaker_state` | Circuit Breaker 상태 (v1.1 추가) |

---

## 11. 비용 추정 (v1.1 재계산)

### 11.1 LLM 호출당 비용 (실제 가격 반영)

| LLM | Input 토큰 | Output 토큰 | 단가 (Input/Output) | 예상 비용/건 |
|-----|-----------|------------|---------------------|-------------|
| Perplexity (sonar-pro) | 1,000 | 2,000 | $5/$15 per 1M | **$0.035** |
| Gemini (gemini-3-pro) | 2,000 | 1,000 | $1.25/$5 per 1M | **$0.0075** |
| Claude (opus-4.5) | 5,000 | 2,000 | $15/$75 per 1M | **$0.225** |
| **합계 (Claude Opus)** | | | | **$0.27/기업** |

#### 비용 절감 옵션: Claude Sonnet 사용 시

| LLM | Input 토큰 | Output 토큰 | 단가 (Input/Output) | 예상 비용/건 |
|-----|-----------|------------|---------------------|-------------|
| Perplexity (sonar-pro) | 1,000 | 2,000 | $5/$15 per 1M | **$0.035** |
| Gemini (gemini-3-pro) | 2,000 | 1,000 | $1.25/$5 per 1M | **$0.0075** |
| Claude (sonnet-4) | 5,000 | 2,000 | $3/$15 per 1M | **$0.045** |
| **합계 (Claude Sonnet)** | | | | **$0.09/기업** |

### 11.2 월간 비용 추정 (v1.1 재계산)

#### Option A: Claude Opus 사용

| 시나리오 | 기업 수 | 갱신 주기 | 월 비용 |
|----------|---------|----------|--------|
| MVP | 100개 | 주 1회 | **$108** |
| Pilot | 500개 | 주 1회 | **$540** |
| Production | 1,000개 | 주 2회 | **$2,160** |

#### Option B: Claude Sonnet 사용 (비용 절감)

| 시나리오 | 기업 수 | 갱신 주기 | 월 비용 |
|----------|---------|----------|--------|
| MVP | 100개 | 주 1회 | **$36** |
| Pilot | 500개 | 주 1회 | **$180** |
| Production | 1,000개 | 주 2회 | **$720** |

### 11.3 v1.0 대비 변경 사항

| 항목 | v1.0 | v1.1 | 차이 |
|------|------|------|------|
| 기업당 비용 (Opus) | $0.06 | $0.27 | **+350%** |
| 기업당 비용 (Sonnet) | - | $0.09 | (신규 옵션) |
| MVP 월 비용 (Opus) | $24 | $108 | +$84 |
| Production 월 비용 (Opus) | $480 | $2,160 | +$1,680 |

---

## 12. 테스트 계획

### 12.1 단위 테스트

| 테스트 | 범위 |
|--------|------|
| Adapter 테스트 | 각 LLM Adapter의 search/validate/parse/normalize |
| Consensus 테스트 | 일치/불일치 시나리오별 처리 |
| Fallback 테스트 | 각 Layer의 정상 작동 |
| Jaccard 테스트 | 문자열 유사도 계산 정확도 |

### 12.2 통합 테스트

| 테스트 | 범위 |
|--------|------|
| E2E 파이프라인 | 전체 흐름 (검색 → 검증 → 종합 → 저장) |
| Cache 테스트 | 캐시 적중/미스 시나리오 |
| Circuit Breaker | 차단/해제 동작 |

### 12.3 부하 테스트

| 테스트 | 목표 |
|--------|------|
| 동시 요청 | 10개 기업 동시 처리 |
| Rate Limit | 분당 10개 제한 검증 |
| Timeout | 30초 타임아웃 검증 |

---

## 13. 마일스톤

| Phase | 기간 | 산출물 |
|-------|------|--------|
| **Phase 1: 설계** | 1주 | 이 PRD 문서 |
| **Phase 2: Backend** | 2주 | LLM Adapter, Consensus Engine, API |
| **Phase 3: Frontend** | 1주 | Profile 표시, 갱신 버튼, 공급망 섹션 |
| **Phase 4: 테스트** | 1주 | 단위/통합/부하 테스트 |
| **Phase 5: 배포** | 3일 | Production 배포 |

---

## 14. 리스크 및 대응

| 리스크 | 심각도 | 대응 방안 |
|--------|--------|----------|
| 외부 LLM API 장애 | HIGH | 4-Layer Fallback |
| 비용 폭발 | **HIGH** | Rate Limiting + Claude Sonnet 옵션 |
| Hallucination | MED | Consensus 교차 검증 |
| 응답 지연 | MED | 캐시 + Background 갱신 |
| 스키마 불일치 | LOW | 정규화 레이어 |
| Gemini 검색 불가 | MED | 검증/보완 역할로 전환 (v1.1) |

---

## 15. 부록

### 15.1 용어 정의

| 용어 | 정의 |
|------|------|
| Consensus | 두 LLM 결과를 비교하여 최종 값을 결정하는 과정 |
| Discrepancy | 두 LLM 결과가 불일치하는 상태 |
| Fallback | 주 경로 실패 시 대체 경로로 처리하는 것 |
| Circuit Breaker | 연속 실패 시 일시적으로 호출을 차단하는 패턴 |
| Jaccard Similarity | 두 집합의 유사도를 측정하는 방법 (교집합/합집합) |
| GEMINI_INFERRED | Gemini가 생성형으로 보완한 정보 (검색 결과 아님) |

### 15.2 참고 문서

- ADR-008: Security Architecture - LLM Separation
- CLAUDE.md: 프로젝트 메모리
- PRD v1.0 (원본): rKYC 시스템 요구사항

---

## 16. PM 결정 사항 (v1.2 확정)

CTO/Tech Lead 기술 검토 후 PM 결정이 확정되었습니다.

### Q1. Gemini 사용 방식 최종 결정

| Option | 설명 | 장점 | 단점 |
|--------|------|------|------|
| **✅ A. 검증자 역할** | Perplexity 결과 검증 + 생성형 보완 | 기존 아키텍처 유지, 교차 검증 가능 | Gemini 생성 정보 신뢰도 불명확 |
| B. Gemini 제외 | Perplexity + Claude 2-Agent | 단순화, 비용 절감 | 교차 검증 불가 |
| C. Gemini + Google Search API | 실제 검색 기능 추가 | 병렬 검색 가능 | 추가 비용 $0.01~0.02/건 |

→ **PM 결정**: ✅ **Option A - 검증자 역할** (Layer 1.5)

### Q2. 비용 증가 수용 여부

| 항목 | v1.0 예상 | v1.1 실제 (Opus) | v1.1 실제 (Sonnet) |
|------|----------|-----------------|-------------------|
| 기업당 비용 | $0.06 | $0.27 (+350%) | $0.09 (+50%) |
| MVP 월 비용 | $24 | $108 | $36 |
| Production 월 비용 | $480 | $2,160 | $720 |

→ **PM 결정**:
- [x] **Claude Opus 유지 (품질 우선)**
- [ ] Claude Sonnet 전환 (비용 절감)
- [ ] 하이브리드 (중요 기업만 Opus)

### Q3. 갱신 주기 정책

| Option | TTL | 갱신 방식 | 월 비용 (1,000개 기업 기준) |
|--------|-----|----------|---------------------------|
| **✅ A. 현재 (적극적)** | 7일 | Background 자동 | $2,160 (Opus) |
| B. 보수적 | 14일 | On-demand | $1,080 (Opus) |
| C. 최소 | 30일 | 수동만 | $500 (Opus) |

→ **PM 결정**: ✅ **Option A - 7일 TTL, Background 자동 갱신**

### 확정된 아키텍처 요약

```
┌─────────────────────────────────────────────────────────────┐
│                    Corp Profiling Pipeline                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 0: Redis Cache (7일 TTL)                             │
│      ↓ MISS                                                  │
│  Layer 1: Perplexity (Primary Search)                       │
│      ↓                                                       │
│  Layer 1.5: Gemini (Validation + Enrichment)                │
│      ↓                                                       │
│  Layer 2: Claude Opus (Synthesis + Consensus)               │
│      ↓ FAILURE                                               │
│  Layer 3: Rule-Based Fallback                               │
│      ↓ FAILURE                                               │
│  Layer 4: Graceful Degradation (Stale Cache)                │
└─────────────────────────────────────────────────────────────┘

비용: $0.27/기업, $2,160/월 (1,000기업 기준)
갱신: 7일 TTL, Background 자동 + 페이지 방문 시 트리거
```

---

**문서 끝**

*Last Updated: 2026-01-19 (v1.2 - PM 결정 확정)*
