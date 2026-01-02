-- ============================================
-- rKYC Database Migration v5: Vector Search
-- pgvector extension for embedding-based search
-- ============================================

-- Prerequisites:
-- Supabase projects have pgvector pre-installed
-- If running locally, run: CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 1. Enable pgvector extension
-- ============================================

-- This should already be available in Supabase
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 2. Signal Embedding Table
-- ============================================

-- Stores embedding vectors for signals
-- Used for semantic search and similar signal discovery
CREATE TABLE IF NOT EXISTS rkyc_signal_embedding (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES rkyc_signal(signal_id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,  -- OpenAI text-embedding-3-small dimension
    model_name VARCHAR(100) DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one embedding per signal
    UNIQUE(signal_id)
);

COMMENT ON TABLE rkyc_signal_embedding IS 'Signal embedding vectors for semantic search (PRD INDEX stage)';
COMMENT ON COLUMN rkyc_signal_embedding.embedding IS 'OpenAI text-embedding-3-small vector (1536 dimensions)';

-- ============================================
-- 3. Case Index Embedding Column
-- ============================================

-- Add embedding column to existing rkyc_case_index table
-- This enables similar case search for Insight Memory
ALTER TABLE rkyc_case_index
ADD COLUMN IF NOT EXISTS embedding vector(1536);

ALTER TABLE rkyc_case_index
ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small';

COMMENT ON COLUMN rkyc_case_index.embedding IS 'Case embedding vector for similar case search';

-- ============================================
-- 4. Vector Search Indexes
-- ============================================

-- IVFFlat index for signal embeddings
-- Good for datasets < 1M vectors
-- lists = sqrt(num_vectors), minimum 100
CREATE INDEX IF NOT EXISTS idx_signal_embedding_vector
ON rkyc_signal_embedding
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- IVFFlat index for case embeddings
CREATE INDEX IF NOT EXISTS idx_case_embedding_vector
ON rkyc_case_index
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ============================================
-- 5. Helper Functions
-- ============================================

-- Function to find similar signals by embedding
CREATE OR REPLACE FUNCTION find_similar_signals(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    signal_id UUID,
    corp_id VARCHAR(20),
    signal_type signal_type_enum,
    event_type event_type_enum,
    summary TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.signal_id,
        s.corp_id,
        s.signal_type,
        s.event_type,
        s.summary,
        1 - (se.embedding <=> query_embedding) AS similarity
    FROM rkyc_signal_embedding se
    JOIN rkyc_signal s ON se.signal_id = s.signal_id
    WHERE 1 - (se.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY se.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION find_similar_signals IS 'Find signals similar to query embedding using cosine similarity';

-- Function to find similar cases for Insight Memory
CREATE OR REPLACE FUNCTION find_similar_cases(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    case_id UUID,
    corp_id VARCHAR(20),
    industry_code VARCHAR(10),
    signal_type signal_type_enum,
    event_type event_type_enum,
    summary TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.case_id,
        c.corp_id,
        c.industry_code,
        c.signal_type,
        c.event_type,
        c.summary,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM rkyc_case_index c
    WHERE c.embedding IS NOT NULL
      AND 1 - (c.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON FUNCTION find_similar_cases IS 'Find similar past cases using embedding similarity';

-- ============================================
-- 6. Verification Queries
-- ============================================

-- Check if extension is installed
-- SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check tables
-- SELECT COUNT(*) FROM rkyc_signal_embedding;
-- SELECT COUNT(*) FROM rkyc_case_index WHERE embedding IS NOT NULL;

-- Test similarity search (requires embeddings to be populated)
-- SELECT * FROM find_similar_signals(
--     (SELECT embedding FROM rkyc_signal_embedding LIMIT 1),
--     5,
--     0.5
-- );

-- ============================================
-- Notes
-- ============================================

-- Index Types:
-- - IVFFlat: Fast approximate search, good for < 1M vectors
-- - HNSW: Better recall, slower build, good for > 1M vectors
--
-- Distance Operators:
-- - <-> : L2 distance (Euclidean)
-- - <#> : Inner product (dot product)
-- - <=> : Cosine distance (1 - cosine similarity)
--
-- For OpenAI embeddings, cosine distance (<=>)  is recommended
--
-- To rebuild index after adding many vectors:
-- REINDEX INDEX idx_signal_embedding_vector;
-- REINDEX INDEX idx_case_embedding_vector;
