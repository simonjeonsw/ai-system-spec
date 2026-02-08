"""Competitor benchmarking utilities for title and structure analysis."""

from __future__ import annotations

import json
from typing import Dict, List


def normalize_titles(titles: List[str]) -> Dict[str, List[str]]:
    normalized = [title.strip() for title in titles if title and title.strip()]
    hooks = [title.split(":")[0] for title in normalized if ":" in title]
    return {
        "titles": normalized,
        "hook_patterns": hooks,
    }


def summarize_benchmarks(titles: List[str]) -> Dict[str, List[str]]:
    normalized = normalize_titles(titles)
    return {
        "top_hooks": normalized["hook_patterns"][:10],
        "packaging_patterns": normalized["titles"][:10],
    }


def main() -> int:
    sample = [
        "Why Inflation Feels Worse Than It Is: The Hidden Metrics",
        "The Leverage Trap: How Borrowing Wipes Out Investors",
        "Fed Rate Cuts Explained: What Happens Next?",
    ]
    print(json.dumps(summarize_benchmarks(sample), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
