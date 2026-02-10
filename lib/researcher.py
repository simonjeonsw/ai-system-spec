import json
import os
import re
import sys
from pathlib import Path

import yt_dlp
from dotenv import load_dotenv

from .json_utils import ensure_schema_version, extract_json
from .model_router import ModelRouter
from .run_logger import build_metrics, emit_run_log
from .schema_validator import validate_payload
from .storage_utils import normalize_video_id, save_json, save_raw
from .supabase_client import supabase
from .trend_scout import TrendScout

# Keep virtual environment path if used locally.
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

load_dotenv()


class VideoResearcher:
    def __init__(self):
        self.router = ModelRouter.from_env()
        self.fast_model = "gemini-2.5-flash"
        self.main_model = "gemini-2.5-flash"
        self.heavy_model = "gemini-2.5-flash-lite"

    def _is_general_knowledge(self, claim: str) -> bool:
        generic_patterns = [
            r"\b(is|refers to|means|defined as|concept|principle|overview)\b",
            r"\b(in general|typically|commonly|basically)\b",
        ]
        return any(re.search(pattern, claim, re.IGNORECASE) for pattern in generic_patterns)

    def _is_high_risk_claim(self, claim: str) -> bool:
        has_numeric = bool(re.search(r"\d", claim))
        high_impact_keywords = bool(
            re.search(
                r"\b(cpi|inflation|interest rate|unemployment|gdp|yield|returns?|probability|forecast|policy|regulation|tax)\b",
                claim,
                re.IGNORECASE,
            )
        )
        return has_numeric or high_impact_keywords

    def _validate_source_governance(self, payload: dict) -> list[str]:
        """Return warnings (relaxed mode) while still enforcing obvious risk boundaries.

        Policy:
        - General-knowledge claims may pass without explicit sources.
        - Non-general claims should have at least 1 source.
        - High-risk claims should preferably have 2+ distinct sources.
        - Claims should include at least one tier_1/tier_2 source when available.
        """
        sources = {item.get("source_id"): item for item in payload.get("sources", [])}
        key_fact_sources = payload.get("key_fact_sources", [])
        warnings: list[str] = []

        missing_sources = []
        weak_corroboration = []
        non_tier12_claims = []

        for entry in key_fact_sources:
            claim = str(entry.get("claim", "")).strip()
            source_ids = [sid for sid in entry.get("source_ids", []) if sid]
            unique_ids = list(dict.fromkeys(source_ids))
            is_general = self._is_general_knowledge(claim)
            is_high_risk = self._is_high_risk_claim(claim)

            if not unique_ids and not is_general:
                missing_sources.append(claim)
                continue

            tiers = [
                sources.get(source_id, {}).get("source_tier")
                for source_id in unique_ids
                if sources.get(source_id)
            ]

            # Relaxed corroboration:
            # - high-risk: recommend >=2 sources
            # - normal claims: 1 source is enough
            if is_high_risk and len(unique_ids) < 2 and not is_general:
                weak_corroboration.append(claim)

            if unique_ids and not is_general and not any(tier in {"tier_1", "tier_2"} for tier in tiers):
                non_tier12_claims.append(claim)

        if missing_sources:
            warnings.append(f"missing_sources={missing_sources}")
        if weak_corroboration:
            warnings.append(f"weak_corroboration={weak_corroboration}")
        if non_tier12_claims:
            warnings.append(f"non_tier12_claims={non_tier12_claims}")
        return warnings

    def get_video_transcript(self, video_id):
        """Fetch metadata and comments for analysis."""
        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "get_comments": True,
            "max_comments": 30,
            "extract_flat": False,
        }
        js_runtime = os.getenv("YTDLP_JS_RUNTIME")
        if js_runtime:
            ydl_opts["js_runtimes"] = [js_runtime]
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                url = f"https://www.youtube.com/watch?v={video_id}" if len(video_id) == 11 else video_id
                info = ydl.extract_info(url, download=False)

                content = f"Title: {info.get('title')}\n"
                content += f"Description: {info.get('description')}\n"
                content += f"Tags: {info.get('tags', [])}\n"

                comments = info.get("comments", [])
                comment_text = "\n".join([f"- {c.get('text')}" for c in comments])
                content += f"\n[Viewer Reactions]\n{comment_text}"

                return content
        except Exception as e:
            return f"Error: {str(e)}"

    def analyze_viral_strategy(self, topic, force_update=False):
        """
        force_update=True: always re-run analysis.
        force_update=False: reuse cached data when available.
        """
        normalized_topic = normalize_video_id(topic)

        if not force_update:
            cached = supabase.table("research_cache").select("*").eq("topic", normalized_topic).execute()
            if cached.data:
                cached_content = cached.data[0].get("content")
                if cached_content:
                    print(f"💡 Loaded cached research: {topic}")
                    emit_run_log(
                        stage="research",
                        status="success",
                        input_refs={"topic": topic},
                        output_refs={"cache": "hit"},
                        metrics=build_metrics(cache_hit=True),
                    )
                    try:
                        cached_payload = json.loads(cached_content)
                        save_json("research", normalized_topic, cached_payload)
                    except json.JSONDecodeError:
                        pass
                    return cached_content

        print(f"🚀 [NEW/REFRESH] Starting research analysis: {normalized_topic}")
        transcript_text = self.get_video_transcript(normalized_topic)

        selected_model = self.main_model
        if len(transcript_text) > 8000:
            selected_model = self.heavy_model

        print(f"📡 Model in use: {selected_model}")

        prompt_text = (
            "You are the Research agent. Return JSON only that matches this schema:\n"
            "{\n"
            '  "executive_summary": "...",\n'
            '  "key_facts": ["..."],\n'
            '  "key_fact_sources": [{"claim": "...", "source_ids": ["src-001"]}],\n'
            '  "data_points": [{"metric": "...", "value": "...", "timeframe": "...", "source_id": "src-001"}],\n'
            '  "sources": [{"source_id": "src-001", "title": "...", "url": "...", "as_of_date": "YYYY-MM-DD", "source_tier": "tier_1|tier_2|tier_3", "freshness_window_days": 180}],\n'
            '  "contrarian_angle": "...",\n'
            '  "viewer_takeaway": "...",\n'
            '  "schema_version": "1.0"\n'
            "}\n"
            "\n"
            "Constraints:\n"
            "- Output English only.\n"
            "- Use real, verifiable sources.\n"
            "- General-knowledge claims may use lighter citation density, but factual/high-risk claims need explicit source_ids.\n"
            "\n"
            f"Topic: {normalized_topic}\n\n"
            f"Video transcript and comments:\n{transcript_text}\n"
        )

        analysis_result = ""
        try:
            analysis_result = self.router.generate_content(prompt_text, preferred_models=[selected_model])
        except Exception as e:
            if "429" in str(e):
                print("⚠️ Quota exceeded. Retrying with model rotation.")
                analysis_result = self.router.generate_content(prompt_text, preferred_models=[selected_model])
            else:
                emit_run_log(
                    stage="research",
                    status="failure",
                    input_refs={"topic": normalized_topic},
                    error_summary=str(e),
                    metrics=build_metrics(cache_hit=False),
                )
                raise e

        research_payload = None
        if analysis_result:
            save_raw("research_raw", normalized_topic, analysis_result)
            try:
                research_payload = extract_json(analysis_result)
                ensure_schema_version(research_payload, "1.0")
                save_json("research", normalized_topic, research_payload)
                validation_error = None
                try:
                    validate_payload("research_output", research_payload)
                except Exception as exc:
                    validation_error = str(exc)
                    print(f"⚠️ Research schema validation warning: {validation_error}")
                governance_warnings = self._validate_source_governance(research_payload)
                if governance_warnings:
                    print(f"⚠️ Source governance warning: {', '.join(governance_warnings)}")

                if not validation_error:
                    supabase.table("research_cache").upsert(
                        {
                            "topic": normalized_topic,
                            "content": json.dumps(research_payload, ensure_ascii=False),
                            "raw_transcript": transcript_text,
                            "updated_at": "now()",
                        },
                        on_conflict="topic",
                    ).execute()
                    print("✅ Research cache updated.")
            except Exception as e:
                print(f"⚠️ Failed to parse research data: {e}")

        emit_run_log(
            stage="research",
            status="success",
            input_refs={"topic": normalized_topic},
            output_refs={"cache": "updated" if analysis_result else "skipped"},
            metrics=build_metrics(cache_hit=False),
        )
        if research_payload:
            return json.dumps(research_payload, ensure_ascii=False, indent=2)
        return analysis_result


if __name__ == "__main__":
    scout = TrendScout()
    researcher = VideoResearcher()

    trends = scout.fetch_trending_videos()

    if isinstance(trends, list):
        for i, trend_item in enumerate(trends, 1):
            print(f"{i}. {trend_item}")
    else:
        print(trends)

    print("\n" + "=" * 50)
    print("👉 Enter a number (1-10) or paste a YouTube URL:")
    user_input = input("👉 Input: ").strip()

    target_id = ""
    if isinstance(trends, list) and user_input.isdigit() and 1 <= int(user_input) <= len(trends):
        selected_text = trends[int(user_input) - 1]
        target_id = selected_text.split(" (Views:")[0]
    else:
        target_id = normalize_video_id(user_input)

    cached = supabase.table("research_cache").select("*").eq("topic", target_id).execute()
    force_refresh = False
    if cached.data and cached.data[0].get("content"):
        choice = input("Existing data found. Use cached data or force a refresh? (y/n): ").strip().lower()
        force_refresh = choice == "n"

    print(f"\n🚀 Running research: {target_id}...")
    result = researcher.analyze_viral_strategy(target_id, force_update=force_refresh)
    print("\n" + "=" * 50)
    print(result)
