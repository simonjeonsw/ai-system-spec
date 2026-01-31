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
