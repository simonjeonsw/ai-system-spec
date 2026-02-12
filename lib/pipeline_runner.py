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
from .ops import log_experiment
from .scene_contract_builder import build_scene_contract
from .image_builder import build_image_contract
from .motion_builder import build_motion_contract


SCENE_ENGINE_VERSION = "2.0"
_CAMERA_ANGLES = [
    "wide shot of a bank vault",
    "close-up of a coin",
    "isometric top-down financial dashboard view",
    "over-the-shoulder view of a ledger",
    "medium shot of host with infographic wall",
    "macro shot of currency notes and calculator",
]
_STAGE_MARKER_PATTERN = re.compile(r"\[(?:scene|visual|narration)\s*:[^\]]*\]|\[(?:scene|visual|narration)\]", re.IGNORECASE)
_PART_MARKER_PATTERN = re.compile(r"---\s*PART\s*\d+\s*:[^-]+---", re.IGNORECASE)
_SECTION_HEADER_PATTERN = re.compile(r"---\s*CONCLUSION\s*---", re.IGNORECASE)
_DIRECTIVE_PREFIX_PATTERN = re.compile(r"^(opening shot|title card|graph|animation|overlay|host appears|secondary graph|chart|infographic)\s*:", re.IGNORECASE)
_SCREENPLAY_CUE_PATTERN = re.compile(r"\*{0,2}\[\d{1,2}:\d{2}\]\*{0,2}", re.IGNORECASE)
_SCENE_BOUNDARY_PATTERN = re.compile(r"\[\s*SCENE\s+(?:START|END)\s*\]", re.IGNORECASE)
_SLUGLINE_PATTERN = re.compile(r"\b(?:INT|EXT)\.[^\n]{0,120}?\b(?:DAY|NIGHT)\b\s*[:\-]*", re.IGNORECASE)
_CLAIM_TOKEN_STOPWORDS = {
    "that",
    "with",
    "this",
    "from",
    "into",
    "about",
    "there",
    "their",
    "have",
    "were",
    "been",
    "while",
    "which",
}
_VISUAL_CUE_KEYWORDS = [
    ("inflation", "Animated purchasing-power erosion chart with shrinking currency icons."),
    ("tax", "Policy dashboard showing tax flow and household net-income impact."),
    ("wage", "Split graph comparing wage trend vs cost-of-living trajectory."),
    ("productivity", "Diverging line chart: productivity growth vs worker compensation."),
    ("debt", "Household debt stack visualization with interest snowball effect."),
    ("regulation", "Regulatory flowchart showing compliance friction on small businesses."),
    ("policy", "Government policy lever infographic tied to household outcomes."),
]
_VISUAL_CUE_FALLBACKS = [
    "Host-led explainer shot with contextual economic infographic wall.",
    "Top-down dashboard montage of cashflow, savings, and spending metrics.",
    "Clean whiteboard-style chart sequence highlighting cause-and-effect economics.",
    "Isometric city economy map illustrating households, firms, and policy channels.",
]
_VISUAL_CUE_VARIANTS = [
    "Use icon-driven composition with concise labels.",
    "Use split-screen comparison with directional arrows.",
    "Use chart-led composition with callout annotations.",
    "Use storyboard sequence showing cause → effect → takeaway.",
]



def _parse_payload(text: str) -> Dict[str, Any]:
    if not text:
        raise ValueError("Empty payload from stage output.")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return extract_json_relaxed(text)


