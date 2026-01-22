# PRD: Signal Analysis Enhancement - 구현 설계서

## 1. 개요

### 1.1 목표
- Signal Type별 특화된 LLM 프롬프트 적용
- RAG 파이프라인을 통한 증거 기반 요약 생성
- API 스키마 확장 (evidenceMap, eventClassification 등)

### 1.2 현재 상태 vs 목표 상태

| 항목 | 현재 | 목표 | Gap |
|------|------|------|-----|
| Signal Type별 프롬프트 | 단일 통합 프롬프트 | DIRECT/INDUSTRY/ENVIRONMENT 별도 | 프롬프트 분리 필요 |
| Evidence 활용 추적 | evidence_id만 연결 | evidenceMap (usedInSummary, reason) | 스키마 확장 필요 |
| Event Classification | event_type (10종) | eventClassification (8종) 추가 | 매핑 로직 필요 |
| Risk Insight | insight_excerpt (enriched) | riskInsight (대출/리스크 관점) | 프롬프트 추가 필요 |
| Action Suggestion | 없음 | actionSuggestion | 프롬프트 추가 필요 |
| RAG Pipeline | LLM에 모든 데이터 직접 전달 | Vector/Keyword 검색 기반 | 파이프라인 신규 구축 |

---

## 2. Signal Type별 프롬프트 설계

### 2.1 SIGNAL_TYPE_CONFIG 정의

```python
SIGNAL_TYPE_CONFIG = {
    "DIRECT": {
        "label": "기업 직접 영향",
        "description": "해당 기업에 직접적으로 영향을 미치는 변화",
        "analysisLogic": "기업 직접 언급된 정보 수집, 내부 스냅샷 변화와 외부 이벤트 연결",
        "evidenceSources": ["INTERNAL_FIELD", "DOC", "EXTERNAL"],
        "promptExtension": "기업명을 명시하고, 직접적인 재무/사업 영향을 중심으로 요약"
    },
    "INDUSTRY": {
        "label": "산업 영향",
        "description": "해당 산업 전체에 영향을 미치는 변화",
        "analysisLogic": "업종 이벤트 수집 후, 해당 기업과의 연관성 1문장 명시",
        "evidenceSources": ["EXTERNAL"],
        "promptExtension": "산업 이벤트 요약 + '{corp_name}에 미치는 영향' 1문장 포함"
    },
    "ENVIRONMENT": {
        "label": "거시환경 영향",
        "description": "정책, 규제, 거시경제 변화",
        "analysisLogic": "거시 환경 변화 수집 후, 기업/산업 영향 가능성 1문장 명시",
        "evidenceSources": ["EXTERNAL"],
        "promptExtension": "거시 변화 요약 + '{corp_name}/{industry_name}에 미치는 영향 가능성' 1문장"
    }
}
```

### 2.2 확장 프롬프트 템플릿

