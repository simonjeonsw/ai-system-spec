# Database Schema (Supabase / PostgreSQL)

Canonical schema for ai-system-spec tables. Code must match these definitions.

## research_cache

Stores research summaries and system events (e.g. boot logs) for the Context Cache.
Used to avoid re-researching topics within 7 days (see SYSTEM_ARCH.md).

| Column     | Type         | Notes                          |
|------------|--------------|--------------------------------|
| id         | uuid         | PK, default gen_random_uuid()  |
| topic      | text         | NOT NULL; UNIQUE; use "system" for boot logs |
| content    | text         | Research summary or log text   |
| deep_analysis | text      | Optional: extended analysis payload |
| raw_transcript | text     | Optional: raw transcript/log data |
| updated_at | timestamptz  | Optional: last update timestamp |
| created_at | timestamptz  | default now()                  |

**Boot log insert:** `{ "content": "System Boot" }`

## scripts

Stores script history for session sync (see SYSTEM_ARCH.md).

| Column     | Type        | Notes                         |
|------------|-------------|-------------------------------|
| id         | uuid        | PK, default gen_random_uuid() |
| content    | text        | Script body                   |
| created_at | timestamptz | default now()                 |

## planning_cache

Stores planner outputs and evaluator feedback for downstream stages.

| Column      | Type        | Notes                         |
|-------------|-------------|-------------------------------|
| id          | uuid        | PK, default gen_random_uuid() |
| topic       | text        | NOT NULL; UNIQUE              |
| plan_content| text        | Planner output                |
| eval_result | text        | Evaluator feedback            |
| created_at  | timestamptz | default now()                 |

## pipeline_runs

Stores structured run logs for pipeline execution and observability.

| Column        | Type        | Notes                                                  |
|---------------|-------------|--------------------------------------------------------|
| id            | uuid        | PK, default gen_random_uuid()                          |
| run_id        | text        | Stable identifier per run                              |
| stage         | text        | Pipeline stage name (research/script/qa/upload/etc.)    |
| status        | text        | success / failure / retry / skipped                 |
| attempts      | int         | Retry count for this stage                             |
| input_refs    | jsonb       | References to inputs (topic IDs, cache keys, etc.)      |
| output_refs   | jsonb       | References to outputs (artifact IDs, URLs, etc.)        |
| error_summary | text        | Short error message if failed                           |
| metrics       | jsonb       | Per-stage metrics (latency, tokens, cost, cache_hit)    |
| created_at    | timestamptz | default now()                                          |

## metadata_experiments

Stores A/B testing results for titles and thumbnails.

| Column            | Type        | Notes                                                  |
|-------------------|-------------|--------------------------------------------------------|
| id                | uuid        | PK, default gen_random_uuid()                          |
| video_id          | text        | Stable video identifier                                |
| experiment_type   | text        | title / thumbnail / other                              |
| title_variant     | text        | Title variant label or value                           |
| thumbnail_variant | text        | Thumbnail variant label or asset reference             |
| start_date        | timestamptz | Experiment start                                       |
| end_date          | timestamptz | Experiment end                                         |
| ctr               | numeric     | Click-through rate                                     |
| avd               | numeric     | Average view duration                                  |
| notes             | text        | Optional insights/decisions                            |
| created_at        | timestamptz | default now()                                          |

## video_scenes

Stores scene builder outputs for each video.

| Column     | Type        | Notes                                  |
|------------|-------------|----------------------------------------|
| video_id   | text        | PK; YouTube video ID or normalized ID  |
| content    | jsonb       | Scene output payload                   |
| created_at | timestamptz | default now()                          |
| updated_at | timestamptz | default now()                          |

## video_metadata

Stores generated metadata for each video.

| Column         | Type        | Notes                                  |
|----------------|-------------|----------------------------------------|
| video_id       | text        | PK; YouTube video ID or normalized ID  |
| title          | text        | Generated title                         |
| description    | text        | Generated description                   |
| tags           | jsonb       | Tag list                                |
| chapters       | jsonb       | Chapter list                            |
| pinned_comment | text        | Generated pinned comment                |
| schema_version | text        | Schema version                          |
| created_at     | timestamptz | default now()                          |
| updated_at     | timestamptz | default now()                          |

## channel_configs

Stores per-channel configuration profiles for multi-channel scaling.

| Column        | Type        | Notes                                         |
|---------------|-------------|-----------------------------------------------|
| id            | uuid        | PK, default gen_random_uuid()                 |
| channel_id    | text        | Unique channel identifier                     |
| name          | text        | Display name                                  |
| tone_profile  | text        | Tone or style profile                         |
| format_profile| text        | Format template reference                     |
| kpi_targets   | jsonb       | Target KPIs (CTR, AVD, RPM, cadence)          |
| created_at    | timestamptz | default now()                                 |

## channel_costs

Tracks per-channel cost and usage for governance and scaling.

| Column        | Type        | Notes                                         |
|---------------|-------------|-----------------------------------------------|
| id            | uuid        | PK, default gen_random_uuid()                 |
| channel_id    | text        | Channel identifier                            |
| run_id        | text        | Pipeline run reference                        |
| provider      | text        | API/model provider                            |
| cost_usd      | numeric     | Estimated cost in USD                         |
| tokens        | int         | Token usage (if applicable)                   |
| created_at    | timestamptz | default now()                                 |
