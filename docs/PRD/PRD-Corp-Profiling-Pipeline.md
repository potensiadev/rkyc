# PRD: Corp Profiling Pipeline

**문서 버전**: v1.0
**작성일**: 2026-01-19
**작성자**: PM (Claude 지원)
**검토자**: SE, CTO, CPO, TA
**상태**: Draft → Review 대기

---

## 1. 개요 (Executive Summary)

### 1.1 배경

rKYC 시스템의 ENVIRONMENT 시그널 생성을 위해서는 기업의 외부 비즈니스 정보(수출 비중, 공급망, 해외 사업 등)가 필요합니다. 현재 이 정보는 Mock 데이터로 하드코딩되어 있으며, 실제 LLM 기반 자동 수집 파이프라인이 필요합니다.

### 1.2 목표

1. **Multi-Agent 아키텍처**: Perplexity + Gemini 병렬 검색으로 정확도 향상
2. **Hallucination 방지**: Consensus Engine을 통한 교차 검증
3. **절대 실패 방지**: 4-Layer Fallback으로 어떤 상황에서도 결과 반환
4. **Frontend 완성**: Gap 항목 모두 채워 Mock 데이터 의존 제거

### 1.3 범위

| 포함 | 제외 |
|------|------|
| Corp Profiling LLM 파이프라인 | 내부 데이터 (Snapshot) 처리 |
| Multi-Agent Consensus Engine | 실시간 주가/재무 API 연동 |
| Frontend Profile 표시 | 사용자 인증/권한 |
| Background 갱신 메커니즘 | 알림 시스템 (이메일/SMS) |

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
| 절대 실패하지 않는 Fallback 체계 | P0 |
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
│  │  Layer 1: Parallel Search (Perplexity + Gemini)                      │   │
│  │      ↓                                                               │   │
│  │  Layer 2: Claude Synthesis (Primary)                                 │   │
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

### 3.2 Multi-Agent 아키텍처

#### 3.2.1 기본 원칙

| 원칙 | 설명 |
|------|------|
| **필수 병렬 호출** | Perplexity, Gemini 둘 다 반드시 호출 |
| **Perplexity 우선** | 불일치 시 Perplexity 결과 채택 |
| **Gemini = 검증자** | 교차 검증 및 confidence 조정 역할 |
| **OpenAI 미사용** | Perplexity + Gemini + Claude만 사용 |

#### 3.2.2 LLM 역할 분담

| LLM | 역할 | 사용 단계 |
|-----|------|----------|
| **Perplexity (sonar-pro)** | Primary 검색 | Layer 1 |
| **Gemini (gemini-3-pro)** | 검증 검색 | Layer 1 |
| **Claude (claude-opus-4.5)** | 결과 종합 | Layer 2 |

#### 3.2.3 Adapter 패턴

```python
# 추상 인터페이스
class LLMAdapter(ABC):
    @abstractmethod
    def search(self, query: str) -> dict:
        """검색 수행"""
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
class PerplexityAdapter(LLMAdapter): ...
class GeminiAdapter(LLMAdapter): ...
```

### 3.3 4-Layer Fallback 아키텍처

#### Layer 0: Cache Check
```
IF cached_profile exists AND age < 7 days:
    RETURN cached_profile immediately
    TRIGGER background_refresh async
```

#### Layer 1: Parallel Search
```
PARALLEL:
    perplexity_result = PerplexityAdapter.search(query)
    gemini_result = GeminiAdapter.search(query)

RESULTS:
    A. 둘 다 성공 → Layer 2
    B. 하나만 성공 → Layer 3
    C. 둘 다 실패 → Layer 4
```

#### Layer 2: Claude Synthesis
```
TRY:
    final = Claude.synthesize(perplexity_result, gemini_result)
    confidence = "HIGH"
    RETURN final
CATCH:
    circuit_breaker.record_failure("claude")
    → Layer 3
```

#### Layer 3: Rule-Based Merge
```
LLM 없이 규칙 기반 병합:
- 숫자: Perplexity 우선, 범위 표시
- 리스트: 합집합 + 출처 태그
- 문자열: Perplexity 우선
confidence = "MED"
```