```python
SIGNAL_ANALYSIS_SYSTEM_PROMPT = """당신은 금융기관 KYC/리스크 분석 AI입니다.

## 역할
- 반드시 제공된 근거(Evidence)만 사용
- 추정/창작 금지
- 출력은 반드시 지정된 JSON 스키마 준수

## Signal Type 분석 규칙
{signal_type_rules}

## 출력 JSON 스키마
```json
{{
  "aiSummary": "Evidence 기반 2~4문장 요약",
  "confidenceLevel": "high|medium|low",
  "impact": "risk|opportunity|neutral",
  "impactStrength": "high|medium|low",
  "eventClassification": "supply_disruption|regulation|investment_ma|financial_change|governance|market_shift|policy_change|competitive_action",
  "evidenceMap": [
    {{ "evidenceId": "e1", "usedInSummary": true, "reason": "요약에 반영된 이유" }}
  ],
  "riskInsight": "대출/리스크 관점 참고 문장",
  "actionSuggestion": "담당자 후속 조치 제안"
}}
```

## Confidence Level 기준
- **high**: 공시(DART), 정부 발표, 내부 데이터 기반 (2개 이상 소스)
- **medium**: 주요 경제지, 신뢰할 수 있는 뉴스 기반 (1개 소스)
- **low**: 단일 출처, 추정 필요한 경우

## 금지 표현
❌ "반드시", "즉시", "확실히", "~할 것이다", "예상됨", "전망됨"
✅ "~로 추정됨", "~가능성 있음", "검토 권고", "~로 보도됨"
"""

# DIRECT 시그널 전용 규칙
DIRECT_SIGNAL_RULES = """
### DIRECT 시그널 분석 규칙
- **기업명 명시**: 요약에 반드시 '{corp_name}' 포함
- **직접 영향 중심**: 기업의 재무, 사업, 경영에 직접적인 영향을 주는 사건
- **내부 데이터 우선**: Internal Snapshot 변화는 HIGH confidence로 처리
- **Evidence 연결**: 모든 주장은 evidence_id로 추적 가능해야 함

### 허용 event_type
- KYC_REFRESH, INTERNAL_RISK_GRADE_CHANGE, OVERDUE_FLAG_ON
- LOAN_EXPOSURE_CHANGE, COLLATERAL_CHANGE, OWNERSHIP_CHANGE
- GOVERNANCE_CHANGE, FINANCIAL_STATEMENT_UPDATE
"""

# INDUSTRY 시그널 전용 규칙
INDUSTRY_SIGNAL_RULES = """
### INDUSTRY 시그널 분석 규칙
- **산업 이벤트 중심**: 업종 전체에 영향을 미치는 변화
- **기업 연관성 명시**: 요약 마지막에 "{corp_name}에 미치는 영향" 1문장 필수
- **event_type**: INDUSTRY_SHOCK만 사용
- **Evidence 연결**: 산업 뉴스/보고서 URL 필수

### 연관성 표현 예시
- "{corp_name}은 {industry_name} 업종으로, 해당 변화의 영향권에 있음"
- "수출 비중이 높은 {corp_name}의 경우 영향이 클 것으로 추정됨"
"""

# ENVIRONMENT 시그널 전용 규칙
ENVIRONMENT_SIGNAL_RULES = """
### ENVIRONMENT 시그널 분석 규칙
- **거시 변화 중심**: 정책, 규제, 거시경제 변화
- **기업/산업 영향 가능성 명시**: 요약에 영향 가능성 1문장 필수
- **event_type**: POLICY_REGULATION_CHANGE만 사용
- **Evidence 연결**: 정부 발표, 규제 문서 URL 필수

### 영향 가능성 표현 예시
- "{corp_name}은 {industry_name} 업종으로, 해당 정책의 영향을 받을 가능성 있음"
- "수출 기업인 {corp_name}의 경우 환율 변동 영향 검토 필요"
"""
```

### 2.3 Event Type → Event Classification 매핑

```python
EVENT_TYPE_TO_CLASSIFICATION = {
    # DIRECT event_types
    "KYC_REFRESH": "governance",
    "INTERNAL_RISK_GRADE_CHANGE": "financial_change",
    "OVERDUE_FLAG_ON": "financial_change",
    "LOAN_EXPOSURE_CHANGE": "financial_change",
    "COLLATERAL_CHANGE": "financial_change",
    "OWNERSHIP_CHANGE": "investment_ma",
    "GOVERNANCE_CHANGE": "governance",
    "FINANCIAL_STATEMENT_UPDATE": "financial_change",
    # INDUSTRY event_types
    "INDUSTRY_SHOCK": "market_shift",  # 또는 supply_disruption
    # ENVIRONMENT event_types
    "POLICY_REGULATION_CHANGE": "policy_change",  # 또는 regulation
}

EVENT_CLASSIFICATION_VALUES = [
    "supply_disruption",    # 공급망 차질
    "regulation",           # 규제 변화
    "investment_ma",        # 투자/M&A
    "financial_change",     # 재무 변화
    "governance",           # 지배구조
    "market_shift",         # 시장 변화
    "policy_change",        # 정책 변화
    "competitive_action",   # 경쟁사 동향
]
```

---

## 3. RAG Pipeline 설계