def _normalize_script_text(script_payload: Dict[str, Any]) -> str:
    def _collect_script_lines(node: Any, lines: list[str]) -> None:
        if isinstance(node, str):
            text = node.strip()
            if text:
                lines.append(text)
            return
        if isinstance(node, list):
            for item in node:
                _collect_script_lines(item, lines)
            return
        if not isinstance(node, dict):
            return

        title = str(node.get("title", "")).strip()
        if title:
            lines.append(title)

        visuals = node.get("visuals")
        if isinstance(visuals, list):
            for visual in visuals:
                visual_text = str(visual).strip()
                if visual_text:
                    lines.append(f"[Visual] {visual_text}")

        narration_value = node.get("narration")
        if isinstance(narration_value, list):
            for sentence in narration_value:
                sentence_text = str(sentence).strip()
                if sentence_text:
                    lines.append(f"[Narration] {sentence_text}")
        elif isinstance(narration_value, str):
            sentence_text = narration_value.strip()
            if sentence_text:
                lines.append(f"[Narration] {sentence_text}")

        text_value = node.get("text")
        if isinstance(text_value, list):
            for sentence in text_value:
                sentence_text = str(sentence).strip()
                if sentence_text:
                    lines.append(f"[Narration] {sentence_text}")
        elif isinstance(text_value, str):
            sentence_text = text_value.strip()
            if sentence_text:
                lines.append(f"[Narration] {sentence_text}")

        # recurse nested dict/list values conservatively
        for key, value in node.items():
            if key in {"title", "visuals", "narration", "text"}:
                continue
            if isinstance(value, (dict, list)):
                _collect_script_lines(value, lines)

    script_text = script_payload.get("script", "")
    if isinstance(script_text, str):
        stripped = script_text.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
            try:
                parsed = json.loads(stripped)
                script_payload["script"] = parsed
                script_text = parsed
            except Exception:
                pass
    if isinstance(script_text, list):
        lines: list[str] = []
        _collect_script_lines(script_text, lines)
        if lines:
            return "\n".join(lines).strip()
        return "\n".join(str(item) for item in script_text).strip()
    if isinstance(script_text, dict):
        lines: list[str] = []
        _collect_script_lines(script_text, lines)
        if lines:
            return "\n".join(lines).strip()
        sections = script_text.get("sections", [])
        lines = []
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
    def _is_overlay_candidate(token: str) -> bool:
        normalized = token.strip()
        if not normalized:
            return False
        if re.search(r"src-\d+", normalized, flags=re.IGNORECASE):
            return False
        if len(normalized) > 32:
            return False
        if re.match(r"^0{2,}$", normalized):
            return False
        if re.match(r"^0\d{2,}$", normalized):
            return False
        if re.match(r"^\d{1,2}:\d{2}$", normalized):
            return False
        if re.match(r"^\d{1,3}$", normalized) and not any(sym in normalized for sym in {"%", "$", "€", "¥", "₩"}):
            return False
        return True

    overlays: list[str] = []
    narration_cleaned = re.sub(r"src-\d+", " ", narration_text, flags=re.IGNORECASE)
    narration_cleaned = re.sub(r"\[\s*\d{1,2}:\d{2}\s*\]", " ", narration_cleaned)
    narration_candidates = re.findall(r"(?:\$\s?\d[\d,]*(?:\.\d+)?|\d+(?:\.\d+)?%|\d[\d,]*(?:\.\d+)?)", narration_cleaned)
    for token in narration_candidates:
        token = token.strip()
        if _is_overlay_candidate(token) and token not in overlays:
            overlays.append(token)
        if len(overlays) >= limit:
            return overlays

    data_points = research_payload.get("data_points", [])
    for point in data_points:
        value = str(point.get("value", "")).strip()
        match = re.search(r"(?:\$\s?\d[\d,]*(?:\.\d+)?|\d+(?:\.\d+)?%)", value)
        candidate = match.group(0).strip() if match else value
        if _is_overlay_candidate(candidate) and candidate not in overlays:
            overlays.append(candidate)
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
    return f"{style_prompt}. {base}. minimalist professional finance aesthetic.".strip()


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
    if len(visual_blocks) == 1:
        single = visual_blocks[0]
        beats = _split_text_into_beats(str(single.get("narration", "")), max_words=38)
        single_word_count = len(str(single.get("narration", "")).split())
        if len(beats) >= 2 and single_word_count >= 80:
            visual_blocks = [
                {
                    "visual": str(single.get("visual", "")),
                    "narration": beat,
                    "section_type": "body",
                }
                for beat in beats
            ]

    scenes = []
    recent_overlays: list[str] = []
    style_key = _load_visual_style_config().get("active_style", "isometric_3d")
    source_hash = _scene_hash(script_payload, "scene-structure")
    for index, block in enumerate(visual_blocks, start=1):
        camera = _CAMERA_ANGLES[(index - 1) % len(_CAMERA_ANGLES)]
        overlay_text = _pick_overlay_text(str(block.get("narration", "")), research_payload, recent_overlays)
        if overlay_text:
            recent_overlays.append(overlay_text)
        visual_cue = str(block.get("visual", "")).strip() or _infer_visual_cue_from_narration(str(block.get("narration", "")), index)
        base_prompt = _build_image_prompt_with_context(visual_cue, research_payload)
        enriched_prompt = f"{base_prompt} Camera angle: {camera}."
        if overlay_text:
            enriched_prompt += f" Overlay text: '{overlay_text}'."
        scenes.append(
            {
                "scene_id": f"s{index:02d}",
                "objective": "Derived from validated script visual cue.",
                "visual_cue": visual_cue,
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


def _infer_visual_cue_from_narration(narration_text: str, index: int) -> str:
    lowered = narration_text.lower()
    for keyword, cue in _VISUAL_CUE_KEYWORDS:
        if keyword in lowered:
            variant = _VISUAL_CUE_VARIANTS[(index - 1) % len(_VISUAL_CUE_VARIANTS)]
            return f"{cue} {variant}".strip()
    fallback = _VISUAL_CUE_FALLBACKS[(index - 1) % len(_VISUAL_CUE_FALLBACKS)]
    variant = _VISUAL_CUE_VARIANTS[(index - 1) % len(_VISUAL_CUE_VARIANTS)]
    return f"{fallback} {variant}".strip()


def _log_metadata_conversion_experiments(video_id: str, metadata_payload: Dict[str, Any]) -> None:
    pinned_variants = metadata_payload.get("pinned_comment_variants") or []
    if isinstance(pinned_variants, list) and len(pinned_variants) >= 2:
        for idx, variant in enumerate(pinned_variants[:2], start=1):
            log_experiment(
                {
                    "video_id": video_id,
                    "experiment_type": "pinned_comment_conversion",
                    "title_variant": metadata_payload.get("title"),
                    "thumbnail_variant": f"comment_v{idx}",
                    "start_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "notes": f"Pinned comment conversion variant {idx}: {str(variant)[:160]}",
                }
            )


def _estimate_runtime_seconds_from_script(script_payload: Dict[str, Any]) -> int:
    script_text = _normalize_script_text(script_payload)
    words = len(script_text.split())
    return int((words / 230) * 60)


def _strip_stage_artifacts(text: str) -> str:
    cleaned = _STAGE_MARKER_PATTERN.sub(" ", text or "")
    cleaned = _PART_MARKER_PATTERN.sub(" ", cleaned)
    cleaned = _SECTION_HEADER_PATTERN.sub(" ", cleaned)
    cleaned = _SCENE_BOUNDARY_PATTERN.sub(" ", cleaned)
    cleaned = _SCREENPLAY_CUE_PATTERN.sub(" ", cleaned)
    cleaned = _SLUGLINE_PATTERN.sub(" ", cleaned)
    cleaned = re.sub(r"\*{1,3}", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _extract_scene_source_ids(text: str, source_ids: set[str]) -> list[str]:
    found = {token.lower() for token in re.findall(r"src-\d+", text or "", flags=re.IGNORECASE)}
    return sorted(src for src in found if src in source_ids)


def _is_high_risk_scene_claim(text: str) -> bool:
    return bool(
        re.search(
            r"\b(inflation|wage|productivity|tax|debt|interest|central bank|policy|regulation|inequality|gdp|cpi|recession)\b",
            text,
            re.IGNORECASE,
        )
        or re.search(r"\d", text)
    )


def _infer_scene_sources(
    narration_text: str,
    research_payload: Dict[str, Any],
    fallback_citations: list[str],
    allowed_source_ids: set[str],
) -> list[str]:
    source_scores: Dict[str, float] = {}
    lowered = narration_text.lower()

    def _add_score(source_id: str, delta: float) -> None:
        sid = source_id.lower()
        if sid not in allowed_source_ids:
            return
        source_scores[sid] = source_scores.get(sid, 0.0) + delta

    for entry in research_payload.get("key_fact_sources", []):
        claim = str(entry.get("claim", "")).lower()
        if not claim:
            continue
        claim_tokens = [token for token in re.findall(r"[a-zA-Z]{4,}", claim) if token not in _CLAIM_TOKEN_STOPWORDS]
        overlap = sum(1 for token in claim_tokens[:8] if token in lowered)
        if overlap >= 3:
            for source_id in entry.get("source_ids", []):
                _add_score(str(source_id), overlap * 1.0)

    for point in research_payload.get("data_points", []):
        metric = str(point.get("metric", "")).lower()
        source_id = str(point.get("source_id", "")).lower()
        metric_tokens = [tok for tok in re.findall(r"[a-zA-Z]{3,}", metric) if tok not in _CLAIM_TOKEN_STOPWORDS]
        metric_overlap = sum(1 for tok in metric_tokens[:4] if tok in lowered)
        if metric_overlap >= 2:
            _add_score(source_id, metric_overlap * 0.8)

        value = str(point.get("value", "")).strip()
        if value and value in narration_text:
            _add_score(source_id, 1.4)

    sorted_by_score = sorted(source_scores.items(), key=lambda item: item[1], reverse=True)
    inferred = [sid for sid, score in sorted_by_score if score >= 1.6][:2]

    if inferred:
        return inferred

    explicit = _extract_scene_source_ids(narration_text, allowed_source_ids)
    if explicit:
        return explicit[:2]

    for source_id in fallback_citations:
        sid = str(source_id).lower()
        if sid in allowed_source_ids:
            return [sid]
    return []


def _pick_overlay_text(
    narration_text: str,
    research_payload: Dict[str, Any],
    used_recently: list[str],
    window: int = 3,
) -> str:
    candidates = _extract_numeric_overlays(research_payload, narration_text, limit=5)
    if not candidates:
        return ""
    recent = set(item for item in used_recently[-window:] if item)
    for candidate in candidates:
        if candidate and candidate not in recent:
            return candidate
    for candidate in candidates:
        if candidate != (used_recently[-1] if used_recently else None):
            return candidate
    return ""


def _normalize_claim_text(text: str) -> str:
    cleaned = _strip_stage_artifacts(text)
    cleaned = cleaned.replace('\\"', '"').strip()
    cleaned = re.sub(r"^(?:\*{0,2}[A-Z0-9][A-Z0-9\s&'\-\.]{5,}:\s*)+", "", cleaned)
    cleaned = re.sub(r'^["“”\']+|["“”\']+$', '', cleaned)
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
    cleaned = re.sub(r"([.!?])\s*:", r"\1", cleaned)
    cleaned = re.sub(r"([.!?]){2,}", r"\1", cleaned)
    cleaned = re.sub(r'"\.$', '.', cleaned)
    cleaned = re.sub(r'\.$"', '.', cleaned)
    cleaned = re.sub(r"^[\s:;,.\-–—]+", "", cleaned)
    return cleaned.strip()


def _sentence_claims_from_text(text: str, max_claims: int = 2) -> list[str]:
    cleaned = _normalize_claim_text(text)
    if not cleaned:
        return []
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", cleaned) if item.strip()]
    claims: list[str] = []
    for sentence in sentences:
        if len(sentence) < 20 or _DIRECTIVE_PREFIX_PATTERN.match(sentence):
            continue
        if re.match(r"^(?:\[[^\]]+\]|\*+|[A-Z\s]{6,}:?)$", sentence.strip()):
            continue
        sentence = _normalize_claim_text(sentence)
        if sentence and sentence[-1] not in ".?!":
            sentence = sentence.rstrip() + "."
        if sentence:
            claims.append(sentence)
        if len(claims) >= max_claims:
            break
    if not claims and cleaned and not _DIRECTIVE_PREFIX_PATTERN.match(cleaned):
        fallback = cleaned if cleaned.endswith((".", "?", "!")) else f"{cleaned}."
        claims.append(fallback)
    return claims


def _split_text_into_beats(text: str, max_words: int = 42) -> list[str]:
    cleaned = _strip_stage_artifacts(text)
    if not cleaned:
        return []
    sentences = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+", cleaned) if chunk.strip()]
    beats: list[str] = []
    bucket: list[str] = []
    word_count = 0
    for sentence in sentences:
        words = sentence.split()
        if len(words) > max_words * 2:
            if bucket:
                beats.append(" ".join(bucket).strip())
                bucket = []
                word_count = 0
            for start in range(0, len(words), max_words):
                chunk = " ".join(words[start : start + max_words]).strip()
                if chunk:
                    beats.append(chunk)
            continue
        if bucket and word_count + len(words) > max_words:
            beats.append(" ".join(bucket).strip())
            bucket = []
            word_count = 0
        bucket.append(sentence)
        word_count += len(words)
    if bucket:
        beats.append(" ".join(bucket).strip())
    return beats


def _extract_section_beats(script_payload: Dict[str, Any]) -> list[Dict[str, str]]:
    script = script_payload.get("script")
    if isinstance(script, str):
        stripped = script.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
            try:
                script = json.loads(stripped)
            except json.JSONDecodeError:
                script = script_payload.get("script")
    beats: list[Dict[str, str]] = []
    if isinstance(script, dict):
        sections = script.get("sections", [])
        if isinstance(sections, list):
            for idx, section in enumerate(sections, start=1):
                section_title = str(section.get("title", "")).strip() or f"section-{idx}"
                visual = str(section.get("visual", "")).strip()
                narration = section.get("narration", "")
                if isinstance(narration, list):
                    narration_text = " ".join(str(item).strip() for item in narration if str(item).strip())
                else:
                    narration_text = str(narration).strip()
                for beat_index, beat_text in enumerate(_split_text_into_beats(narration_text), start=1):
                    beats.append(
                        {
                            "title": section_title,
                            "visual": visual,
                            "narration": beat_text,
                            "beat_id": f"{idx}-{beat_index}",
                        }
                    )
    if beats:
        return beats

    blocks = _extract_visual_blocks(_normalize_script_text(script_payload))
    for idx, block in enumerate(blocks, start=1):
        for beat_index, beat_text in enumerate(_split_text_into_beats(str(block.get("narration", ""))), start=1):
            beats.append(
                {
                    "title": f"block-{idx}",
                    "visual": str(block.get("visual", "")),
                    "narration": beat_text,
                    "beat_id": f"{idx}-{beat_index}",
                }
            )
    return beats


def _ensure_scene_granularity(
    scene_output: Dict[str, Any],
    script_payload: Dict[str, Any],
    research_payload: Dict[str, Any],
    min_scenes: int = 10,
) -> Dict[str, Any]:
    scenes = list(scene_output.get("scenes", []))
    runtime_sec = _estimate_runtime_seconds_from_script(script_payload)
    target_scenes = max(min_scenes, min(24, int(runtime_sec / 28)))

    if runtime_sec <= 300 or len(scenes) >= target_scenes:
        return scene_output

    beats = _extract_section_beats(script_payload)
    if not beats:
        return scene_output

    style_profile = _load_visual_style_config().get("active_style", "isometric_3d")
    source_hash = _scene_hash(script_payload, "scene-structure")
    expanded: list[Dict[str, Any]] = []
    recent_overlays: list[str] = []

    for idx, beat in enumerate(beats, start=1):
        camera = _CAMERA_ANGLES[(idx - 1) % len(_CAMERA_ANGLES)]
        overlay_text = _pick_overlay_text(str(beat.get("narration", "")), research_payload, recent_overlays)
        if overlay_text:
            recent_overlays.append(overlay_text)
        prompt = _build_image_prompt_with_context(beat.get("visual", ""), research_payload)
        prompt = f"{prompt} Camera angle: {camera}."
        if overlay_text:
            prompt += f" Overlay text: '{overlay_text}'."

        expanded.append(
            {
                "scene_id": f"s{idx:02d}",
                "objective": f"Deliver beat {beat.get('beat_id', idx)} from section '{beat.get('title', 'section')}'.",
                "visual_cue": beat.get("visual", ""),
                "key_claims": _sentence_claims_from_text(beat.get("narration", ""), max_claims=2),
                "source_refs": [],
                "evidence_sources": [],
                "visual_prompt": prompt,
                "narration_prompt": beat.get("narration", ""),
                "transition_note": "Advance to the next semantic beat while preserving narrative continuity.",
                "camera_angle": camera,
                "overlay_text": overlay_text,
                "style_profile": style_profile,
                "scene_engine_version": SCENE_ENGINE_VERSION,
                "source_script_hash": source_hash,
                "schema_version": "1.0",
            }
        )

    source_ids = {
        str(source.get("source_id", "")).lower()
        for source in research_payload.get("sources", [])
        if source.get("source_id")
    }
    fallback_citations = [str(item).lower() for item in script_payload.get("citations", []) if str(item).lower().startswith("src-")]
    for scene in expanded:
        narration_text = _normalize_claim_text(str(scene.get("narration_prompt", "")))
        scene["narration_prompt"] = narration_text
        mapped_sources = _extract_scene_source_ids(narration_text, source_ids)
        claims = scene.get("key_claims") or _sentence_claims_from_text(narration_text, max_claims=1)
        claims = [_normalize_claim_text(claim) for claim in claims if _normalize_claim_text(claim)]
        scene["key_claims"] = claims
        if not mapped_sources and any(_is_high_risk_scene_claim(claim) for claim in claims):
            mapped_sources = _infer_scene_sources(narration_text, research_payload, fallback_citations, source_ids)
        scene["evidence_sources"] = mapped_sources
        scene["source_refs"] = [{"claim": claim, "sources": mapped_sources} for claim in claims if mapped_sources]
        if scene.get("scene_id") == "s22":
            override = (
                " Include a line graph icon with diverging lines labeled 'Productivity' and 'Wages', "
                "and annotate that the gap widens over time."
            )
            scene["visual_prompt"] = f"{scene.get('visual_prompt', '').strip()}{override}".strip()

    while len(expanded) < target_scenes and expanded:
        candidate_index = max(range(len(expanded)), key=lambda i: len(str(expanded[i].get("narration_prompt", "")).split()))
        candidate = expanded[candidate_index]
        narration_text = str(candidate.get("narration_prompt", ""))
        words = narration_text.split()
        if len(words) < 14:
            new_idx = len(expanded) + 1
            camera = _CAMERA_ANGLES[(new_idx - 1) % len(_CAMERA_ANGLES)]
            fallback_overlay = _pick_overlay_text(narration_text, research_payload, recent_overlays)
            if fallback_overlay:
                recent_overlays.append(fallback_overlay)
            continued_narration = narration_text or "Continue this key idea with a concrete example and practical action."
            continued_prompt = _build_image_prompt_with_context(str(candidate.get("visual_cue", "")), research_payload)
            continued_prompt = f"{continued_prompt} Camera angle: {camera}."
            if fallback_overlay:
                continued_prompt += f" Overlay text: '{fallback_overlay}'."
            expanded.append(
                {
                    **candidate,
                    "scene_id": f"s{new_idx:02d}",
                    "objective": f"{candidate.get('objective', 'Scene')} (continued)",
                    "transition_note": "Keep narrative continuity with a concise reinforcement beat.",
                    "camera_angle": camera,
                    "overlay_text": fallback_overlay,
                    "visual_prompt": continued_prompt,
                    "narration_prompt": continued_narration,
                    "key_claims": _sentence_claims_from_text(continued_narration, max_claims=1),
                }
            )
            continue
        pivot = len(words) // 2
        left_text = " ".join(words[:pivot]).strip()
        right_text = " ".join(words[pivot:]).strip()
        candidate["narration_prompt"] = left_text
        candidate["key_claims"] = _sentence_claims_from_text(left_text, max_claims=1)
        candidate["objective"] = f"{candidate.get('objective', 'Scene')} (part 1)"
        candidate["transition_note"] = "Continue to the next sub-beat for deeper explanation."
        new_idx = len(expanded) + 1
        expanded.insert(
            candidate_index + 1,
            {
                **candidate,
                "scene_id": f"s{new_idx:02d}",
                "narration_prompt": right_text,
                "key_claims": _sentence_claims_from_text(right_text, max_claims=1),
                "objective": f"{candidate.get('objective', 'Scene')} (part 2)",
                "transition_note": "Resolve this sub-beat and move forward.",
            },
        )

    for scene in expanded:
        narration_text = _normalize_claim_text(str(scene.get("narration_prompt", "")))
        scene["narration_prompt"] = narration_text
        mapped_sources = _extract_scene_source_ids(narration_text, source_ids)
        claims = scene.get("key_claims") or _sentence_claims_from_text(narration_text, max_claims=1)
        claims = [_normalize_claim_text(claim) for claim in claims if _normalize_claim_text(claim)]
        scene["key_claims"] = claims
        if not mapped_sources and any(_is_high_risk_scene_claim(claim) for claim in claims):
            mapped_sources = _infer_scene_sources(narration_text, research_payload, fallback_citations, source_ids)
        scene["evidence_sources"] = mapped_sources
        scene["source_refs"] = [{"claim": claim, "sources": mapped_sources} for claim in claims if mapped_sources]

    scene_output["scenes"] = expanded
    return scene_output


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
    lines = ["# Scene Structure", ""]
    lines.append("| Scene ID | Start (sec) | End (sec) | Objective | Script Refs | Transition |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for scene in scene_output.get("scenes", []):
        refs = ", ".join(scene.get("script_refs", []))
        lines.append(
            f"| {scene.get('scene_id', '')} | {scene.get('start_sec', '')} | {scene.get('end_sec', '')} | {scene.get('objective', '')} | {refs} | {scene.get('transition_note', '')} |"
        )
    lines.append("")
    lines.append("## Scene Summary")
    lines.append(f"- Total scenes: {len(scene_output.get('scenes', []))}")
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
    expected_hash = _scene_hash(script_payload, "scene-structure")
    cached_hash = str(cached_scene.get("source_script_hash", ""))
    cached_version = str(cached_scene.get("scene_engine_version", ""))
    runtime_sec = _estimate_runtime_seconds_from_script(script_payload)
    cached_scene_count = len(cached_scene.get("scenes", []))
    granularity_mismatch = runtime_sec > 300 and cached_scene_count < 10
    return (
        cached_hash != expected_hash
        or cached_version != SCENE_ENGINE_VERSION
        or granularity_mismatch
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
    "image": "image_output",
    "motion": "motion_output",
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
            elif stage == "image":
                images = payload.get("images", [])
                if not images:
                    print(f"⚠️ Invalid image payload for {stage}. Regenerating.")
                    path.unlink(missing_ok=True)
                    return None
                try:
                    for image in images:
                        validate_payload(schema_name, image)
                except Exception:
                    print(f"⚠️ Schema validation failed for {stage}. Regenerating.")
                    path.unlink(missing_ok=True)
                    return None
            elif stage == "motion":
                motions = payload.get("motions", [])
                if not motions:
                    print(f"⚠️ Invalid motion payload for {stage}. Regenerating.")
                    path.unlink(missing_ok=True)
                    return None
                try:
                    for motion in motions:
                        validate_payload(schema_name, motion)
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

    validation_report = None
    state: Dict[str, Any] = {}

    def _checkpoint_state() -> None:
        if state.get("research"):
            save_json("research", video_id, state["research"])
        if state.get("plan"):
            save_json("plan", video_id, state["plan"])
        if state.get("scenes"):
            save_json("scenes", video_id, state["scenes"])
        if state.get("image"):
            save_json("image", video_id, state["image"])
        if state.get("motion"):
            save_json("motion", video_id, state["motion"])
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
            plan_result, _ = _run_stage(
                stage="planner",
                run_id=run_id,
                input_refs={"video_id": video_id},
                action=lambda: planner.create_project_plan(video_id),
            )
            if isinstance(plan_result, str) and plan_result.startswith("❌"):
                raise ValueError(plan_result)
            if not isinstance(plan_result, dict):
                raise TypeError(
                    "Planner stage must return a dictionary payload. "
                    f"Got type={type(plan_result).__name__}"
                )
            plan_payload = plan_result
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
        validation_report = {
            "status": verification_result.status,
            "errors": verification_result.errors,
            "sentence_map": verification_result.sentence_map,
            "coverage": verification_result.coverage,
            "semantic": verification_result.semantic,
        }
        emit_run_log(
            stage="validator",
            status="success" if verification_result.status == "pass" else "failure",
            input_refs={"video_id": video_id, "root_run_id": run_id},
            output_refs={"validation_report": validation_report},
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
            validation_report = {
                "status": verification_result.status,
                "errors": verification_result.errors,
                "sentence_map": verification_result.sentence_map,
                "coverage": verification_result.coverage,
                "semantic": verification_result.semantic,
            }
            emit_run_log(
                stage="validator",
                status="success" if verification_result.status == "pass" else "failure",
                input_refs={
                    "video_id": video_id,
                    "retry": "validator_feedback",
                    "root_run_id": run_id,
                },
                output_refs={"validation_report": validation_report},
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
            raw_scene_output = cached_scene
        else:
            raw_scene_output = _build_scene_output_from_script(script_payload, research_payload)
            raw_scene_output["scene_engine_version"] = SCENE_ENGINE_VERSION
            raw_scene_output["source_script_hash"] = _scene_hash(script_payload, "scene-structure")
            raw_scene_output = _ensure_scene_granularity(raw_scene_output, script_payload, research_payload, min_scenes=10)

        scene_output, scene_contexts = build_scene_contract(raw_scene_output)
        image_output = build_image_contract(scene_contexts)
        motion_output = build_motion_contract(image_output)
        save_json("scenes", video_id, scene_output)
        save_json("image", video_id, image_output)
        save_json("motion", video_id, motion_output)
        save_markdown("scenes", video_id, _render_scenes_markdown(scene_output))
        state["scenes"] = scene_output
        state["image"] = image_output
        state["motion"] = motion_output
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

        semantic_result = validator.semantic_consistency_check(
            metadata_payload=metadata_payload,
            scene_output=scene_output,
        )
        if semantic_result["status"] != "pass":
            emit_run_log(
                stage="semantic_validator",
                status="failure",
                input_refs={"video_id": video_id, "root_run_id": run_id},
                output_refs={"semantic_errors": semantic_result["errors"]},
                metrics=build_metrics(cache_hit=False),
                run_id=_log_run_id(run_id, "semantic_validator", 1),
            )
            raise ValueError("; ".join(semantic_result["errors"][:3]))

        if validation_report is None:
            validation_report = {"status": "pass", "errors": [], "sentence_map": [], "coverage": {}, "semantic": {}}
        validation_report["semantic"] = semantic_result

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
        try:
            _log_metadata_conversion_experiments(video_id, metadata_payload)
        except Exception as experiment_exc:
            emit_run_log(
                stage="ops",
                status="warning",
                input_refs={"video_id": video_id, "root_run_id": run_id},
                output_refs={"note": "metadata conversion experiment logging skipped"},
                error_summary=str(experiment_exc),
                metrics=build_metrics(cache_hit=False),
                run_id=_log_run_id(run_id, "ops", 1),
            )
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
        "image": image_output,
        "motion": motion_output,
        "script_long": script_payload,
        "script_shorts": shorts_payload,
        "validation_report": validation_report,
        "verification_report": validation_report,
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
        print("Artifacts: data/{video_id}_{research|plan|script|script_long|script_shorts|scenes|image|motion|metadata}.{json|md}")
    save_json("validation_report", result["video_id"], result.get("validation_report") or {"status": "n/a", "errors": [], "sentence_map": []})
    save_json("verification_report", result["video_id"], result.get("validation_report") or {"status": "n/a", "errors": [], "sentence_map": []})
    manifest_path = Path(__file__).resolve().parent.parent / "data" / f"{result['video_id']}_pipeline.json"
    manifest = {
        "video_id": result["video_id"],
        "files": {
            "research": f"data/{result['video_id']}_research.json",
            "plan": f"data/{result['video_id']}_plan.json",
            "scenes": f"data/{result['video_id']}_scenes.json",
            "image": f"data/{result['video_id']}_image.json",
            "motion": f"data/{result['video_id']}_motion.json",
            "script": f"data/{result['video_id']}_script.json",
            "metadata": f"data/{result['video_id']}_metadata.json",
            "validation_report": f"data/{result['video_id']}_validation_report.json",
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
