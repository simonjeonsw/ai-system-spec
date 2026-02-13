"""Compute weekly false-hold/false-promote calibration metrics from labeled outcomes."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List


VALID = {"correct_hold", "false_hold", "correct_promote", "false_promote"}


def build_report(outcomes: List[Dict[str, str]]) -> Dict[str, float]:
    total = len(outcomes)
    if total == 0:
        return {
            "total": 0,
            "false_hold_rate": 0.0,
            "false_promote_rate": 0.0,
            "correct_hold_rate": 0.0,
            "correct_promote_rate": 0.0,
        }

    counts = {label: 0 for label in VALID}
    for item in outcomes:
        label = item.get("label")
        if label not in VALID:
            raise ValueError(f"Unknown calibration label: {label}")
        counts[label] += 1

    return {
        "total": total,
        "false_hold_rate": counts["false_hold"] / total,
        "false_promote_rate": counts["false_promote"] / total,
        "correct_hold_rate": counts["correct_hold"] / total,
        "correct_promote_rate": counts["correct_promote"] / total,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/policy_calibration_report.py <labeled_outcomes.json>", file=sys.stderr)
        return 1

    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    outcomes = payload.get("historical_outcomes", [])
    report = build_report(outcomes)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