### 3.1 전체 아키텍처

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Ingestion   │────▶│  Indexing    │────▶│  Retrieval   │
│  (수집)       │     │  (인덱싱)     │     │  (검색)       │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Storage    │◀────│  Validation  │◀────│  Generation  │
│  (저장)       │     │  (검증)       │     │  (LLM 생성)   │
└──────────────┘     └──────────────┘     └──────────────┘
```

### 3.2 Stage별 상세

#### Stage 1: Ingestion (수집)
```python
class EvidenceIngestion:
    """
    외부 데이터 수집 및 정규화
    """
    def ingest(self, source_type: str, raw_data: dict) -> Evidence:
        return Evidence(
            evidence_id=generate_uuid(),
            source_type=source_type,  # news, disclosure, report, regulation, internal
            title=raw_data.get("title"),
            snippet=self._extract_snippet(raw_data),
            source_name=raw_data.get("source_name"),
            source_url=raw_data.get("url"),
            published_at=raw_data.get("published_at"),
            raw_content=raw_data.get("content"),
            metadata={
                "credibility": self._assess_credibility(raw_data),
                "industry_codes": self._extract_industry_codes(raw_data),
                "corp_mentions": self._extract_corp_mentions(raw_data),
            }
        )
```

#### Stage 2: Indexing (인덱싱)
```python
class EvidenceIndex:
    """
    Vector + Keyword 하이브리드 인덱싱
    """
    def __init__(self):
        self.vector_store = PGVectorStore()  # pgvector 기반
        self.keyword_index = PostgresFullText()  # tsvector 기반

    async def index(self, evidence: Evidence):
        # 1. Embedding 생성 (text-embedding-3-large)
        embedding = await self.embedding_service.embed(
            f"{evidence.title} {evidence.snippet}"
        )

        # 2. Vector Store 저장
        await self.vector_store.upsert(
            id=evidence.evidence_id,
            embedding=embedding,
            metadata={
                "source_type": evidence.source_type,
                "published_at": evidence.published_at,
                "corp_mentions": evidence.metadata.get("corp_mentions"),
            }
        )

        # 3. Keyword Index 저장
        await self.keyword_index.index(
            id=evidence.evidence_id,
            text=f"{evidence.title} {evidence.snippet} {evidence.raw_content}",
            fields={
                "title": evidence.title,
                "corp_names": evidence.metadata.get("corp_mentions"),
                "industry_codes": evidence.metadata.get("industry_codes"),
            }
        )
```

#### Stage 3: Retrieval (검색)
```python
class HybridRetriever:
    """
    Vector + Keyword 하이브리드 검색
    """
    async def retrieve(
        self,
        query: str,
        corp_id: str,
        signal_type: str,
        top_k: int = 10,
    ) -> list[Evidence]:
        # 1. Vector 검색 (semantic similarity)
        query_embedding = await self.embedding_service.embed(query)
        vector_results = await self.vector_store.search(
            embedding=query_embedding,
            top_k=top_k * 2,
            filters={"corp_mentions": {"$contains": corp_id}},
        )

        # 2. Keyword 검색 (exact match)
        keyword_results = await self.keyword_index.search(
            query=query,
            filters={
                "corp_id": corp_id,
                "signal_type_relevant": signal_type,
            },
            top_k=top_k * 2,
        )

        # 3. Reciprocal Rank Fusion (RRF)
        combined = self._rrf_merge(vector_results, keyword_results)

        # 4. Reranking (optional)
        reranked = await self._rerank(combined, query)

        return reranked[:top_k]
```

#### Stage 4: Generation (LLM 생성)
```python
class SignalAnalysisGenerator:
    """
    Signal Type별 분석 생성
    """
    async def generate(
        self,
        signal_input: SignalInput,
        evidences: list[Evidence],
        signal_type: str,
    ) -> SignalAnalysisOutput:
        # 1. Signal Type별 프롬프트 선택
        rules = self._get_signal_rules(signal_type)
        system_prompt = SIGNAL_ANALYSIS_SYSTEM_PROMPT.format(
            signal_type_rules=rules
        )

        # 2. User 프롬프트 구성
        user_prompt = self._format_user_prompt(
            signal_input=signal_input,
            evidences=evidences,
            signal_type_config=SIGNAL_TYPE_CONFIG[signal_type],
        )

        # 3. LLM 호출 (with fallback)
        response = await self.llm_service.call_with_json_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=SignalAnalysisOutput,
        )

        return response
