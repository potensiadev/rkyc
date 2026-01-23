-- ============================================================================
-- Migration v9: Fix NULL field_provenance in existing profiles
-- Purpose: Mark profiles with NULL/empty field_provenance for regeneration
-- ============================================================================

-- P2-1 Fix: Set expires_at to past for profiles with NULL/empty field_provenance
-- This will trigger regeneration on next access

UPDATE rkyc_corp_profile
SET
    expires_at = NOW() - INTERVAL '1 day',
    updated_at = NOW()
WHERE
    field_provenance IS NULL
    OR field_provenance = '{}'::jsonb
    OR jsonb_typeof(field_provenance) IS NULL;

-- Log affected rows
DO $$
DECLARE
    affected_count INTEGER;
BEGIN
    GET DIAGNOSTICS affected_count = ROW_COUNT;
    RAISE NOTICE 'Updated % profiles with NULL/empty field_provenance', affected_count;
END $$;

-- Also add index for faster lookup of expired profiles (if not exists)
CREATE INDEX IF NOT EXISTS idx_corp_profile_expires_at
ON rkyc_corp_profile(expires_at);

-- Add index for provenance-based queries
CREATE INDEX IF NOT EXISTS idx_corp_profile_field_provenance_null
ON rkyc_corp_profile((field_provenance IS NULL));

COMMENT ON INDEX idx_corp_profile_expires_at IS 'For efficient expired profile lookup';
COMMENT ON INDEX idx_corp_profile_field_provenance_null IS 'For finding profiles needing provenance regeneration';
