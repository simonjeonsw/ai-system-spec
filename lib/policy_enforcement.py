"""Operational enforcement checks for policy decision -> action closure."""

from __future__ import annotations

from datetime import datetime, timezone
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


def evaluate_calibration_label_staleness(
    historical_outcomes: List[Dict[str, Any]] | None,
    *,
    max_age_days: int = 7,
    reference_time: datetime | None = None,
) -> Dict[str, Any]:
    """Evaluate label freshness for policy calibration governance."""

    outcomes = _safe_list(historical_outcomes)
    now = reference_time or datetime.now(timezone.utc)

    stale = 0
    missing_timestamp = 0
    fresh = 0
    oldest_age_days = 0.0

    for item in outcomes:
        if not isinstance(item, dict):
            missing_timestamp += 1
            stale += 1
            continue

        raw_ts = item.get("labeled_at")
        if not raw_ts:
            missing_timestamp += 1
            stale += 1
            continue

        try:
            labeled_at = datetime.fromisoformat(str(raw_ts))
        except ValueError:
            missing_timestamp += 1
            stale += 1
            continue

        if labeled_at.tzinfo is None:
            labeled_at = labeled_at.replace(tzinfo=timezone.utc)

        age_days = max((now - labeled_at).total_seconds() / 86400.0, 0.0)
        oldest_age_days = max(oldest_age_days, age_days)

        if age_days > max_age_days:
            stale += 1
        else:
            fresh += 1

    total = len(outcomes)
    stale_rate = (stale / total) if total else 0.0

    return {
        "total_labels": total,
        "fresh_label_count": fresh,
        "stale_label_count": stale,
        "missing_label_timestamp_count": missing_timestamp,
        "stale_label_rate": stale_rate,
        "oldest_label_age_days": oldest_age_days,
        "governance_ok": stale_rate == 0.0,
    }


def check_phase_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run full policy, enforcement, and calibration-governance checks."""

    from lib.policy_engine import PhaseEvaluationInput, evaluate_phase_state

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
    decision["calibration_governance"] = evaluate_calibration_label_staleness(
        payload.get("historical_outcomes")
    )
    return decision