```

#### Stage 5: Validation (검증)
```python
class SignalAnalysisValidator:
    """
    출력 검증 및 정제
    """
    def validate(self, output: dict, evidences: list[Evidence]) -> ValidationResult:
        errors = []
        warnings = []

        # 1. JSON 스키마 검증
        if not self._validate_schema(output):
            errors.append("Invalid JSON schema")

        # 2. Enum 범위 검증
        if output.get("eventClassification") not in EVENT_CLASSIFICATION_VALUES:
            errors.append(f"Invalid eventClassification: {output.get('eventClassification')}")

        # 3. EvidenceMap 검증
        evidence_ids = {e.evidence_id for e in evidences}
        for em in output.get("evidenceMap", []):
            if em.get("evidenceId") not in evidence_ids:
                errors.append(f"Unknown evidenceId: {em.get('evidenceId')}")

        # 4. 금지 표현 검증
        forbidden = self._check_forbidden_expressions(output.get("aiSummary", ""))
        if forbidden:
            warnings.append(f"Forbidden expressions found: {forbidden}")

        # 5. Confidence ↔ Evidence 수 검증
        evidence_count = len([em for em in output.get("evidenceMap", []) if em.get("usedInSummary")])
        if output.get("confidenceLevel") == "high" and evidence_count < 2:
            warnings.append("HIGH confidence requires 2+ evidence sources")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
```

---

## 4. API 스키마 확장

### 4.1 SignalAnalysisOutput 스키마

```python
from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum

class EventClassification(str, Enum):
    SUPPLY_DISRUPTION = "supply_disruption"
    REGULATION = "regulation"
    INVESTMENT_MA = "investment_ma"
    FINANCIAL_CHANGE = "financial_change"
    GOVERNANCE = "governance"
    MARKET_SHIFT = "market_shift"
    POLICY_CHANGE = "policy_change"
    COMPETITIVE_ACTION = "competitive_action"

class EvidenceMapItem(BaseModel):
    evidenceId: str = Field(..., description="Evidence ID")
    usedInSummary: bool = Field(..., description="요약에 반영 여부")
    reason: str = Field(..., description="반영 이유 (50자 이내)")

class SignalAnalysisOutput(BaseModel):
    """Signal Analysis LLM 출력 스키마"""
    aiSummary: str = Field(..., description="Evidence 기반 2-4문장 요약", max_length=500)
    confidenceLevel: Literal["high", "medium", "low"] = Field(..., description="신뢰도")
    impact: Literal["risk", "opportunity", "neutral"] = Field(..., description="영향 방향")
    impactStrength: Literal["high", "medium", "low"] = Field(..., description="영향 강도")
    eventClassification: EventClassification = Field(..., description="이벤트 분류")
    evidenceMap: list[EvidenceMapItem] = Field(..., description="Evidence 사용 맵")
    riskInsight: str = Field(..., description="대출/리스크 관점 참고 문장", max_length=200)
    actionSuggestion: str = Field(..., description="담당자 후속 조치 제안", max_length=200)
