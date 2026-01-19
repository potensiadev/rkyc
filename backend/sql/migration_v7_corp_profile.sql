-- Migration v7: Corp Profile with Anti-Hallucination Audit Trail
-- PRD: Corp Profiling Pipeline for ENVIRONMENT Signal Enhancement
-- Date: 2026-01-19

-- ============================================================================
-- Step 1: Add new ENUM values for evidence types
-- ============================================================================

-- Add CORP_PROFILE to evidence_type_enum
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'CORP_PROFILE'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'evidence_type_enum')
    ) THEN
        ALTER TYPE evidence_type_enum ADD VALUE 'CORP_PROFILE';
    END IF;
END
$$;

-- Add PROFILE_KEYPATH to ref_type_enum
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'PROFILE_KEYPATH'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'ref_type_enum')
    ) THEN
        ALTER TYPE ref_type_enum ADD VALUE 'PROFILE_KEYPATH';
    END IF;
END
$$;

-- Add PROFILING to progress_step_enum
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'PROFILING'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'progress_step_enum')
    ) THEN
        ALTER TYPE progress_step_enum ADD VALUE 'PROFILING' AFTER 'DOC_INGEST';
    END IF;
END
$$;

-- ============================================================================
-- Step 2: Create rkyc_corp_profile table
-- ============================================================================

CREATE TABLE IF NOT EXISTS rkyc_corp_profile (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corp_id VARCHAR(20) NOT NULL UNIQUE REFERENCES corp(corp_id) ON DELETE CASCADE,

    -- ========================================================================
    -- Extracted Profile Fields
    -- ========================================================================
    business_summary TEXT NOT NULL,
    revenue_krw BIGINT,
    export_ratio_pct INTEGER CHECK (export_ratio_pct IS NULL OR (export_ratio_pct >= 0 AND export_ratio_pct <= 100)),

    -- Exposure Information
    country_exposure JSONB DEFAULT '{}',      -- {"중국": 20, "미국": 30}
    key_materials TEXT[] DEFAULT '{}',        -- ["실리콘 웨이퍼", "PCB"]
    key_customers TEXT[] DEFAULT '{}',        -- ["삼성전자", "SK하이닉스"]
    overseas_operations TEXT[] DEFAULT '{}',  -- ["베트남 하노이 공장"]

    -- ========================================================================
    -- Confidence & Attribution (Anti-Hallucination Layer 2)
    -- ========================================================================
    profile_confidence confidence_level NOT NULL,
    field_confidences JSONB NOT NULL DEFAULT '{}',  -- {"export_ratio_pct": "HIGH", "country_exposure": "MED"}
    source_urls TEXT[] NOT NULL DEFAULT '{}',

    -- ========================================================================
    -- AUDIT TRAIL (Anti-Hallucination Layer 4 - Critical)
    -- ========================================================================
    raw_search_result JSONB,                  -- Complete Perplexity response for traceability
    field_provenance JSONB NOT NULL DEFAULT '{}',  -- Per-field source mapping
    -- Example: {
    --   "export_ratio_pct": {
    --     "source_url": "https://dart.fss.or.kr/...",
    --     "excerpt": "수출 비중은 62%를 기록",
    --     "confidence": "HIGH",
    --     "extraction_date": "2026-01-19T10:00:00Z"
    --   }
    -- }
    extraction_model VARCHAR(100),            -- LLM model used (e.g., "claude-opus-4-5-20251101")
    extraction_prompt_version VARCHAR(20) DEFAULT 'v1.0',  -- Prompt version for reproducibility

    -- ========================================================================
    -- Fallback & Validation Flags
    -- ========================================================================
    is_fallback BOOLEAN DEFAULT FALSE,        -- True if using industry default profile
    search_failed BOOLEAN DEFAULT FALSE,      -- True if Perplexity search failed
    validation_warnings TEXT[] DEFAULT '{}',  -- Warnings from CorpProfileValidator

    -- ========================================================================
    -- Status
    -- ========================================================================
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'UNKNOWN')),

    -- ========================================================================
    -- TTL Management
    -- ========================================================================
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,

    -- ========================================================================
    -- Timestamps
    -- ========================================================================
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Step 3: Create Indexes
-- ============================================================================

-- Primary lookup index
CREATE INDEX IF NOT EXISTS idx_corp_profile_corp_id ON rkyc_corp_profile(corp_id);

-- TTL management - find expired profiles
CREATE INDEX IF NOT EXISTS idx_corp_profile_expires ON rkyc_corp_profile(expires_at);

-- Filter by confidence level
CREATE INDEX IF NOT EXISTS idx_corp_profile_confidence ON rkyc_corp_profile(profile_confidence);

-- Filter by fallback status
CREATE INDEX IF NOT EXISTS idx_corp_profile_is_fallback ON rkyc_corp_profile(is_fallback);

-- Composite index for cache lookup (corp_id + expires_at)
CREATE INDEX IF NOT EXISTS idx_corp_profile_cache_lookup ON rkyc_corp_profile(corp_id, expires_at DESC);

-- ============================================================================
-- Step 4: Create trigger for updated_at
-- ============================================================================

-- Reuse existing trigger function if available, otherwise create
CREATE OR REPLACE FUNCTION update_corp_profile_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_corp_profile_updated_at ON rkyc_corp_profile;
CREATE TRIGGER trigger_corp_profile_updated_at
    BEFORE UPDATE ON rkyc_corp_profile
    FOR EACH ROW
    EXECUTE FUNCTION update_corp_profile_updated_at();

-- ============================================================================
-- Step 5: Comments for documentation
-- ============================================================================

COMMENT ON TABLE rkyc_corp_profile IS
'Corp Profile with anti-hallucination audit trail. Stores structured business profile
extracted from external sources (Perplexity) with full provenance tracking.';

COMMENT ON COLUMN rkyc_corp_profile.field_confidences IS
'Per-field confidence levels: {"field_name": "HIGH|MED|LOW"}.
HIGH = Official sources (DART, IR), MED = News, LOW = Estimates/Unknown';

COMMENT ON COLUMN rkyc_corp_profile.field_provenance IS
'Complete audit trail for each extracted field. Includes source_url, excerpt, confidence, and extraction_date.';

COMMENT ON COLUMN rkyc_corp_profile.raw_search_result IS
'Complete Perplexity API response preserved for audit. Never modify after creation.';

COMMENT ON COLUMN rkyc_corp_profile.is_fallback IS
'True if profile was created from industry defaults due to search failure or insufficient data.';

COMMENT ON COLUMN rkyc_corp_profile.extraction_prompt_version IS
'Version of the extraction prompt used. For reproducibility and debugging hallucination issues.';

-- ============================================================================
-- Verification queries
-- ============================================================================

-- Verify ENUM values added
SELECT enumlabel FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'evidence_type_enum')
ORDER BY enumsortorder;

SELECT enumlabel FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'ref_type_enum')
ORDER BY enumsortorder;

-- Verify table created
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'rkyc_corp_profile'
ORDER BY ordinal_position;
