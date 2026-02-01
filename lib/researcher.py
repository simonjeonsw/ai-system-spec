"""Research agent: fetch latest news and store in research_cache.

Uses duckduckgo-search for free news search. Inserts into Supabase
research_cache with topic='news_research'. Schema: spec/SCHEMA.md.
"""

import sys

from duckduckgo_search import DDGS

from lib.supabase_client import get_client

QUERY = "AI Agent Trends"
MAX_RESULTS = 3
TOPIC = "news_research"
# Text column per spec/SCHEMA.md; fallback if schema uses body/summary.
TEXT_COLUMNS = ("content", "body", "summary", "message")


def _format_item(title: str, link: str, summary: str) -> str:
    """One news item as a short block for content column."""
    return f"Title: {title}\nLink: {link}\nSummary: {summary}"


def main() -> int:
    # 1. Search news
    try:
        results = list(
            DDGS().news(QUERY, max_results=MAX_RESULTS)
        )
    except Exception as e:
        print(f"Search failed: {e}", file=sys.stderr)
        return 1

    if not results:
        print("No news results found.", file=sys.stderr)
        return 1

    # 2. Normalize keys (ddgs uses 'url' and 'body'; we want Link and Summary)
    items = []
    for r in results[:MAX_RESULTS]:
        title = r.get("title") or ""
        link = r.get("url") or r.get("href") or ""
        summary = (r.get("body") or "")[:500].strip()
        items.append(_format_item(title, link, summary))

    # 3. Insert into research_cache (topic NOT NULL, one row per item)
    client = get_client()
    last_error = None
    for col in TEXT_COLUMNS:
        try:
            rows = [{"topic": TOPIC, col: text} for text in items]
            client.table("research_cache").insert(rows).execute()
            print(f"Inserted {len(rows)} rows into research_cache (topic={TOPIC!r}).")
            return 0
        except Exception as e:
            last_error = e
            err_str = str(e)
            if "PGRST204" in err_str or "Could not find" in err_str:
                continue
            if "23502" in err_str:
                raise
            raise

    print(
        f"Insert failed: {last_error}\n"
        "research_cache needs topic and a text column (content/body/summary). "
        "See spec/SCHEMA.md.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