```

### 4.2 API 엔드포인트

#### 4.2.1 Signal 분석 요청
```
POST /api/v1/signals/{signal_id}/analyze
```

**Request Body:**
```json
{
  "forceRegenerate": false,
  "signalTypeOverride": null
}
```

**Response:**
```json
{
  "signalId": "uuid",
  "analysis": {
    "aiSummary": "엠케이전자의 2024년 3분기 연체 플래그가 활성화되었으며...",
    "confidenceLevel": "high",
    "impact": "risk",
    "impactStrength": "high",
    "eventClassification": "financial_change",
    "evidenceMap": [
      { "evidenceId": "e1", "usedInSummary": true, "reason": "연체 플래그 출처" },
      { "evidenceId": "e2", "usedInSummary": true, "reason": "내부 등급 변경 출처" }
    ],
    "riskInsight": "연체 발생으로 신용도 하락 가능성 있음. 담보 재평가 검토 권고.",
    "actionSuggestion": "1) 담보 현황 재확인 2) 여신 한도 재검토 3) 분기 재무제표 확보"
  },
  "generatedAt": "2026-01-22T10:30:00Z",
  "llmModel": "claude-opus-4-5-20251101"
}
```

#### 4.2.2 Evidence 검색
```
GET /api/v1/evidences?corpId={corpId}&signalId={signalId}&signalType={signalType}
```

**Response:**
```json
{
  "evidences": [
    {
      "evidenceId": "e1",
      "sourceType": "internal",
      "title": "Internal Snapshot 변경",
      "snippet": "overdue_flag: false → true",
      "sourceName": "rkyc_internal_snapshot",
      "publishedAt": "2026-01-20T00:00:00Z",
      "refType": "SNAPSHOT_KEYPATH",
      "refValue": "/credit/loan_summary/overdue_flag",
      "credibility": "official"
    }
  ],
  "totalCount": 5
}
```

---

## 5. 데이터베이스 스키마 확장

### 5.1 rkyc_signal_analysis 테이블 (신규)

```sql
CREATE TABLE rkyc_signal_analysis (
    analysis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id),

    -- LLM 분석 결과
    ai_summary TEXT NOT NULL,
    confidence_level VARCHAR(10) NOT NULL CHECK (confidence_level IN ('high', 'medium', 'low')),
    event_classification VARCHAR(30) NOT NULL,
    risk_insight TEXT,
    action_suggestion TEXT,

    -- Evidence Map (JSONB)
    evidence_map JSONB NOT NULL DEFAULT '[]',

    -- 메타데이터
    llm_model VARCHAR(100),
    llm_prompt_version VARCHAR(20),
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 인덱스
    UNIQUE (signal_id)
);

CREATE INDEX idx_signal_analysis_signal_id ON rkyc_signal_analysis(signal_id);
CREATE INDEX idx_signal_analysis_classification ON rkyc_signal_analysis(event_classification);
```

### 5.2 rkyc_evidence 테이블 확장

```sql
ALTER TABLE rkyc_evidence
ADD COLUMN IF NOT EXISTS raw_content TEXT,
ADD COLUMN IF NOT EXISTS credibility VARCHAR(20) DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS embedding vector(2000);

-- Credibility ENUM 값: official, major_media, minor_media, unknown
-- embedding: 검색용 벡터 (text-embedding-3-large, 2000d)

CREATE INDEX idx_evidence_embedding ON rkyc_evidence
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

---

## 6. 구현 우선순위

### Phase 1: 기반 작업 (1-2일)
1. ✅ SIGNAL_TYPE_CONFIG 및 확장 프롬프트 정의
2. ✅ SignalAnalysisOutput Pydantic 스키마 정의
3. ✅ EVENT_TYPE_TO_CLASSIFICATION 매핑 구현
4. DB 마이그레이션 (rkyc_signal_analysis 테이블)

### Phase 2: RAG 파이프라인 (3-4일)
1. EvidenceIndex 클래스 구현 (Vector + Keyword)
2. HybridRetriever 구현 (RRF 병합)
3. SignalAnalysisGenerator 구현
4. SignalAnalysisValidator 구현

### Phase 3: API 통합 (2일)
1. POST /api/v1/signals/{id}/analyze 엔드포인트
2. GET /api/v1/evidences 검색 엔드포인트
3. SignalDetailPage UI 연동 (aiSummary, evidenceMap, riskInsight 표시)

### Phase 4: 테스트 및 최적화 (2일)
1. 6개 기업 시드 데이터로 E2E 테스트
2. 프롬프트 튜닝 (금지 표현 검증, Confidence 정확도)
3. RAG 검색 품질 평가 (Recall@10)

---

## 7. 참고: 현재 코드베이스 매핑

| PRD 항목 | 현재 파일 | 변경 필요 |
|----------|----------|----------|
| LLM Prompts | `backend/app/worker/llm/prompts.py` | 확장 |
| Signal Pipeline | `backend/app/worker/pipelines/signal_extraction.py` | 수정 |
| Validation | `backend/app/worker/pipelines/validation.py` | 수정 |
| Evidence Schema | `backend/app/schemas/signal.py` | 확장 |
| Enriched API | `backend/app/api/v1/endpoints/signals_enriched.py` | 확장 |
| Embedding | `backend/app/worker/llm/embedding.py` | 재사용 |
| Frontend | `src/pages/SignalDetailPage.tsx` | 수정 |

---

*작성일: 2026-01-22*
*버전: v1.0*
