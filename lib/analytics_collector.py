"""YouTube Analytics collection utilities."""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from typing import Any, Dict, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

from .run_logger import build_metrics, emit_run_log
from .supabase_client import supabase


ANALYTICS_SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def build_analytics_client() -> Any:
    load_dotenv()
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
        scopes=ANALYTICS_SCOPES,
    )
    return build("youtubeAnalytics", "v2", credentials=credentials)


def fetch_video_metrics(
    *,
    video_id: str,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    client = build_analytics_client()
    response = (
        client.reports()
        .query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,impressionsCtr",
            dimensions="video",
            filters=f"video=={video_id}",
        )
        .execute()
    )

    rows = response.get("rows", [])
    if not rows:
        return {
            "video_id": video_id,
            "views": 0,
            "estimated_minutes_watched": 0,
            "average_view_duration": 0,
            "impressions_ctr": None,
        }

    row = rows[0]
    return {
        "video_id": row[0],
        "views": row[1],
        "estimated_minutes_watched": row[2],
        "average_view_duration": row[3],
        "impressions_ctr": row[4] if len(row) > 4 else None,
    }


def store_metrics_snapshot(
    *,
    video_id: str,
    start_date: str,
    end_date: str,
    metrics: Dict[str, Any],
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "video_id": video_id,
        "experiment_type": "analytics_snapshot",
        "start_date": start_date,
        "end_date": end_date,
        "ctr": metrics.get("impressions_ctr"),
        "avd": metrics.get("average_view_duration"),
        "notes": notes,
    }
    supabase.table("metadata_experiments").insert(payload).execute()
    return payload


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python -m lib.analytics_collector <video_id> [start_date] [end_date]",
            file=sys.stderr,
        )
        return 1

    video_id = sys.argv[1].strip()
    today = date.today()
    start_date = sys.argv[2] if len(sys.argv) > 2 else (today - timedelta(days=7)).isoformat()
    end_date = sys.argv[3] if len(sys.argv) > 3 else today.isoformat()

    try:
        metrics = fetch_video_metrics(
            video_id=video_id,
            start_date=start_date,
            end_date=end_date,
        )
        snapshot = store_metrics_snapshot(
            video_id=video_id,
            start_date=start_date,
            end_date=end_date,
            metrics=metrics,
        )
        emit_run_log(
            stage="analytics",
            status="success",
            input_refs={"video_id": video_id, "start_date": start_date, "end_date": end_date},
            output_refs={"metrics": metrics},
            metrics=build_metrics(cache_hit=False),
        )
        print(json.dumps({"metrics": metrics, "snapshot": snapshot}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        emit_run_log(
            stage="analytics",
            status="failure",
            input_refs={"video_id": video_id, "start_date": start_date, "end_date": end_date},
            error_summary=str(exc),
            metrics=build_metrics(cache_hit=False),
        )
        print(f"Analytics collection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
