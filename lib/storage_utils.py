"""Storage helpers for local JSON backups and video ID normalization."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def normalize_video_id(value: str) -> str:
    match = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11})", value)
    return match.group(1) if match else value.strip()


def save_json(stage: str, video_id: str, payload: Dict[str, Any]) -> Path:
    ensure_data_dir()
    path = DATA_DIR / f"{stage}_{video_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
