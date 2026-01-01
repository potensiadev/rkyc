-- Migration v4: Add VALIDATION and INSIGHT to progress_step_enum
-- Run this in Supabase SQL Editor

-- PostgreSQL doesn't allow easy enum modification, so we need to:
-- 1. Check if values already exist
-- 2. Add new values if they don't exist

-- Add VALIDATION if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'VALIDATION'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'progress_step_enum')
    ) THEN
        ALTER TYPE progress_step_enum ADD VALUE 'VALIDATION' AFTER 'SIGNAL';
    END IF;
END $$;

-- Add INSIGHT if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'INSIGHT'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'progress_step_enum')
    ) THEN
        ALTER TYPE progress_step_enum ADD VALUE 'INSIGHT' AFTER 'INDEX';
    END IF;
END $$;

-- Verify enum values
SELECT enumlabel
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'progress_step_enum')
ORDER BY enumsortorder;
