import os
import sys
import json
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from googleapiclient.discovery import build
import google.generativeai as genai

from lib.supabase_client import get_client

# Load environment variables
load_dotenv()

# YouTube API configuration
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    print("Error: YOUTUBE_API_KEY not found in .env", file=sys.stderr)
    sys.exit(1)

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# Gemini API configuration
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GENAI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env", file=sys.stderr)
    sys.exit(1)

genai.configure(api_key=GENAI_API_KEY)
# Using the default model for text generation
GEMINI_MODEL = genai.GenerativeModel('gemini-pro')

SUPABASE_CLIENT = get_client()
RESEARCH_TOPIC = "youtube_benchmarking"
CATEGORIES = ["Finance", "Economics", "History", "Education"]
MAX_CHANNELS_PER_CATEGORY = 5
MAX_VIDEOS_PER_CHANNEL = 5
DAYS_FOR_GROWTH_ANALYSIS = 30


def get_youtube_service():
    """Builds and returns the YouTube API service."""
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)


def get_top_channels_by_category(youtube, category: str):
    """
    Searches for channels related to a category and attempts to find those with high subscriber growth.
    This is a simplified approach as direct subscriber growth metrics are not easily available via YouTube API search.
    It will prioritize channels with more videos and higher total view counts as a proxy for activity/growth.
    """
    print(f"Searching for top channels in {category}...")
    channels = []
    search_response = youtube.search().list(
        q=category,
        type="channel",
        part="id,snippet",
        maxResults=MAX_CHANNELS_PER_CATEGORY,
    ).execute()

    channel_ids = [item["id"]["channelId"] for item in search_response.get("items", [])]

    if not channel_ids:
        return []

    channels_response = youtube.channels().list(
        part="snippet,statistics",
        id=",".join(channel_ids)
    ).execute()

    for item in channels_response.get("items", []):
        channels.append({
            "id": item["id"],
            "title": item["snippet"]["title"],
            "subscribers": int(item["statistics"].get("subscriberCount", 0)),
            "video_count": int(item["statistics"].get("videoCount", 0)),
            "view_count": int(item["statistics"].get("viewCount", 0)),
            "url": f"https://www.youtube.com/channel/{item['id']}"
        })
    
    # Sort by a combination of subscribers and view count as a proxy for "top performing"
    channels.sort(key=lambda x: (x["subscribers"] * 0.7 + x["view_count"] * 0.3), reverse=True)
    
    return channels


def get_channel_videos(youtube, channel_id: str, max_results=MAX_VIDEOS_PER_CHANNEL):
    """Fetches recent videos from a given channel."""
    print(f"Fetching recent videos for channel {channel_id}...")
    videos = []
    search_response = youtube.search().list(
        channelId=channel_id,
        type="video",
        part="id,snippet",
        order="date", # Most recent videos first
        maxResults=max_results
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]

    if not video_ids:
        return []

    videos_response = youtube.videos().list(
        part="snippet,statistics",
        id=",".join(video_ids)
    ).execute()

    for item in videos_response.get("items", []):
        snippet = item["snippet"]
        statistics = item["statistics"]
        videos.append({
            "id": item["id"],
            "title": snippet["title"],
            "description": snippet.get("description", ""),
            "published_at": snippet["publishedAt"],
            "view_count": int(statistics.get("viewCount", 0)),
            "like_count": int(statistics.get("likeCount", 0)),
            "comment_count": int(statistics.get("commentCount", 0)),
            "thumbnail_url": snippet["thumbnails"]["high"]["url"],
            "url": f"https://www.youtube.com/watch?v={item['id']}"
        })
    return videos


