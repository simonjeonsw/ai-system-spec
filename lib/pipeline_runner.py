"""End-to-end pipeline runner for research → metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import signal
import time
import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from .json_utils import extract_json_relaxed, recover_script_payload
from .metadata_generator import generate_metadata
from .planner import ContentPlanner
from .researcher import VideoResearcher
from .scripter import ContentScripter
from .run_logger import build_metrics, emit_run_log
from .storage_utils import normalize_video_id, save_json, load_json, ensure_data_dir, save_markdown
from .supabase_client import supabase
from .schema_validator import validate_payload
from .validation_runner import validate_all
from .validator import ScriptValidator


SCENE_ENGINE_VERSION = "2.0"
_CAMERA_ANGLES = [
    "wide shot of a bank vault",
    "close-up of a coin",
    "isometric top-down financial dashboard view",
    "over-the-shoulder view of a ledger",
    "medium shot of host with infographic wall",
    "macro shot of currency notes and calculator",
]


def _parse_payload(text: str) -> Dict[str, Any]:
    if not text:
        raise ValueError("Empty payload from stage output.")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return extract_json_relaxed(text)


def _normalize_script_text(script_payload: Dict[str, Any]) -> str:
    script_text = script_payload.get("script", "")
    if isinstance(script_text, str):
        stripped = script_text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed = json.loads(stripped)
                script_payload["script"] = parsed
                script_text = parsed
            except Exception:
                pass
    if isinstance(script_text, list):
        return "\n".join(str(item) for item in script_text).strip()
    if isinstance(script_text, dict):
        sections = script_text.get("sections", [])
        lines: list[str] = []
        if isinstance(sections, list) and sections:
            for section in sections:
                visual = str(section.get("visual", "")).strip()
                if visual:
                    lines.append(f"[Visual] {visual}")
                narration = section.get("narration", "")
                if isinstance(narration, list):
                    narration_text = " ".join(str(item).strip() for item in narration if str(item).strip())
                else:
                    narration_text = str(narration).strip()
                if narration_text:
                    lines.append(f"[Narration] {narration_text}")
                lines.append("")
            return "\n".join(lines).strip()
        return json.dumps(script_text, ensure_ascii=False)
    return str(script_text).strip()


def _extract_visual_blocks(script_text: str) -> list[Dict[str, Any]]:
    blocks = []
    current_visual = None
    current_narration: list[str] = []
    for raw_line in script_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        visual_match = re.match(r"^\[(visual)\]\s*(.*)", line, re.IGNORECASE)
        narration_match = re.match(r"^\[(narration)\]\s*(.*)", line, re.IGNORECASE)
        if visual_match:
            if current_visual or current_narration:
                blocks.append(
                    {
                        "visual": current_visual or "",
                        "narration": " ".join(current_narration).strip(),
                        "section_type": "body",
                    }
                )
            current_visual = visual_match.group(2).strip()
            current_narration = []
            continue
        if narration_match:
            current_narration.append(narration_match.group(2).strip())
            continue
        current_narration.append(line)
    if current_visual or current_narration:
        blocks.append(
            {
                "visual": current_visual or "",
                "narration": " ".join(current_narration).strip(),
                "section_type": "body",
            }
        )
    if not blocks:
        blocks.append({"visual": "On-screen host narration.", "narration": script_text[:500].strip(), "section_type": "body"})
    return blocks


def _build_image_prompt(visual_text: str) -> str:
    return _build_image_prompt_with_context(visual_text, {})


def _load_visual_style_config() -> Dict[str, Any]:
    default = {
        "active_style": "isometric_3d",
        "styles": {
            "isometric_3d": (
                "3D isometric view, premium Blender-style rendering, minimalist professional "
                "finance aesthetic, soft clay-like textures, soft studio lighting, clean background, "
                "high resolution, 8k"
            ),
            "cinematic": (
                "high-detail cinematic frame, 16:9, photorealistic lighting, shallow depth of field, "
                "clean composition"
            ),
            "infographic": (
                "clean financial infographic style, vector-like iconography, clear labels, high contrast, "
                "presentation-ready"
            ),
        },
    }
    config_path = Path(__file__).resolve().parent.parent / "config" / "visual_style.json"
    if not config_path.exists():
        return default
    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return default
    active_style = loaded.get("active_style", default["active_style"])
    styles = loaded.get("styles", {})
    merged_styles = {**default["styles"], **styles}
    return {"active_style": active_style, "styles": merged_styles}


def _extract_numeric_overlays(research_payload: Dict[str, Any], narration_text: str = "", limit: int = 3) -> list[str]:
    overlays: list[str] = []
    narration_candidates = re.findall(r"(?:\$\s?\d[\d,]*(?:\.\d+)?|\d+(?:\.\d+)?%|\d[\d,]*(?:\.\d+)?)", narration_text)
    for token in narration_candidates:
        token = token.strip()
        if token and token not in overlays:
            overlays.append(token)
        if len(overlays) >= limit:
            return overlays

    data_points = research_payload.get("data_points", [])
    for point in data_points:
        value = str(point.get("value", "")).strip()
        if value and value not in overlays:
            overlays.append(value)
        if len(overlays) >= limit:
            return overlays

    candidates = research_payload.get("key_facts", [])
    for item in candidates:
        text = str(item)
        if not re.search(r"\d|%|\$|€|¥|₩", text):
            continue
        snippet = text.strip()
        if len(snippet) > 80:
            snippet = snippet[:77].rstrip() + "..."
        overlays.append(snippet)
        if len(overlays) >= limit:
            break
    return overlays


def _build_image_prompt_with_context(visual_text: str, research_payload: Dict[str, Any]) -> str:
    base = visual_text.strip() or "On-screen host narration with supporting visuals."
    style_config = _load_visual_style_config()
    style_key = style_config.get("active_style", "isometric_3d")
    style_prompt = style_config.get("styles", {}).get(style_key, "")
    overlays = _extract_numeric_overlays(research_payload)
    overlay_text = ""
    if overlays:
        overlay_text = " Overlay text: '" + "' | '".join(overlays) + "'."
    return f"{style_prompt}. {base}. minimalist professional finance aesthetic.{overlay_text}".strip()


def _scene_hash(script_payload: Dict[str, Any], style_key: str) -> str:
    base = f"{_normalize_script_text(script_payload)}::{style_key}::{SCENE_ENGINE_VERSION}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _build_scene_output_from_script(
    script_payload: Dict[str, Any],
    research_payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    script_text = _normalize_script_text(script_payload)
    visual_blocks = _extract_visual_blocks(script_text)
    research_payload = research_payload or {}
    scenes = []
    style_key = _load_visual_style_config().get("active_style", "isometric_3d")
    source_hash = _scene_hash(script_payload, style_key)
    for index, block in enumerate(visual_blocks, start=1):
        camera = _CAMERA_ANGLES[(index - 1) % len(_CAMERA_ANGLES)]
        overlays = _extract_numeric_overlays(research_payload, block.get("narration", ""), limit=1)
        overlay_text = overlays[0] if overlays else ""
        base_prompt = _build_image_prompt_with_context(block["visual"], research_payload)
        enriched_prompt = f"{base_prompt} Camera angle: {camera}."
        if overlay_text:
            enriched_prompt += f" Overlay text: '{overlay_text}'."
        scenes.append(
            {
                "scene_id": f"s{index:02d}",
                "objective": "Derived from validated script visual cue.",
                "visual_cue": block["visual"],
                "key_claims": [],
                "source_refs": [],
                "evidence_sources": [],
                "visual_prompt": enriched_prompt,
                "narration_prompt": block["narration"] or "Narration derived from script.",
                "transition_note": "Auto-generated from script sequence.",
                "camera_angle": camera,
                "overlay_text": overlay_text,
                "style_profile": style_key,
                "scene_engine_version": SCENE_ENGINE_VERSION,
                "source_script_hash": source_hash,
                "schema_version": "1.0",
            }
        )
    return {"scenes": scenes}


def _render_research_markdown(research_payload: Dict[str, Any]) -> str:
    key_facts = research_payload.get("key_facts", [])
    key_fact_sources = research_payload.get("key_fact_sources", [])
    sources = research_payload.get("sources", [])
    source_map = {source.get("source_id"): source for source in sources}
    lines = ["# Research Summary", ""]
    summary = research_payload.get("executive_summary", "")
    if summary:
        lines.extend(["## Executive Summary", summary, ""])
    lines.append("## Key Findings")
    lines.append("| # | Claim | Sources |")
    lines.append("| --- | --- | --- |")
    for idx, claim in enumerate(key_facts, start=1):
        source_ids = []
        for entry in key_fact_sources:
            if entry.get("claim") == claim:
                source_ids = entry.get("source_ids", [])
                break
        lines.append(f"| {idx} | {claim} | {', '.join(source_ids)} |")
    lines.append("")
    lines.append("## Sources")
    lines.append("| Source ID | Title | Tier | As of | URL |")
    lines.append("| --- | --- | --- | --- | --- |")
    for source in sources:
        lines.append(
            f"| {source.get('source_id', '')} | {source.get('title', '')} | "
            f"{source.get('source_tier', '')} | {source.get('as_of_date', '')} | "
            f"{source.get('url', '')} |"
        )
    lines.append("")
    lines.append("## Source Quality Notes")
    lines.append("| Source ID | Freshness (days) | Notes |")
    lines.append("| --- | --- | --- |")
    for source_id, source in source_map.items():
        lines.append(
            f"| {source_id} | {source.get('freshness_window_days', '')} | "
            f"{source.get('source_tier', '')} source |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_plan_markdown(plan_payload: Dict[str, Any]) -> str:
    lines = ["# Plan Summary", ""]
    lines.append(f"**Topic:** {plan_payload.get('topic', '')}")
    lines.append(f"**Target Audience:** {plan_payload.get('target_audience', '')}")
    lines.append(f"**Business Goal:** {plan_payload.get('business_goal', '')}")
    lines.append(f"**Monetization Angle:** {plan_payload.get('monetization_angle', '')}")
    lines.append("")
    lines.append("## Retention Hypothesis")
    lines.append(plan_payload.get("retention_hypothesis", ""))
    lines.append("")
    lines.append("## Selection Rationale")
    lines.append(plan_payload.get("selection_rationale", ""))
    lines.append("")
    lines.append("## Topic Candidates")
    lines.append("| Topic | Total Score | Viral Potential | Notes |")
    lines.append("| --- | --- | --- | --- |")
    for candidate in plan_payload.get("topic_candidates", []):
        scores = candidate.get("scores", {})
        lines.append(
            f"| {candidate.get('topic', '')} | {candidate.get('total_score', '')} | "
            f"{scores.get('viral_potential', '')} | {candidate.get('notes', '')} |"
        )
    lines.append("")
    lines.append("## Content Constraints")
    for item in plan_payload.get("content_constraints", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _render_scenes_markdown(scene_output: Dict[str, Any]) -> str:
    lines = ["# Scene Prompts", ""]
    lines.append("| Scene ID | Camera | Overlay | Visual Cue | Image Prompt | Narration |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    overlay_count = 0
    for scene in scene_output.get("scenes", []):
        visual_cue = scene.get("visual_cue", "")
        visual_prompt = scene.get("visual_prompt", "")
        narration = scene.get("narration_prompt", "")
        camera = scene.get("camera_angle", "")
        overlay = scene.get("overlay_text", "")
        if overlay:
            overlay_count += 1
        lines.append(
            f"| {scene.get('scene_id', '')} | {camera} | {overlay} | {visual_cue} | {visual_prompt} | {narration} |"
        )
    lines.append("")
    lines.append("## Scene Summary")
    lines.append(f"- Total scenes: {len(scene_output.get('scenes', []))}")
    lines.append(f"- Scenes with overlays: {overlay_count}")
    lines.append(f"- Scene engine version: {scene_output.get('scene_engine_version', SCENE_ENGINE_VERSION)}")
    lines.append("")
    return "\n".join(lines)


def _render_script_markdown(script_payload: Dict[str, Any], shorts_payload: Dict[str, Any] | None) -> str:
    shorts_script = ""
    if shorts_payload:
        shorts_script = shorts_payload.get("script", "")
    return (
        "# Long-form Script\n\n"
        f"{script_payload.get('script', '')}\n\n"
        "# Shorts Script\n\n"
        f"{shorts_script}\n"
    )


def _canonicalize_research_payload(research_payload: Dict[str, Any]) -> Dict[str, Any]:
    key_facts = research_payload.get("key_facts", [])
    key_fact_sources = research_payload.get("key_fact_sources", [])
    canonical_sources = []
    for idx, claim in enumerate(key_facts, start=1):
        fact_id = f"fact-{idx:03d}"
        matched = next((entry for entry in key_fact_sources if entry.get("claim") == claim), None)
        source_ids = matched.get("source_ids", []) if matched else []
        canonical_sources.append({"fact_id": fact_id, "claim": claim, "source_ids": source_ids})
    if canonical_sources:
        research_payload["key_fact_sources"] = canonical_sources
    return research_payload


def _is_placeholder_script(script_payload: Dict[str, Any]) -> bool:
    text = str(script_payload.get("script", ""))
    placeholder_tokens = ["[OPENING HOOK]", "[MID-REWARD]", "[OPEN LOOP", "[CALL TO ACTION]"]
    return any(token in text for token in placeholder_tokens)


def _should_regenerate_scenes(
    cached_scene: Dict[str, Any] | None,
    script_payload: Dict[str, Any],
) -> bool:
    if not cached_scene:
        return True
    style_key = _load_visual_style_config().get("active_style", "isometric_3d")
    expected_hash = _scene_hash(script_payload, style_key)
    cached_hash = str(cached_scene.get("source_script_hash", ""))
    cached_version = str(cached_scene.get("scene_engine_version", ""))
    cached_style = str(cached_scene.get("style_profile", ""))
    return (
        cached_hash != expected_hash
        or cached_version != SCENE_ENGINE_VERSION
        or cached_style != style_key
    )

def _is_transient_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(token in message for token in ("429", "5xx", "timeout", "resource_exhausted"))

def _log_run_id(root_run_id: str, stage: str, attempt: int) -> str:
    return f"{root_run_id}:{stage}:{attempt}"


def _run_stage(
    *,
    stage: str,
    run_id: str,
    input_refs: Dict[str, Any],
    action: Callable[[], Any],
    max_retries: int = 3,
    base_delay_s: float = 1.0,
) -> Tuple[Any, int]:
    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        start_time = time.monotonic()
        try:
            result = action()
            latency_ms = int((time.monotonic() - start_time) * 1000)
            emit_run_log(
                stage=stage,
                status="success",
                input_refs={**input_refs, "root_run_id": run_id},
                output_refs={"status": "completed"},
                metrics=build_metrics(
                    latency_ms=latency_ms,
                    cache_hit=False,
                    retry_count=attempt - 1,
                ),
                attempts=attempt,
                run_id=_log_run_id(run_id, stage, attempt),
            )
            return result, attempt
        except Exception as exc:
            last_error = exc
            latency_ms = int((time.monotonic() - start_time) * 1000)
            emit_run_log(
                stage=stage,
                status="failure",
                input_refs={**input_refs, "root_run_id": run_id},
                error_summary=str(exc),
                metrics=build_metrics(
                    latency_ms=latency_ms,
                    cache_hit=False,
                    retry_count=attempt - 1,
                ),
                attempts=attempt,
                run_id=_log_run_id(run_id, stage, attempt),
            )
            if not _is_transient_error(exc) or attempt >= max_retries:
                break
            time.sleep(base_delay_s * (2 ** (attempt - 1)))
    raise RuntimeError(f"{stage} failed after {max_retries} attempts") from last_error


_STAGE_SCHEMA = {
    "research": "research_output",
    "plan": "planner_output",
    "scenes": "scene_output",
    "script": "script_output",
    "script_long": "script_output",
    "script_shorts": "script_output",
    "metadata": None,
}


def _load_stage_payload(stage: str, video_id: str) -> Optional[Dict[str, Any]]:
    data_dir = ensure_data_dir()
    path = data_dir / f"{video_id}_{stage}.json"
    if path.exists():
        try:
            payload = load_json(path)
        except json.JSONDecodeError:
            print(f"⚠️ Corrupted JSON detected for {stage}. Regenerating.")
            path.unlink(missing_ok=True)
            return None
        schema_name = _STAGE_SCHEMA.get(stage)
        if schema_name:
            if stage == "scenes":
                scenes = payload.get("scenes", [])
                if not scenes:
                    print(f"⚠️ Invalid scene payload for {stage}. Regenerating.")
                    path.unlink(missing_ok=True)
                    return None
                try:
                    for scene in scenes:
                        validate_payload(schema_name, scene)
                except Exception:
                    print(f"⚠️ Schema validation failed for {stage}. Regenerating.")
                    path.unlink(missing_ok=True)
                    return None
            else:
                try:
                    validate_payload(schema_name, payload)
                except Exception:
                    print(f"⚠️ Schema validation failed for {stage}. Regenerating.")
                    path.unlink(missing_ok=True)
                    return None
        return payload
    return None


def run_pipeline(video_input: str, refresh: bool = False) -> Dict[str, Any]:
    video_id = normalize_video_id(video_input)
    researcher = VideoResearcher()
    planner = ContentPlanner()
    scripter = ContentScripter()
    run_id = emit_run_log(
        stage="orchestrator",
        status="success",
        input_refs={"video_id": video_id},
        output_refs={"status": "started"},
        metrics=build_metrics(cache_hit=False),
    )

    verification_report = None
    state: Dict[str, Any] = {}

    def _checkpoint_state() -> None:
        if state.get("research"):
            save_json("research", video_id, state["research"])
        if state.get("plan"):
            save_json("plan", video_id, state["plan"])
        if state.get("scenes"):
            save_json("scenes", video_id, state["scenes"])
        if state.get("script_long"):
            save_json("script", video_id, state["script_long"])
            save_json("script_long", video_id, state["script_long"])
        if state.get("script_shorts"):
            save_json("script_shorts", video_id, state["script_shorts"])
        if state.get("metadata"):
            save_json("metadata", video_id, state["metadata"])

    def _handle_signal(_signum, _frame) -> None:
        _checkpoint_state()
        raise SystemExit("Graceful shutdown: checkpoints saved.")

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    try:
        script_updated = False
        cached_research = None if refresh else _load_stage_payload("research", video_id)
        if cached_research:
            research_payload = cached_research
            research_payload = _canonicalize_research_payload(research_payload)
            save_markdown("research", video_id, _render_research_markdown(research_payload))
        else:
            research_text, _ = _run_stage(
                stage="research",
                run_id=run_id,
                input_refs={"video_id": video_id, "refresh": refresh},
                action=lambda: researcher.analyze_viral_strategy(video_id, force_update=refresh),
            )
            research_payload = _parse_payload(research_text)
            research_payload = _canonicalize_research_payload(research_payload)
            save_json("research", video_id, research_payload)
            save_markdown("research", video_id, _render_research_markdown(research_payload))
        state["research"] = research_payload

        cached_plan = None if refresh else _load_stage_payload("plan", video_id)
        if cached_plan:
            plan_payload = cached_plan
            save_markdown("plan", video_id, _render_plan_markdown(plan_payload))
        else:
            plan_text, _ = _run_stage(
                stage="planner",
                run_id=run_id,
                input_refs={"video_id": video_id},
                action=lambda: planner.create_project_plan(video_id),
            )
            if plan_text.startswith("❌"):
                raise ValueError(plan_text)
            plan_payload = _parse_payload(plan_text)
            save_json("plan", video_id, plan_payload)
            save_markdown("plan", video_id, _render_plan_markdown(plan_payload))
        state["plan"] = plan_payload

        source_ids = [source.get("source_id") for source in research_payload.get("sources", []) if source.get("source_id")]
        shorts_payload: Dict[str, Any] | None = None
        cached_script = None if refresh else _load_stage_payload("script_long", video_id)
        if cached_script:
            script_payload = cached_script
        else:
            script_text, _ = _run_stage(
                stage="script",
                run_id=run_id,
                input_refs={"video_id": video_id},
                action=lambda: scripter.write_full_script(
                    video_id,
                    source_ids=source_ids,
                    mode="long",
                ),
            )
            if script_text.startswith("❌"):
                raw_path = ensure_data_dir() / f"{video_id}_script_long_raw.json"
                if raw_path.exists():
                    raw_payload = load_json(raw_path)
                    script_text = raw_payload.get("raw_text", script_text)
                else:
                    raise ValueError(script_text)
            try:
                script_payload = _parse_payload(script_text)
            except Exception:
                script_payload = recover_script_payload(script_text)
            if _is_placeholder_script(script_payload):
                raise ValueError("Script generation returned placeholder content for long-form script.")
            script_payload["video_id"] = video_id
            script_payload["mode"] = "long"
            supabase.table("scripts").insert(
                {"content": json.dumps(script_payload, ensure_ascii=False)}
            ).execute()
            save_json("script", video_id, script_payload)
            save_json("script_long", video_id, script_payload)
            script_updated = True
        state["script_long"] = script_payload

        cached_shorts = None if refresh else _load_stage_payload("script_shorts", video_id)
        if cached_shorts:
            shorts_payload = cached_shorts
        else:
            shorts_text, _ = _run_stage(
                stage="script_shorts",
                run_id=run_id,
                input_refs={"video_id": video_id},
                action=lambda: scripter.write_full_script(
                    video_id,
                    source_ids=source_ids,
                    mode="shorts",
                ),
            )
            if shorts_text.startswith("❌"):
                raw_path = ensure_data_dir() / f"{video_id}_script_shorts_raw.json"
                if raw_path.exists():
                    raw_payload = load_json(raw_path)
                    shorts_text = raw_payload.get("raw_text", shorts_text)
                else:
                    raise ValueError(shorts_text)
            try:
                shorts_payload = _parse_payload(shorts_text)
            except Exception:
                shorts_payload = recover_script_payload(shorts_text)
            if _is_placeholder_script(shorts_payload):
                raise ValueError("Script generation returned placeholder content for shorts script.")
            shorts_payload["video_id"] = video_id
            shorts_payload["mode"] = "shorts"
            supabase.table("scripts").insert(
                {"content": json.dumps(shorts_payload, ensure_ascii=False)}
            ).execute()
            save_json("script_shorts", video_id, shorts_payload)
            script_updated = True
        state["script_shorts"] = shorts_payload
        save_markdown("script", video_id, _render_script_markdown(script_payload, shorts_payload))
        supabase.table("video_scripts").upsert(
            {
                "video_id": video_id,
                "long_script": json.dumps(script_payload, ensure_ascii=False),
                "shorts_script": json.dumps(shorts_payload, ensure_ascii=False),
            },
            on_conflict="video_id",
        ).execute()

        validator = ScriptValidator(research_payload, script_payload)
        verification_result = validator.validate()
        verification_report = {
            "status": verification_result.status,
            "errors": verification_result.errors,
            "sentence_map": verification_result.sentence_map,
            "coverage": verification_result.coverage,
        }
        emit_run_log(
            stage="validator",
            status="success" if verification_result.status == "pass" else "failure",
            input_refs={"video_id": video_id, "root_run_id": run_id},
            output_refs={"verification_report": verification_report},
            metrics=build_metrics(cache_hit=False),
            run_id=_log_run_id(run_id, "validator", 1),
        )

        if verification_result.status != "pass":
            feedback = "; ".join(verification_result.errors)
            script_text, _ = _run_stage(
                stage="script_repair",
                run_id=run_id,
                input_refs={"video_id": video_id, "retry": "validator_feedback"},
                action=lambda: scripter.write_full_script_with_feedback(
                    video_id,
                    feedback,
                    source_ids=source_ids,
                    mode="long",
                ),
            )
            if script_text.startswith("❌"):
                raw_path = ensure_data_dir() / f"{video_id}_script_long_raw.json"
                if raw_path.exists():
                    raw_payload = load_json(raw_path)
                    script_text = raw_payload.get("raw_text", script_text)
                else:
                    raise ValueError(script_text)
            try:
                script_payload = _parse_payload(script_text)
            except Exception:
                script_payload = recover_script_payload(script_text)
            if _is_placeholder_script(script_payload):
                raise ValueError("Script repair still returned placeholder content.")
            script_payload["video_id"] = video_id
            script_payload["mode"] = "long"
            supabase.table("scripts").insert(
                {"content": json.dumps(script_payload, ensure_ascii=False)}
            ).execute()
            save_json("script", video_id, script_payload)
            save_json("script_long", video_id, script_payload)
            script_updated = True
            save_markdown("script", video_id, _render_script_markdown(script_payload, shorts_payload))

            validator = ScriptValidator(research_payload, script_payload)
            verification_result = validator.validate()
            verification_report = {
                "status": verification_result.status,
                "errors": verification_result.errors,
                "sentence_map": verification_result.sentence_map,
                "coverage": verification_result.coverage,
            }
            emit_run_log(
                stage="validator",
                status="success" if verification_result.status == "pass" else "failure",
                input_refs={
                    "video_id": video_id,
                    "retry": "validator_feedback",
                    "root_run_id": run_id,
                },
                output_refs={"verification_report": verification_report},
                metrics=build_metrics(cache_hit=False),
                run_id=_log_run_id(run_id, "validator", 2),
            )
            if verification_result.status != "pass":
                emit_run_log(
                    stage="validator",
                    status="warning",
                    input_refs={"video_id": video_id, "root_run_id": run_id},
                    output_refs={"note": "validation failed after auto-repair; proceeding"},
                    metrics=build_metrics(cache_hit=False),
                    run_id=_log_run_id(run_id, "validator", 3),
                )

        cached_scene = None if refresh or script_updated else _load_stage_payload("scenes", video_id)
        if cached_scene and not script_updated and not _should_regenerate_scenes(cached_scene, script_payload):
            scene_output = cached_scene
            save_markdown("scenes", video_id, _render_scenes_markdown(scene_output))
        else:
            scene_output = _build_scene_output_from_script(script_payload, research_payload)
            scene_output["scene_engine_version"] = SCENE_ENGINE_VERSION
            scene_output["style_profile"] = _load_visual_style_config().get("active_style", "isometric_3d")
            scene_output["source_script_hash"] = _scene_hash(script_payload, scene_output["style_profile"])
            save_json("scenes", video_id, scene_output)
            save_markdown("scenes", video_id, _render_scenes_markdown(scene_output))
        state["scenes"] = scene_output
        supabase.table("video_scenes").upsert(
            {
                "video_id": video_id,
                "content": json.dumps(scene_output, ensure_ascii=False),
            },
            on_conflict="video_id",
        ).execute()

        cached_metadata = None if refresh else _load_stage_payload("metadata", video_id)
        if cached_metadata:
            metadata_payload = cached_metadata
        else:
            metadata_payload, _ = _run_stage(
                stage="metadata",
                run_id=run_id,
                input_refs={"video_id": video_id},
                action=lambda: generate_metadata(
                    plan_payload=plan_payload,
                    script_payload=script_payload,
                ),
            )
            save_json("metadata", video_id, metadata_payload)
        state["metadata"] = metadata_payload
        supabase.table("video_metadata").upsert(
            {
                "video_id": video_id,
                "title": metadata_payload.get("title"),
                "description": metadata_payload.get("description"),
                "tags": metadata_payload.get("tags"),
                "chapters": metadata_payload.get("chapters"),
                "pinned_comment": metadata_payload.get("pinned_comment"),
                "thumbnail_variants": metadata_payload.get("thumbnail_variants"),
                "community_post": metadata_payload.get("community_post"),
                "pinned_comment_variants": metadata_payload.get("pinned_comment_variants"),
                "community_post_variants": metadata_payload.get("community_post_variants"),
                "estimated_runtime_sec": metadata_payload.get("estimated_runtime_sec"),
                "speech_rate_wpm": metadata_payload.get("speech_rate_wpm"),
                "schema_version": metadata_payload.get("schema_version"),
            },
            on_conflict="video_id",
        ).execute()
    except Exception as exc:
        _checkpoint_state()
        failure_payload = {
            "video_id": video_id,
            "status": "failed",
        }
        try:
            supabase.table("video_uploads").upsert(
                {
                    **failure_payload,
                    "metadata_path": None,
                    "video_path": None,
                },
                on_conflict="video_id",
            ).execute()
        except Exception as insert_exc:
            if "metadata_path" in str(insert_exc):
                supabase.table("video_uploads").upsert(
                    failure_payload,
                    on_conflict="video_id",
                ).execute()
            else:
                raise
        raise exc

    return {
        "run_id": run_id,
        "video_id": video_id,
        "research": research_payload,
        "plan": plan_payload,
        "scenes": scene_output,
        "script_long": script_payload,
        "script_shorts": shorts_payload,
        "verification_report": verification_report,
        "metadata": metadata_payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full pipeline end-to-end.")
    parser.add_argument("--url", required=True, help="YouTube URL or video ID")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force refresh (ignore cached data)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation_runner all --url after completion",
    )
    parser.add_argument(
        "--video-path",
        help="Optional path to video file to upload after metadata generation",
    )
    parser.add_argument(
        "--privacy-status",
        default="private",
        help="YouTube privacy status (private|unlisted|public)",
    )
    parser.add_argument(
        "--notify-subscribers",
        action="store_true",
        help="Notify subscribers on upload",
    )
    parser.add_argument(
        "--print-result",
        action="store_true",
        help="Print full pipeline JSON result to terminal",
    )
    args = parser.parse_args()

    result = run_pipeline(args.url, refresh=args.refresh)
    if args.print_result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"✅ Pipeline completed: {result['video_id']}")
        print("Artifacts: data/{video_id}_{research|plan|script|script_long|script_shorts|scenes|metadata}.{json|md}")
    save_json("verification_report", result["video_id"], result.get("verification_report") or {"status": "n/a", "errors": [], "sentence_map": []})
    manifest_path = Path(__file__).resolve().parent.parent / "data" / f"{result['video_id']}_pipeline.json"
    manifest = {
        "video_id": result["video_id"],
        "files": {
            "research": f"data/{result['video_id']}_research.json",
            "plan": f"data/{result['video_id']}_plan.json",
            "scenes": f"data/{result['video_id']}_scenes.json",
            "script": f"data/{result['video_id']}_script.json",
            "metadata": f"data/{result['video_id']}_metadata.json",
            "verification_report": f"data/{result['video_id']}_verification_report.json",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.validate:
        validate_all(normalize_video_id(args.url))

    if args.video_path:
        from .ops import publish_video

        metadata_path = Path(__file__).resolve().parent.parent / "data" / f"{result['video_id']}_metadata.json"
        payload = {
            "video_id": result["video_id"],
            "status": "published",
            "metadata_path": str(metadata_path),
            "video_path": args.video_path,
            "privacy_status": args.privacy_status,
            "notify_subscribers": args.notify_subscribers,
        }
        upload_result = publish_video(payload)
        print(json.dumps({"upload": upload_result}, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