#### Layer 4: Graceful Degradation
```
모든 외부 LLM 실패 시:
1. DB 기존 Profile 반환 (있으면)
2. 없으면 최소 Profile 반환:
   {
     "status": "PARTIAL",
     "message": "외부 정보 수집 실패",
     "corp_name": (DB),
     "industry_name": (DB)
   }
```

### 3.4 결과 보장 매트릭스

| Perplexity | Gemini | Claude | 최종 결과 | Confidence |
|------------|--------|--------|----------|------------|
| ✅ | ✅ | ✅ | Claude 종합 | HIGH |
| ✅ | ✅ | ❌ | Rule-Based 병합 | MED |
| ✅ | ❌ | ✅ | Claude 단일 정제 | MED |
| ✅ | ❌ | ❌ | Perplexity 직접 | LOW |
| ❌ | ✅ | ✅ | Claude 단일 정제 | LOW |
| ❌ | ✅ | ❌ | Gemini 직접 | LOW |
| ❌ | ❌ | - | DB 기존 데이터 | STALE |
| ❌ | ❌ | - | 최소 Profile | NONE |

**핵심**: 어떤 상황에서도 사용자에게 결과를 반환한다. 전체 실패 없음.

---

## 4. Consensus Engine 설계

### 4.1 불일치 처리 로직

#### 4.1.1 시나리오별 처리

| 시나리오 | Perplexity | Gemini | 처리 | Confidence |
|----------|------------|--------|------|------------|
| A. 둘 다 성공 + 일치 | ✅ 값 있음 | ✅ 동일 값 | Perplexity 값 채택 | HIGH |
| B. 둘 다 성공 + 불일치 | ✅ 값 있음 | ✅ 다른 값 | Perplexity 값 + discrepancy 플래그 | MED |
| C. Perplexity만 성공 | ✅ 값 있음 | ❌ 실패/null | Perplexity 값 채택 | MED |
| D. Gemini만 성공 | ❌ 실패/null | ✅ 값 있음 | Gemini 값 채택 | LOW |
| E. 둘 다 실패 | ❌ 실패 | ❌ 실패 | null 반환 | NONE |
| F. 둘 다 null | null | null | null 유지 (정보 없음 확인) | HIGH |

#### 4.1.2 "일치"의 정의

| 필드 타입 | 일치 조건 |
|-----------|----------|
| 숫자 (%) | 차이 ≤ 10% (예: 55% vs 60% = 일치) |
| 숫자 (금액) | 차이 ≤ 20% |
| 국가 코드 | 상위 3개국 중 2개 이상 동일 |
| 리스트 | 50% 이상 항목 중복 |
| 문자열 | 핵심 키워드 70% 이상 일치 |

#### 4.1.3 필드별 비교 규칙

| 필드 | 타입 | 일치 조건 | 불일치 시 처리 |
|------|------|----------|---------------|
| export_ratio_pct | int | 차이 ≤ 10% | Perplexity 값, 범위로 표시 |
| revenue_krw | int | 차이 ≤ 20% | Perplexity 값 |
| country_exposure | dict | Top 3 중 2개 일치 | Perplexity 값 |
| key_customers | list | 50% 항목 일치 | 합집합 (Union) |
| key_materials | list | 50% 항목 일치 | 합집합 (Union) |
| competitors | list | 50% 항목 일치 | 합집합 (Union) |
| business_summary | str | 키워드 70% 일치 | Perplexity 값 |

### 4.2 Consensus Metadata 저장

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
  "timestamp": "2026-01-19T10:00:00Z",
  "processing_time_ms": 4520
}
```

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
  overall_confidence: "HIGH" | "MED" | "LOW" | "NONE" | "STALE";
  discrepancy_fields: string[];
  fallback_used: string | null;
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

### 6.1 검색 쿼리 프롬프트 (Perplexity/Gemini)

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

### 6.2 종합 프롬프트 (Claude)

```
두 검색 엔진의 결과를 종합하여 {corp_name}의 비즈니스 프로파일을 JSON으로 작성하세요.

## Perplexity 검색 결과
{perplexity_result}

## Gemini 검색 결과
{gemini_result}