def analyze_video_with_gemini(video_data: dict, channel_subscribers: int):
    """Analyzes video data using the Gemini model."""
    prompt = (
        f"Analyze the following YouTube video data to determine 'Why this video went viral' "
        f"and summarize its 'Winning Hook' or 'Visual Strategy'.\n\n"
        f"Video Title: {video_data['title']}\n"
        f"Video Description: {video_data['description']}\n"
        f"Video URL: {video_data['url']}\n"
        f"View Count: {video_data['view_count']}\n"
        f"Channel Subscribers (approx): {channel_subscribers}\n"
        f"Published At: {video_data['published_at']}\n\n"
        f"Consider the view-to-subscriber ratio ({video_data['view_count'] / channel_subscribers:.2f} if > 0) as a key indicator. "
        f"Focus on the title, description, and implied visual strategy (from title/description) to identify patterns.\n\n"
        f"Provide a concise analysis for 'Why it went viral', and a distinct summary for 'Winning Hook/Visual Strategy'."
    )
    
    try:
        response = GEMINI_MODEL.generate_content(prompt)
        analysis_text = response.text
        
        viral_reason = "N/A"
        winning_strategy = "N/A"

        # Simple parsing for now, could be improved with more robust NLP if needed
        if "Why it went viral:" in analysis_text:
            parts = analysis_text.split("Why it went viral:", 1)
            viral_reason = parts[1].split("Winning Hook/Visual Strategy:", 1)[0].strip()
            if "Winning Hook/Visual Strategy:" in analysis_text:
                winning_strategy = analysis_text.split("Winning Hook/Visual Strategy:", 1)[1].strip()
        elif "Winning Hook/Visual Strategy:" in analysis_text:
             winning_strategy = analysis_text.split("Winning Hook/Visual Strategy:", 1)[1].strip()
        else:
            viral_reason = analysis_text # Fallback if parsing fails

        return {
            "why_viral": viral_reason,
            "winning_hook_visual_strategy": winning_strategy
        }
    except Exception as e:
        print(f"Gemini analysis failed for video {video_data['id']}: {e}", file=sys.stderr)
        return {
            "why_viral": f"Analysis failed: {e}",
            "winning_hook_visual_strategy": f"Analysis failed: {e}"
        }


def store_research_data(data: dict):
    """Stores the research data into the Supabase research_cache."""
    try:
        SUPABASE_CLIENT.table("research_cache").insert(data).execute()
        print(f"Stored data for video {data.get('video_id')} in research_cache.")
    except Exception as e:
        print(f"Error storing data to Supabase: {e}", file=sys.stderr)


def main() -> int:
    youtube = get_youtube_service()

    for category in CATEGORIES:
        print(f"Starting research for category: {category}")
        channels = get_top_channels_by_category(youtube, category)
        
        for channel in channels:
            print(f"Processing channel: {channel['title']} ({channel['id']})")
            videos = get_channel_videos(youtube, channel['id'])

            for video in videos:
                print(f"Analyzing video: {video['title']} ({video['id']})")
                
                # Calculate view-to-subscriber ratio
                view_to_sub_ratio = 0
                if channel['subscribers'] > 0:
                    view_to_sub_ratio = video['view_count'] / channel['subscribers']

                # Simulate thumbnail keyword extraction from title/description
                thumbnail_keywords = list(set(video['title'].lower().split() + video['description'].lower().split()))
                
                gemini_analysis = analyze_video_with_gemini(video, channel['subscribers'])

                research_data = {
                    "topic": RESEARCH_TOPIC,
                    "category": category,
                    "channel_id": channel['id'],
                    "channel_title": channel['title'],
                    "channel_subscribers": channel['subscribers'],
                    "video_id": video['id'],
                    "video_title": video['title'],
                    "video_description": video['description'],
                    "video_url": video['url'],
                    "view_count": video['view_count'],
                    "view_to_subscriber_ratio": view_to_sub_ratio,
                    "thumbnail_keywords": json.dumps(thumbnail_keywords), # Store as JSON string
                    "why_viral": gemini_analysis["why_viral"],
                    "winning_hook_visual_strategy": gemini_analysis["winning_hook_visual_strategy"],
                    "published_at": video['published_at']
                }
                store_research_data(research_data)
            time.sleep(1) # Small delay to avoid hitting API limits quickly

    print("YouTube algorithm analysis complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
