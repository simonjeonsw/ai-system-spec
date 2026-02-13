"""Deterministic policy evaluator for GEO readiness and phase transitions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY_PATH = ROOT / "config" / "geo_phase_policy.json"


@dataclass(frozen=True)
class PhaseEvaluationInput:
    published_videos: int
    ctr_weekly: List[float]
    avd_weekly: List[float]
    geo_readiness_warning_count_weekly: List[int]
    source_contract_ready: bool
    source_linkage_pass_rate: float
    research_source_coverage: float
    incident_open: bool = False
    override_record: Optional[Dict[str, Any]] = None


def load_policy(path: Path = DEFAULT_POLICY_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _sustained_increase_streak(values: List[int]) -> int:
    if len(values) < 2:
        return 0
    streak = 0
    for idx in range(1, len(values)):
        if values[idx] > values[idx - 1]:
            streak += 1
        else:
            streak = 0
    return streak


def _relative_range(values: List[float]) -> float:
    if not values:
        return 1.0
    mean = sum(values) / len(values)
    if mean <= 0:
        return 1.0
    return (max(values) - min(values)) / mean


def _validate_override_record(
    override: Optional[Dict[str, Any]], policy: Dict[str, Any]
) -> Dict[str, Any]:
    enforcement = policy["decision_enforcement"]
    override_policy = enforcement["override"]

    if not override:
        return {
            "present": False,
            "valid": False,
            "applied": False,
            "reason": "NO_OVERRIDE",
        }

    required = override_policy["required_fields"]
    missing = [field for field in required if field not in override or not override[field]]
    if missing:
        return {
            "present": True,
            "valid": False,
            "applied": False,
            "reason": f"MISSING_OVERRIDE_FIELDS:{','.join(sorted(missing))}",
        }

    try:
        created_at = datetime.fromisoformat(override["created_at"])
        expires_at = datetime.fromisoformat(override["expires_at"])
    except ValueError:
        return {
            "present": True,
            "valid": False,
            "applied": False,
            "reason": "INVALID_OVERRIDE_TIMESTAMP",
        }

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= created_at:
        return {
            "present": True,
            "valid": False,
            "applied": False,
            "reason": "INVALID_OVERRIDE_TTL_ORDER",
        }

    ttl_limit = timedelta(hours=override_policy["max_ttl_hours"])
    if expires_at - created_at > ttl_limit:
        return {
            "present": True,
            "valid": False,
            "applied": False,
            "reason": "OVERRIDE_TTL_EXCEEDS_POLICY",
        }

    if _now_utc() > expires_at:
        return {
            "present": True,
            "valid": False,
            "applied": False,
            "reason": "OVERRIDE_EXPIRED",
        }

    if not enforcement["override"]["allowed"]:
        return {
            "present": True,
            "valid": False,
            "applied": False,
            "reason": "OVERRIDE_DISABLED_BY_POLICY",
        }

    return {
        "present": True,
        "valid": True,
        "applied": False,
        "reason": "OVERRIDE_ACCEPTED_FOR_REVIEW",
    }


def evaluate_geo_readiness(
    input_data: PhaseEvaluationInput, policy: Dict[str, Any]
) -> Dict[str, Any]:
    settings = policy["geo_readiness"]
    escalation = settings["escalation"]
    warnings = input_data.geo_readiness_warning_count_weekly
    latest = warnings[-1] if warnings else 0
    streak = _sustained_increase_streak(warnings)

    level = "green"
    reason_codes: List[str] = []

    red = escalation["red"]
    if latest >= red["min_weekly_warning_count"] and streak >= red["sustained_increase_weeks"] - 1:
        level = "red"
        reason_codes.append("GEO_WARN_RED_THRESHOLD")
    else:
        yellow = escalation["yellow"]
        if latest >= yellow["min_weekly_warning_count"] and streak >= yellow["sustained_increase_weeks"] - 1:
            level = "yellow"
            reason_codes.append("GEO_WARN_YELLOW_THRESHOLD")

    incident_rules = settings["incident_rules"]
    incident_required = level in incident_rules["create_incident_on_level"]
    hold = level in incident_rules["auto_hold_on_level"]
    if incident_rules["auto_hold_when_incident_open"] and input_data.incident_open:
        hold = True
        reason_codes.append("OPEN_INCIDENT_HOLD")

    return {
        "level": level,
        "latest_warning_count": latest,
        "sustained_increase_streak": streak,
        "incident_required": incident_required,
        "phase_hold": hold,
        "reason_codes": sorted(set(reason_codes)),
    }


def evaluate_phase_b_transition(
    input_data: PhaseEvaluationInput, policy: Dict[str, Any]
) -> Dict[str, Any]:
    rules = policy["phase_b_transition"]
    reasons: List[str] = []
    promotable = True

    if input_data.published_videos < rules["minimum_published_videos"]:
        promotable = False
        reasons.append("VIDEO_COUNT_BELOW_MINIMUM")
    if input_data.published_videos > rules["maximum_published_videos"]:
        promotable = False
        reasons.append("VIDEO_COUNT_ABOVE_PHASE_B_WINDOW")

    ctr_cfg = rules["ctr"]
    avd_cfg = rules["avd"]

    if len(input_data.ctr_weekly) < ctr_cfg["min_data_points"]:
        promotable = False
        reasons.extend(["CTR_DATA_INSUFFICIENT", "decision_hold_pending_info"])
    else:
        ctr_range = _relative_range(input_data.ctr_weekly[-rules["stability_window_weeks"] :])
        if ctr_range > ctr_cfg["max_relative_range"]:
            promotable = False
            reasons.append("CTR_STABILITY_FAIL")

    if len(input_data.avd_weekly) < avd_cfg["min_data_points"]:
        promotable = False
        reasons.extend(["AVD_DATA_INSUFFICIENT", "decision_hold_pending_info"])
    else:
        avd_range = _relative_range(input_data.avd_weekly[-rules["stability_window_weeks"] :])
        if avd_range > avd_cfg["max_relative_range"]:
            promotable = False
            reasons.append("AVD_STABILITY_FAIL")

    src_cfg = rules["source_evidence"]
    if src_cfg["require_contract_ready"] and not input_data.source_contract_ready:
        promotable = False
        reasons.append("SOURCE_CONTRACT_NOT_READY")
    if input_data.source_linkage_pass_rate < src_cfg["minimum_linkage_pass_rate"]:
        promotable = False
        reasons.append("SOURCE_LINKAGE_PASS_RATE_FAIL")
    if input_data.research_source_coverage < src_cfg["minimum_research_source_coverage"]:
        promotable = False
        reasons.append("RESEARCH_SOURCE_COVERAGE_FAIL")

    if input_data.incident_open:
        promotable = False
        reasons.append("OPEN_INCIDENT_HOLD")

    return {
        "from_phase": rules["from_phase"],
        "to_phase": rules["to_phase"],
        "promotable": promotable,
        "reason_codes": sorted(set(reasons)),
        "exceptions": rules["exceptions"],
        "rollback": rules["rollback"],
    }


def _map_reason_codes_to_actions(reason_codes: List[str], policy: Dict[str, Any]) -> List[str]:
    mapping = policy["decision_enforcement"]["reason_code_actions"]
    unknown = sorted(code for code in reason_codes if code not in mapping)
    if unknown:
        raise ValueError(f"Unknown reason codes for mandatory action mapping: {unknown}")

    return sorted({mapping[code] for code in reason_codes})


def _build_human_summary(can_promote: bool, reason_codes: List[str], actions: List[str]) -> str:
    if can_promote:
        return "Promotion is allowed: all policy checks passed and no hold conditions were triggered."
    reasons = ", ".join(reason_codes) if reason_codes else "UNKNOWN_REASON"
    required_actions = ", ".join(actions) if actions else "NO_ACTION_REGISTERED"
    return (
        "Promotion is blocked or held because policy reason codes were triggered: "
        f"{reasons}. Required actions: {required_actions}."
    )


def _decision_hash(payload: Dict[str, Any]) -> str:
    packed = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def _compute_false_decision_metrics(outcomes: List[Dict[str, Any]]) -> Dict[str, float]:
    total = max(len(outcomes), 1)
    false_hold = sum(1 for item in outcomes if item.get("label") == "false_hold")
    false_promote = sum(1 for item in outcomes if item.get("label") == "false_promote")
    return {
        "false_hold_rate": false_hold / total,
        "false_promote_rate": false_promote / total,
    }


def evaluate_phase_state(
    input_data: PhaseEvaluationInput, historical_outcomes: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    policy = load_policy()
    geo = evaluate_geo_readiness(input_data, policy)
    transition = evaluate_phase_b_transition(input_data, policy)

    all_reason_codes = sorted(set(geo["reason_codes"] + transition["reason_codes"]))

    final_hold = geo["phase_hold"] or (not transition["promotable"])
    can_promote = transition["promotable"] and not geo["phase_hold"]

    override_status = _validate_override_record(input_data.override_record, policy)
    manual_override_allowed = bool(policy["phase_b_transition"]["exceptions"].get("manual_override_allowed"))

    override_applied = False
    if override_status["valid"] and manual_override_allowed:
        override_applied = True
        can_promote = True
        final_hold = False
    elif override_status["present"] and not override_status["valid"]:
        all_reason_codes.extend(["OVERRIDE_REJECTED", "decision_hold_pending_info"])
        can_promote = False
        final_hold = True

    all_reason_codes = sorted(set(all_reason_codes))
    mandatory_actions = _map_reason_codes_to_actions(all_reason_codes, policy) if all_reason_codes else ["PROMOTION_ALLOWED"]

    if policy["decision_enforcement"]["require_action_or_signed_override"]:
        if not mandatory_actions and not (override_status["present"] and override_status["valid"]):
            raise ValueError("Policy decision generated no mandatory actions and no valid signed override.")

    explanation_payload = {
        "policy_version": policy["policy_version"],
        "reason_codes": all_reason_codes,
        "mandatory_actions": mandatory_actions,
        "can_promote": can_promote,
        "phase_hold": final_hold,
        "override_status": {
            **override_status,
            "applied": override_applied,
        },
    }

    provenance = {
        "policy_version": policy["policy_version"],
        "evaluated_at": _now_utc().isoformat(),
        "input_snapshot": {
            "published_videos": input_data.published_videos,
            "ctr_weekly": input_data.ctr_weekly,
            "avd_weekly": input_data.avd_weekly,
            "geo_readiness_warning_count_weekly": input_data.geo_readiness_warning_count_weekly,
            "source_contract_ready": input_data.source_contract_ready,
            "source_linkage_pass_rate": input_data.source_linkage_pass_rate,
            "research_source_coverage": input_data.research_source_coverage,
            "incident_open": input_data.incident_open,
        },
    }
    provenance["decision_hash"] = _decision_hash({**provenance, **explanation_payload})

    metrics = _compute_false_decision_metrics(historical_outcomes or [])

    return {
        "policy_version": policy["policy_version"],
        "current_phase": policy["phase"]["current"],
        "promotion_target": transition["to_phase"],
        "phase_hold": final_hold,
        "incident_required": geo["incident_required"],
        "decision_without_action": int(not bool(mandatory_actions)),
        "promotion_during_hold": int(can_promote and final_hold),
        "override_audit_violations": int(override_status["present"] and not override_status["valid"]),
        "geo_readiness": geo,
        "promotion": transition,
        "mandatory_actions": mandatory_actions,
        "provenance": provenance,
        "explain": {
            "can_promote": can_promote,
            "reason_codes": sorted(set(all_reason_codes)),
            "question": policy["dashboard"]["must_answer"],
            "machine": explanation_payload,
            "human": _build_human_summary(can_promote, all_reason_codes, mandatory_actions),
        },
        "calibration": metrics,
    }
