"""Operational enforcement checks for policy decision -> action closure."""

from __future__ import annotations

from typing import Any, Dict, List


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def evaluate_decision_action_closure(
    decision: Dict[str, Any],
    executed_actions: List[str] | None = None,
    action_artifacts: List[Dict[str, Any]] | None = None,
    observed_operations: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Return machine-evaluable enforcement status for a policy decision."""

    executed = set(str(a) for a in _safe_list(executed_actions))
    required_actions = [
        str(a)
        for a in _safe_list(decision.get("mandatory_actions"))
        if str(a) != "PROMOTION_ALLOWED"
    ]

    explain = decision.get("explain", {}) if isinstance(decision, dict) else {}
    machine = explain.get("machine", {}) if isinstance(explain, dict) else {}
    override_status = machine.get("override_status", {}) if isinstance(machine, dict) else {}
    override_applied = bool(override_status.get("applied"))
    override_valid = bool(override_status.get("valid"))

    missing_required_actions = sorted(set(required_actions) - executed)

    closure_ok = bool(not missing_required_actions or (override_applied and override_valid))

    policy_hash = (
        decision.get("provenance", {}).get("decision_hash")
        if isinstance(decision.get("provenance"), dict)
        else None
    )

    artifacts = _safe_list(action_artifacts)
    linked = 0
    for artifact in artifacts:
        if isinstance(artifact, dict) and artifact.get("decision_hash") == policy_hash:
            linked += 1
    linkage_coverage = (linked / len(artifacts)) if artifacts else (1.0 if policy_hash else 0.0)

    observed = _safe_list(observed_operations)
    out_of_band = 0
    for event in observed:
        if not isinstance(event, dict):
            out_of_band += 1
            continue
        if event.get("decision_hash") != policy_hash and not event.get("override_ref"):
            out_of_band += 1

    promotion_during_hold = 0
    phase_hold = bool(decision.get("phase_hold"))
    for event in observed:
        if isinstance(event, dict) and event.get("operation") == "PROMOTION_EXECUTED" and phase_hold:
            promotion_during_hold += 1

    decision_without_action = int((len(required_actions) > 0) and not closure_ok)

    return {
        "decision_action_closure_rate": 1.0 if closure_ok else 0.0,
        "decision_without_action_rate": float(decision_without_action),
        "promotion_during_hold_count": promotion_during_hold,
        "override_audit_violation_rate": float(
            int(bool(override_status.get("present")) and not override_valid)
        ),
        "out_of_band_action_count": out_of_band,
        "provenance_linkage_coverage": linkage_coverage,
        "missing_required_actions": missing_required_actions,
        "closure_ok": closure_ok,
    }
