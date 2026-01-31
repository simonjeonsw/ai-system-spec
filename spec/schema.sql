-- Supabase schema for ai-system-spec.
-- Run in SQL Editor: https://supabase.com/dashboard/project/_/sql

-- research_cache: research summaries and system events (e.g. boot logs)
CREATE TABLE IF NOT EXISTS research_cache (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  topic text NOT NULL,
  content text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- If table exists with wrong columns, add content:
-- ALTER TABLE research_cache ADD COLUMN IF NOT EXISTS content text;

-- scripts: script history for session sync
CREATE TABLE IF NOT EXISTS scripts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content text NOT NULL,
  created_at timestamptz DEFAULT now()
);
