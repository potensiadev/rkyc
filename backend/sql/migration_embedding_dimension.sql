-- Migration: Embedding 차원 1536 → 2000 변경
-- Model: text-embedding-3-small → text-embedding-3-large (dimensions=2000)
-- 주의: 기존 embedding 데이터가 있으면 삭제됨
-- NOTE: pgvector는 최대 2000 차원까지만 지원 (IVFFlat/HNSW 모두)

-- 1. 기존 인덱스 삭제
DROP INDEX IF EXISTS idx_signal_embedding;
DROP INDEX IF EXISTS idx_case_embedding;
DROP INDEX IF EXISTS idx_signal_embedding_vector;
DROP INDEX IF EXISTS idx_case_embedding_vector;

-- 2. 기존 embedding 데이터 삭제 (차원 불일치 방지)
DELETE FROM rkyc_signal_embedding;

-- 3. 컬럼 타입 변경 (2000 = pgvector 최대 지원 차원)
ALTER TABLE rkyc_signal_embedding
ALTER COLUMN embedding TYPE vector(2000);

ALTER TABLE rkyc_case_index
ALTER COLUMN embedding TYPE vector(2000);

-- 4. HNSW 인덱스 생성 (IVFFlat보다 검색 성능 우수)
CREATE INDEX idx_signal_embedding_vector
ON rkyc_signal_embedding
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_case_embedding_vector
ON rkyc_case_index
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
