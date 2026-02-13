"""Generate machine-readable phase-state explanation from KPI input."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.policy_enforcement import check_phase_state


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/phase_state_report.py <input_metrics.json>", file=sys.stderr)
        return 1

    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    decision = check_phase_state(payload)

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
