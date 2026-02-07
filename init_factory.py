"""Factory init: verify Supabase connection and required tables.

- Connects using lib/supabase_client.
- Checks existence of research_cache, scripts, and planning_cache.
- Inserts a System Boot log entry into research_cache.
- Schema: spec/SCHEMA.md, spec/schema.sql
"""

import sys

from lib.supabase_client import get_client

REQUIRED_TABLES = ("research_cache", "scripts", "planning_cache")
BOOT_MESSAGE = "System Boot"
# Text column for log body; try common names (schema may vary).
TEXT_COLUMNS = ("content", "body", "summary", "message")


def main() -> int:
    client = get_client()

    for table in REQUIRED_TABLES:
        try:
            client.table(table).select("*").limit(1).execute()
        except Exception as e:
            print(f"Table '{table}' missing or inaccessible: {e}", file=sys.stderr)
            return 1
    print("Tables research_cache, scripts, and planning_cache exist.")

    # research_cache: topic NOT NULL, plus a text column. See spec/SCHEMA.md.
    last_error = None
    for col in TEXT_COLUMNS:
        try:
            client.table("research_cache").insert(
                {"topic": "system", col: BOOT_MESSAGE}
            ).execute()
            print(f"Inserted '{BOOT_MESSAGE}' into research_cache.")
            return 0
        except Exception as e:
            last_error = e
            err_str = str(e)
            if "PGRST204" in err_str or "Could not find" in err_str:
                continue
            if "23502" in err_str:  # NOT NULL violation - column exists
                raise
            raise

    print(
        f"Insert failed: {last_error}\n"
        "research_cache needs: topic (NOT NULL) and a text column "
        "(content, body, summary, or message). See spec/schema.sql.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
