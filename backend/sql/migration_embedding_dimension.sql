-- Migration: Embedding 차원 1536 → 3072 변경
-- Model: text-embedding-3-small → text-embedding-3-large
-- 주의: 기존 embedding 데이터가 있으면 삭제됨
-- NOTE: IVFFlat은 최대 2000 차원까지만 지원 → HNSW 인덱스 사용

-- 1. 기존 인덱스 삭제 (IVFFlat → HNSW 변경)
DROP INDEX IF EXISTS idx_signal_embedding;
DROP INDEX IF EXISTS idx_case_embedding;

-- 2. 기존 embedding 데이터 삭제 (차원 불일치 방지)
DELETE FROM rkyc_signal_embedding;

-- 3. 컬럼 타입 변경
ALTER TABLE rkyc_signal_embedding
ALTER COLUMN embedding TYPE vector(3072);

-- 4. rkyc_case_index에도 embedding 컬럼이 있다면 동일하게 변경
ALTER TABLE rkyc_case_index
ALTER COLUMN embedding TYPE vector(3072);

-- 5. HNSW 인덱스 생성 (IVFFlat과 달리 차원 제한 없음, 성능도 더 좋음)
-- m: 각 노드당 연결 수 (기본 16), ef_construction: 빌드 시 탐색 범위 (기본 64)
CREATE INDEX idx_signal_embedding
ON rkyc_signal_embedding
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_case_embedding
ON rkyc_case_index
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
