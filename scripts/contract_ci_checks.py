"""Contract CI guard checks for M2 stabilization."""

from __future__ import annotations

import ast
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


def _assert_validation_includes_metadata_stage() -> None:
    source = (ROOT / "lib" / "validation_runner.py").read_text(encoding="utf-8")
    if '"metadata": "metadata_output"' not in source:
        raise SystemExit("validation_runner missing metadata_output stage mapping")


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
    print("contract ci checks passed")
