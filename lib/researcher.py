import json
import os
import sys
from pathlib import Path

# Keep virtual environment path if used locally.
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from google.genai import Client
from .supabase_client import supabase
from .trend_scout import TrendScout
from .json_utils import ensure_schema_version, extract_json
from .run_logger import build_metrics, emit_run_log
from .schema_validator import validate_payload
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

class VideoResearcher:
    def __init__(self):
        self.client = Client(api_key=os.getenv("GEMINI_API_KEY"))
        # Available model mapping.
        self.fast_model = "gemini-2.0-flash"
        self.main_model = "gemini-2.0-flash"
        self.heavy_model = "gemini-2.5-flash"

    def get_video_transcript(self, video_id):
        """Fetch metadata and comments for analysis."""
        ydl_opts = {
            'skip_download': True, 
            'quiet': True,
            'get_comments': True, 
            'max_comments': 30,  # Limit for efficiency
            'extract_flat': False
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                url = f"https://www.youtube.com/watch?v={video_id}" if len(video_id) == 11 else video_id
                info = ydl.extract_info(url, download=False)
                
                # Build content payload for analysis
                content = f"Title: {info.get('title')}\n"
                content += f"Description: {info.get('description')}\n"
                content += f"Tags: {info.get('tags', [])}\n"
                
                # Append comments for analysis
                comments = info.get('comments', [])
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

        # 1. Cache check
        if not force_update:
            cached = supabase.table("research_cache").select("*").eq("topic", topic).execute()
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
                    return cached_content

        # 2. Collect data and analyze
        print(f"🚀 [NEW/REFRESH] Starting research analysis: {topic}")
        transcript_text = self.get_video_transcript(topic)
        
        # Select model based on content length
        selected_model = self.main_model
        if len(transcript_text) > 8000:
            selected_model = self.heavy_model

        print(f"📡 Model in use: {selected_model}")
        
        # Structured research output (English JSON only)
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
            "- Use real, verifiable sources. If only the video is available, include it as a Tier 3 source and add at least one corroborating Tier 1 or Tier 2 source.\n"
            "\n"
            f"Topic: {topic}\n\n"
            f"Video transcript and comments:\n{transcript_text}\n"
        )

        analysis_result = ""
        try:
            response = self.client.models.generate_content(
                model=selected_model,
                contents=prompt_text
            )
            analysis_result = response.text
        except Exception as e:
            if "429" in str(e):
                fallback = self.heavy_model
                print(f"⚠️ {selected_model} quota exceeded. Switching to {fallback}.")
                response = self.client.models.generate_content(model=fallback, contents=prompt_text)
                analysis_result = response.text
            else:
                emit_run_log(
                    stage="research",
                    status="failure",
                    input_refs={"topic": topic},
                    error_summary=str(e),
                    metrics=build_metrics(cache_hit=False),
                )
                raise e

        # Overwrite existing record when topic matches
        research_payload = None
        if 'analysis_result' in locals() and analysis_result:
            try:
                research_payload = extract_json(analysis_result)
                ensure_schema_version(research_payload, "1.0")
                validate_payload("research_output", research_payload)
                supabase.table("research_cache").upsert({
                    "topic": topic,
                    "content": json.dumps(research_payload, ensure_ascii=False),
                    "raw_transcript": transcript_text,
                    "updated_at": "now()" # Track refresh timestamp
                }, on_conflict='topic').execute()
                print("✅ Research cache updated.")
            except Exception as e:
                print(f"⚠️ Failed to save research data: {e}")

        emit_run_log(
            stage="research",
            status="success",
            input_refs={"topic": topic},
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

    print("\n" + "="*50)
    print("👉 Enter a number (1-10) or paste a YouTube URL:")
    user_input = input("👉 Input: ").strip()

    target_id = ""
    if "v=" in user_input:
        target_id = user_input.split("v=")[1].split("&")[0]
    elif "youtu.be/" in user_input:
        target_id = user_input.split("/")[-1]
    elif user_input.isdigit() and 1 <= int(user_input) <= len(trends):
        selected_text = trends[int(user_input)-1]
        target_id = selected_text.split(" (Views:")[0]
    else:
        target_id = user_input

    print(f"\n🚀 Running research: {target_id}...")
    result = researcher.analyze_viral_strategy(target_id)
    print("\n" + "="*50)
    print(result)
