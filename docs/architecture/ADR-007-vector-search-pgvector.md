# ADR-007: Vector Search - pgvector 기반 유사 케이스 검색

## 상태
**승인됨** (2026-01-02)

## 컨텍스트
rKYC 시스템의 INDEX(7단계) 및 INSIGHT(8단계) 파이프라인에서 시그널과 과거 케이스의 의미적 유사성을 기반으로 검색 기능이 필요합니다.

### 요구사항
- 시그널 요약 텍스트 벡터화
- 유사 시그널/케이스 검색
- 인사이트 메모리 (과거 케이스 참조)
- Supabase PostgreSQL 호환

## 결정

### Embedding 모델 선택
**OpenAI text-embedding-3-large**
- Dimension: 2000 (pgvector 최대 지원)
- 품질 우선 ($0.00013/1K tokens)
- 한국어 지원
- 최고 수준의 의미 표현

### Vector Database 선택
**pgvector (Supabase 내장)**

선택 이유:
1. **인프라 단순화**: 별도 벡터 DB 불필요
2. **Supabase 기본 지원**: 추가 설정 최소화
3. **트랜잭션 일관성**: Signal과 Embedding 동시 저장
4. **비용**: 추가 서비스 비용 없음

### 인덱스 전략
**IVFFlat (Inverted File with Flat)**

```sql
CREATE INDEX idx_signal_embedding_vector
ON rkyc_signal_embedding
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

선택 이유:
- 현재 데이터 규모 (< 10K signals)에 적합
- 빠른 인덱스 빌드
- 메모리 효율적

HNSW 대비:
- HNSW는 대규모 (> 1M) 데이터에 적합
- 현재 규모에서는 IVFFlat이 더 효율적

### 스키마 설계

```sql
-- Signal Embedding (별도 테이블)
CREATE TABLE rkyc_signal_embedding (
    embedding_id UUID PRIMARY KEY,
    signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id),
    embedding vector(1536) NOT NULL,
    model_name VARCHAR(100),
    created_at TIMESTAMPTZ,
    UNIQUE(signal_id)
);

-- Case Index (기존 테이블에 컬럼 추가)
ALTER TABLE rkyc_case_index
ADD COLUMN embedding vector(1536);
```

### 유사도 검색 쿼리

```sql
-- Cosine Similarity 기반 검색
SELECT
    signal_id,
    summary,
    1 - (embedding <=> query_embedding) AS similarity
FROM rkyc_signal_embedding
WHERE 1 - (embedding <=> query_embedding) >= 0.7
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

## 대안 검토

### Option A: Pinecone
- 장점: 관리형 서비스, 고성능
- 단점: 추가 비용 ($70+/월), 데이터 분산

### Option B: Weaviate
- 장점: 오픈소스, 다양한 기능
- 단점: 자체 운영 필요, 복잡성 증가

### Option C: pgvector (선택)
- 장점: Supabase 내장, 비용 없음, 단순성
- 단점: 대규모 확장 시 성능 제한

## 결과

### 구현된 컴포넌트
- `EmbeddingService` (llm/embedding.py)
- `migration_v5_vector.sql` (pgvector 스키마)
- `IndexPipeline` 임베딩 저장 로직
- `InsightPipeline` 유사 케이스 검색

### 처리 흐름
```
Signal 생성 → Summary 텍스트 추출 → Embedding 생성 (batch)
    → rkyc_signal_embedding 저장 → 유사 케이스 검색 가능
```

### 성능 고려사항
- Embedding 생성: ~100ms/signal (batch 처리)
- 유사 검색: ~50ms (top-5)
- 인덱스 재구축: 데이터 증가 시 `REINDEX` 필요

### 확장 계획
- 100K+ signals: HNSW 인덱스로 전환 검토
- 1M+ signals: 별도 벡터 DB (Pinecone) 검토

## 참고
- PRD 14.8: 인사이트 메모리 케이스 인덱스
- pgvector 문서: https://github.com/pgvector/pgvector
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
