-- Migration: Embedding 차원 1536 → 3072 변경
-- Model: text-embedding-3-small → text-embedding-3-large
-- 주의: 기존 embedding 데이터가 있으면 삭제됨

-- 1. 기존 embedding 데이터 삭제 (차원 불일치 방지)
DELETE FROM rkyc_signal_embedding;

-- 2. 컬럼 타입 변경
ALTER TABLE rkyc_signal_embedding
ALTER COLUMN embedding TYPE vector(3072);

-- 3. rkyc_case_index에도 embedding 컬럼이 있다면 동일하게 변경
ALTER TABLE rkyc_case_index
ALTER COLUMN embedding TYPE vector(3072);

-- 4. 인덱스 재생성 (차원 변경 시 필요)
DROP INDEX IF EXISTS idx_signal_embedding;
CREATE INDEX idx_signal_embedding
ON rkyc_signal_embedding
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

DROP INDEX IF EXISTS idx_case_embedding;
CREATE INDEX idx_case_embedding
ON rkyc_case_index
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
