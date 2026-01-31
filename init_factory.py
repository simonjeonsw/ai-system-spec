"""Factory init: verify Supabase connection and required tables.

- Connects using lib/supabase_client.
- Checks existence of research_cache and scripts.
- Inserts a System Boot log entry into research_cache.
"""

import sys

from lib.supabase_client import get_client

REQUIRED_TABLES = ("research_cache", "scripts")
BOOT_MESSAGE = "System Boot"


def main() -> int:
    client = get_client()

    for table in REQUIRED_TABLES:
        try:
            client.table(table).select("*").limit(1).execute()
        except Exception as e:
            print(f"Table '{table}' missing or inaccessible: {e}", file=sys.stderr)
            return 1
    print("Tables research_cache and scripts exist.")

    try:
        client.table("research_cache").insert({"message": BOOT_MESSAGE}).execute()
    except Exception as e:
        print(f"Insert failed (schema may differ): {e}", file=sys.stderr)
        return 1
    print(f"Inserted '{BOOT_MESSAGE}' into research_cache.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
