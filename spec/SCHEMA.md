# Database Schema (Supabase / PostgreSQL)

Canonical schema for ai-system-spec tables. Code must match these definitions.

## research_cache

Stores research summaries and system events (e.g. boot logs) for the Context Cache.
Used to avoid re-researching topics within 7 days (see SYSTEM_ARCH.md).

| Column     | Type         | Notes                          |
|------------|--------------|--------------------------------|
| id         | uuid         | PK, default gen_random_uuid()  |
| topic      | text         | NOT NULL; use "system" for boot logs |
| content    | text         | Research summary or log text   |
| created_at | timestamptz  | default now()                  |

**Boot log insert:** `{ "content": "System Boot" }`

## scripts

Stores script history for session sync (see SYSTEM_ARCH.md).

| Column     | Type        | Notes                         |
|------------|-------------|-------------------------------|
| id         | uuid        | PK, default gen_random_uuid() |
| content    | text        | Script body                   |
| created_at | timestamptz | default now()                 |

## pipeline_runs

Stores structured run logs for pipeline execution and observability.

| Column        | Type        | Notes                                                  |
|---------------|-------------|--------------------------------------------------------|
| id            | uuid        | PK, default gen_random_uuid()                          |
| run_id        | text        | Stable identifier per run                              |
| stage         | text        | Pipeline stage name (research/script/qa/upload/etc.)    |
| status        | text        | success | failure | retry | skipped                     |
| attempts      | int         | Retry count for this stage                             |
| input_refs    | jsonb       | References to inputs (topic IDs, cache keys, etc.)      |
| output_refs   | jsonb       | References to outputs (artifact IDs, URLs, etc.)        |
| error_summary | text        | Short error message if failed                           |
| metrics       | jsonb       | Per-stage metrics (latency, tokens, cost, cache_hit)    |
| created_at    | timestamptz | default now()                                          |
