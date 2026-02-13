"""Deterministic policy evaluator for GEO readiness and phase transitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


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



def load_policy(path: Path = DEFAULT_POLICY_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))



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
        reasons.append("CTR_DATA_INSUFFICIENT")
    else:
        ctr_range = _relative_range(input_data.ctr_weekly[-rules["stability_window_weeks"] :])
        if ctr_range > ctr_cfg["max_relative_range"]:
            promotable = False
            reasons.append("CTR_STABILITY_FAIL")

    if len(input_data.avd_weekly) < avd_cfg["min_data_points"]:
        promotable = False
        reasons.append("AVD_DATA_INSUFFICIENT")
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



def evaluate_phase_state(input_data: PhaseEvaluationInput) -> Dict[str, Any]:
    policy = load_policy()
    geo = evaluate_geo_readiness(input_data, policy)
    transition = evaluate_phase_b_transition(input_data, policy)

    final_hold = geo["phase_hold"] or (not transition["promotable"])

    return {
        "policy_version": policy["policy_version"],
        "current_phase": policy["phase"]["current"],
        "promotion_target": transition["to_phase"],
        "phase_hold": final_hold,
        "geo_readiness": geo,
        "promotion": transition,
        "explain": {
            "can_promote": transition["promotable"] and not geo["phase_hold"],
            "reason_codes": sorted(set(geo["reason_codes"] + transition["reason_codes"])),
            "question": policy["dashboard"]["must_answer"],
        },
    }
