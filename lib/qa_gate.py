"""QA gate evaluation for CTR/AVD/30s retention metrics."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict

from .run_logger import emit_run_log


THRESHOLDS = {
    "finance": {"ctr": 5.0, "avd": 40.0, "retention_30s": 65.0},
    "education": {"ctr": 4.0, "avd": 45.0, "retention_30s": 70.0},
    "news": {"ctr": 5.5, "avd": 35.0, "retention_30s": 60.0},
}

GOVERNANCE = {
    "finance": {
        "publish": {"ctr": 5.0, "avd": 40.0},
        "hold": {"ctr": (4.0, 4.9), "avd": (35.0, 39.0)},
        "rework": {"ctr": 4.0, "avd": 35.0},
    },
    "education": {
        "publish": {"ctr": 4.0, "avd": 45.0},
        "hold": {"ctr": (3.2, 3.9), "avd": (38.0, 44.0)},
        "rework": {"ctr": 3.2, "avd": 38.0},
    },
    "news": {
        "publish": {"ctr": 5.5, "avd": 35.0},
        "hold": {"ctr": (4.5, 5.4), "avd": (30.0, 34.0)},
        "rework": {"ctr": 4.5, "avd": 30.0},
    },
}


def evaluate_metrics(metrics: Dict[str, float], channel_type: str) -> Dict[str, str]:
    if channel_type not in THRESHOLDS:
        raise ValueError(f"Unknown channel_type: {channel_type}")

    ctr = float(metrics["ctr"])
    avd = float(metrics["avd"])
    retention_30s = float(metrics["retention_30s"])

    decision = "hold"
    rules = GOVERNANCE[channel_type]
    if ctr >= rules["publish"]["ctr"] and avd >= rules["publish"]["avd"]:
        decision = "publish"
    elif ctr < rules["rework"]["ctr"] or avd < rules["rework"]["avd"]:
        decision = "rework"

    pass_flags = []
    thresholds = THRESHOLDS[channel_type]
    if ctr < thresholds["ctr"]:
        pass_flags.append("ctr_below_baseline")
    if avd < thresholds["avd"]:
        pass_flags.append("avd_below_baseline")
    if retention_30s < thresholds["retention_30s"]:
        pass_flags.append("retention_30s_below_baseline")

    return {
        "channel_type": channel_type,
        "decision": decision,
        "flags": pass_flags,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m lib.qa_gate <metrics_json_path>", file=sys.stderr)
        return 1

    metrics_path = Path(sys.argv[1])
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))

    try:
        result = evaluate_metrics(payload["metrics"], payload["channel_type"])
        emit_run_log(
            stage="qa_gate",
            status="success",
            input_refs={"metrics_path": str(metrics_path)},
            output_refs=result,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        emit_run_log(
            stage="qa_gate",
            status="failure",
            input_refs={"metrics_path": str(metrics_path)},
            error_summary=str(exc),
        )
        print(f"QA gate failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
