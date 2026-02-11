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
-- Ensure upserts on topic are supported:
CREATE UNIQUE INDEX IF NOT EXISTS research_cache_topic_key ON research_cache (topic);

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
-- Ensure upserts on topic are supported:
CREATE UNIQUE INDEX IF NOT EXISTS planning_cache_topic_key ON planning_cache (topic);

-- video_scenes: scene builder outputs per video
CREATE TABLE IF NOT EXISTS video_scenes (
  video_id text PRIMARY KEY,
  content jsonb NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- video_metadata: generated metadata per video
CREATE TABLE IF NOT EXISTS video_metadata (
  video_id text PRIMARY KEY,
  title text NOT NULL,
  description text NOT NULL,
  tags jsonb NOT NULL,
  chapters jsonb NOT NULL,
  pinned_comment text NOT NULL,
  pinned_comment_variants jsonb,
  thumbnail_variants jsonb,
  community_post text,
  community_post_variants jsonb,
  estimated_runtime_sec integer,
  speech_rate_wpm integer,
  schema_version text NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- video_uploads: upload attempt logs per video
CREATE TABLE IF NOT EXISTS video_uploads (
  video_id text PRIMARY KEY,
  status text,
  notify_subscribers boolean,
  published_at timestamptz,
  metadata_path text,
  video_path text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- video_scripts: long-form + shorts scripts per video
CREATE TABLE IF NOT EXISTS video_scripts (
  video_id text PRIMARY KEY,
  long_script jsonb,
  shorts_script jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- metadata_experiments: packaging/conversion experiment logs
CREATE TABLE IF NOT EXISTS metadata_experiments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id text NOT NULL,
  experiment_type text NOT NULL,
  title_variant text,
  thumbnail_variant text,
  start_date timestamptz,
  end_date timestamptz,
  ctr numeric,
  avd numeric,
  notes text,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS metadata_experiments_video_id_idx ON metadata_experiments (video_id);
