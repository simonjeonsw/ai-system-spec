"""Generate machine-readable phase-state explanation from KPI input."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.policy_engine import PhaseEvaluationInput, evaluate_phase_state
from lib.policy_enforcement import evaluate_decision_action_closure


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/phase_state_report.py <input_metrics.json>", file=sys.stderr)
        return 1

    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    data = PhaseEvaluationInput(
        published_videos=payload["published_videos"],
        ctr_weekly=payload["ctr_weekly"],
        avd_weekly=payload["avd_weekly"],
        geo_readiness_warning_count_weekly=payload["geo_readiness_warning_count_weekly"],
        source_contract_ready=payload["source_contract_ready"],
        source_linkage_pass_rate=payload["source_linkage_pass_rate"],
        research_source_coverage=payload["research_source_coverage"],
        incident_open=payload.get("incident_open", False),
        override_record=payload.get("override_record"),
    )
    decision = evaluate_phase_state(data, historical_outcomes=payload.get("historical_outcomes"))

    decision["operational_enforcement"] = evaluate_decision_action_closure(
        decision,
        executed_actions=payload.get("executed_actions"),
        action_artifacts=payload.get("action_artifacts"),
        observed_operations=payload.get("observed_operations"),
    )

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
