"""Competitor benchmarking utilities for title and structure analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


TARGETS_PATH = Path(__file__).resolve().parent.parent / "config" / "targets.json"


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


def load_targets(path: Path | None = None) -> Dict[str, List[str]]:
    target_path = path or TARGETS_PATH
    if not target_path.exists():
        return {"benchmark_channels": [], "focus_areas": []}
    return json.loads(target_path.read_text(encoding="utf-8"))


def build_planner_context() -> Dict[str, List[str]]:
    targets = load_targets()
    return {
        "benchmark_channels": targets.get("benchmark_channels", []),
        "focus_areas": targets.get("focus_areas", []),
    }


def main() -> int:
    targets = load_targets()
    sample = [
        "Why Inflation Feels Worse Than It Is: The Hidden Metrics",
        "The Leverage Trap: How Borrowing Wipes Out Investors",
        "Fed Rate Cuts Explained: What Happens Next?",
    ]
    print(json.dumps({"targets": targets, "summary": summarize_benchmarks(sample)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
