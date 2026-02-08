"""YouTube upload utilities using OAuth2 credentials."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from .run_logger import build_metrics, emit_run_log


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def _load_metadata(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_description(metadata: Dict[str, Any]) -> str:
    description = metadata.get("description", "")
    chapters: List[Dict[str, str]] = metadata.get("chapters", [])
    if chapters:
        chapter_lines = ["", "Chapters:"]
        chapter_lines.extend(
            f"{chapter.get('timecode', '00:00')} {chapter.get('title', '').strip()}"
            for chapter in chapters
        )
        description = "\n".join([description.strip(), *chapter_lines]).strip()
    return description


def build_youtube_client() -> Any:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    if not client_id or not client_secret or not refresh_token:
        raise ValueError("Missing Google OAuth environment variables.")

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=credentials)


def upload_video(
    *,
    metadata: Dict[str, Any],
    video_path: Path,
    privacy_status: str = "private",
    notify_subscribers: bool = False,
) -> Dict[str, Any]:
    youtube = build_youtube_client()

    request_body = {
        "snippet": {
            "title": metadata.get("title", ""),
            "description": _build_description(metadata),
            "tags": metadata.get("tags", []),
            "categoryId": metadata.get("category_id", "27"),
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": metadata.get("made_for_kids", False),
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media,
        notifySubscribers=notify_subscribers,
    )

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = request.execute()
            return {
                "video_id": response.get("id"),
                "status": privacy_status,
                "notify_subscribers": notify_subscribers,
            }
        except HttpError as exc:
            last_error = exc
            if exc.resp.status in {429, 500, 502, 503, 504} and attempt == 0:
                time.sleep(2)
                continue
            raise
        except Exception as exc:
            last_error = exc
            raise
    raise RuntimeError(f"Upload failed after retries: {last_error}")


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Usage: python -m lib.youtube_uploader <metadata_json> <video_path>",
            file=sys.stderr,
        )
        return 1

    metadata_path = Path(sys.argv[1])
    video_path = Path(sys.argv[2])

    try:
        metadata = _load_metadata(metadata_path)
        result = upload_video(metadata=metadata, video_path=video_path)
        emit_run_log(
            stage="upload",
            status="success",
            input_refs={"metadata": str(metadata_path), "video_path": str(video_path)},
            output_refs=result,
            metrics=build_metrics(cache_hit=False),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        emit_run_log(
            stage="upload",
            status="failure",
            input_refs={"metadata": str(metadata_path), "video_path": str(video_path)},
            error_summary=str(exc),
            metrics=build_metrics(cache_hit=False),
        )
        print(f"Upload failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
