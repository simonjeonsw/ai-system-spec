"""Contract CI guard checks for M2/M3 policy stabilization."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE_FILE = ROOT / "lib" / "pipeline_runner.py"
DELETED_LEGACY = ROOT / "lib" / "scene_contract_builder.py"

BANNED_TOKENS = {
    "scene_contract_builder",
    "build_scene_contract",
    "_separate_scene_image_motion_contracts",
}


def _assert_legacy_removed() -> None:
    if DELETED_LEGACY.exists():
        raise SystemExit(f"Legacy file still exists: {DELETED_LEGACY}")


def _assert_no_banned_tokens() -> None:
    for path in ROOT.rglob("*.py"):
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8")
        for token in BANNED_TOKENS:
            if token in text:
                raise SystemExit(f"Banned legacy token '{token}' found in {path}")


def _assert_metadata_schema_hardening() -> None:
    schema_path = ROOT / "spec" / "schemas" / "metadata_output.schema.json"
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    if payload.get("additionalProperties") is not False:
        raise SystemExit("metadata_output schema must set additionalProperties=false")


def _assert_validation_includes_metadata_stage() -> None:
    source = (ROOT / "lib" / "validation_runner.py").read_text(encoding="utf-8")
    if '"metadata": "metadata_output"' not in source:
        raise SystemExit("validation_runner missing metadata_output stage mapping")




def _assert_policy_config_contract() -> None:
    policy_path = ROOT / "config" / "geo_phase_policy.json"
    if not policy_path.exists():
        raise SystemExit("Missing policy config: config/geo_phase_policy.json")
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    required_paths = [
        ("policy_version",),
        ("geo_readiness", "escalation", "yellow", "min_weekly_warning_count"),
        ("geo_readiness", "escalation", "red", "min_weekly_warning_count"),
        ("phase_b_transition", "minimum_published_videos"),
        ("phase_b_transition", "source_evidence", "minimum_linkage_pass_rate"),
        ("decision_enforcement", "require_action_or_signed_override"),
        ("decision_enforcement", "unknown_reason_code_action"),
        ("decision_enforcement", "reason_code_actions", "decision_hold_pending_info"),
    ]
    for path in required_paths:
        cursor = payload
        for key in path:
            if key not in cursor:
                raise SystemExit(f"Missing policy key: {'/'.join(path)}")
            cursor = cursor[key]


def _assert_phase_b_c_not_activated() -> None:
    metadata_schema = json.loads((ROOT / "spec" / "schemas" / "metadata_output.schema.json").read_text(encoding="utf-8"))
    props = metadata_schema.get("properties", {})
    banned_active_keys = {"faq_snippets", "key_claims_for_ai", "canonical_source_urls"}
    activated = sorted(k for k in banned_active_keys if k in props)
    if activated:
        raise SystemExit(f"Phase B/C fields must not be active in metadata_output.schema.json: {activated}")


def _assert_draft_contract_files_exist() -> None:
    required = [
        ROOT / "spec" / "schemas" / "metadata_output.phase_b.draft.schema.json",
        ROOT / "spec" / "schemas" / "metadata_output.phase_c.draft.schema.json",
        ROOT / "spec" / "schemas" / "source_evidence_contract.schema.json",
        ROOT / "spec" / "schemas" / "phase_state_input.schema.json",
    ]
    for path in required:
        if not path.exists():
            raise SystemExit(f"Missing required draft/contract file: {path}")

def _assert_pipeline_uses_canonical_handoff() -> None:
    source = PIPELINE_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    required = {"build_structure_only_scenes", "build_image_contract", "build_motion_contract"}
    missing = sorted(required - names)
    if missing:
        raise SystemExit(f"Canonical handoff symbols missing in pipeline_runner: {missing}")


if __name__ == "__main__":
    _assert_legacy_removed()
    _assert_no_banned_tokens()
    _assert_pipeline_uses_canonical_handoff()
    _assert_validation_includes_metadata_stage()
    _assert_metadata_schema_hardening()
    _assert_policy_config_contract()
    _assert_phase_b_c_not_activated()
    _assert_draft_contract_files_exist()
    print("contract ci checks passed")
