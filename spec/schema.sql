-- Supabase schema for ai-system-spec.
-- Run in SQL Editor: https://supabase.com/dashboard/project/_/sql

-- research_cache: research summaries and system events (e.g. boot logs)
CREATE TABLE IF NOT EXISTS research_cache (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  topic text NOT NULL,
  content text NOT NULL,
  deep_analysis text,
  raw_transcript text,
  updated_at timestamptz,
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

-- planning_cache: planner outputs and evaluator feedback
CREATE TABLE IF NOT EXISTS planning_cache (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  topic text NOT NULL,
  plan_content text NOT NULL,
  eval_result text,
  created_at timestamptz DEFAULT now()
);