## 종합 규칙
1. 두 결과에서 언급된 모든 정보를 포함하세요
2. 동일 필드에 다른 값이 있으면:
   - 숫자: Perplexity 값 채택, Gemini 값은 참고로 기록
   - 리스트: 합집합 (중복 제거)
3. 한쪽에만 있는 정보도 포함하세요
4. 각 필드마다 source를 표시하세요: "PERPLEXITY", "GEMINI", "BOTH"
5. 상충되는 정보는 discrepancy: true로 표시하세요
6. 확인되지 않은 필드는 null로 반환하세요
7. 예시 데이터를 절대 사용하지 마세요

## 출력 스키마
{output_schema}

JSON만 출력하세요. 설명이나 주석을 포함하지 마세요.
```

### 6.3 프롬프트 금지 사항

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
- source 표시 (PERPLEXITY / GEMINI / BOTH 뱃지)
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
        </tr>
      </thead>
      <tbody>
        {profile.supply_chain.key_suppliers.map(supplier => (
          <tr key={supplier.name}>
            <td>{supplier.name}</td>
            <td>{supplier.type}</td>
            <td>{supplier.share || "-"}</td>
            <td>{supplier.location || "-"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>

  {/* 조달처 국가 비중 */}
  <div>
    <h3>조달처 국가 비중</h3>
    {/* 국가별 비중 차트 또는 리스트 */}
  </div>

  {/* 단일 소스 리스크 */}
  {profile.supply_chain.single_source_risk.length > 0 && (
    <div className="bg-yellow-50 p-3 rounded">
      <h3>단일 소스 리스크 품목</h3>
      <ul>
        {profile.supply_chain.single_source_risk.map(item => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  )}

  {/* 원자재 수입 비중 */}
  {profile.supply_chain.material_import_ratio_pct && (
    <div>
      원자재 수입 비중: {profile.supply_chain.material_import_ratio_pct}%
    </div>
  )}
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

---

## 11. 비용 추정

### 11.1 LLM 호출당 비용

| LLM | 역할 | 예상 비용/건 |
|-----|------|-------------|
| Perplexity (sonar-pro) | 검색 | $0.02 |
| Gemini (gemini-3-pro) | 검색 | $0.01 |
| Claude (opus-4.5) | 종합 | $0.03 |
| **합계** | | **$0.06/기업** |

### 11.2 월간 비용 추정

| 시나리오 | 기업 수 | 갱신 주기 | 월 비용 |
|----------|---------|----------|--------|
| MVP | 100개 | 주 1회 | $24 |
| Pilot | 500개 | 주 1회 | $120 |
| Production | 1,000개 | 주 2회 | $480 |

---

## 12. 테스트 계획

### 12.1 단위 테스트

| 테스트 | 범위 |
|--------|------|
| Adapter 테스트 | 각 LLM Adapter의 search/parse/normalize |
| Consensus 테스트 | 일치/불일치 시나리오별 처리 |
| Fallback 테스트 | 각 Layer의 정상 작동 |

### 12.2 통합 테스트

| 테스트 | 범위 |
|--------|------|
| E2E 파이프라인 | 전체 흐름 (검색 → 종합 → 저장) |
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
| LLM API 장애 | HIGH | 4-Layer Fallback |
| 비용 폭발 | MED | Rate Limiting + 야간 배치 |
| Hallucination | MED | Consensus 교차 검증 |
| 응답 지연 | MED | 캐시 + Background 갱신 |
| 스키마 불일치 | LOW | 정규화 레이어 |

---

## 15. 부록

### 15.1 용어 정의

| 용어 | 정의 |
|------|------|
| Consensus | 두 LLM 결과를 비교하여 최종 값을 결정하는 과정 |
| Discrepancy | 두 LLM 결과가 불일치하는 상태 |
| Fallback | 주 경로 실패 시 대체 경로로 처리하는 것 |
| Circuit Breaker | 연속 실패 시 일시적으로 호출을 차단하는 패턴 |

### 15.2 참고 문서

- ADR-008: Security Architecture - LLM Separation
- CLAUDE.md: 프로젝트 메모리
- PRD v1.0 (원본): rKYC 시스템 요구사항

---

**문서 끝**

*Last Updated: 2026-01-19*
