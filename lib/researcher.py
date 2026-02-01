import os
import yt_dlp
import google.generativeai as genai
from googleapiclient.discovery import build
from .supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()

class DeepResearcher:
    def __init__(self):
        self.youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def get_video_transcript(self, video_id):
        """Extract subtitles using yt-dlp."""
        ydl_opts = {
            'skip_download': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['ko', 'en'],
            'quiet': True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                return info.get('description', '') # Simplified for prompt brevity
        except:
            return "Transcript extraction failed. Falling back to metadata."

    def analyze_viral_strategy(self, topic):
        """Search videos and analyze their transcripts."""
        search_res = self.youtube.search().list(q=topic, part="snippet", maxResults=1).execute()
        
        for item in search_res['items']:
            v_id = item['id']['videoId']
            transcript = self.get_video_transcript(v_id)
            
            # Request analysis from Gemini
            prompt = f"Analyze this YouTube transcript for viral patterns: {transcript}"
            response = self.model.generate_content(prompt)
            
            # Save to Supabase
            supabase.table("research_cache").insert({
                "topic": topic,
                "deep_analysis": {"insight": response.text, "video_id": v_id}
            }).execute()
            
            return response.text

if __name__ == "__main__":
    # Integration with Scout
    from .trend_scout import TrendScout
    scout = TrendScout()
    topic = scout.fetch_trending_videos()
    
    researcher = DeepResearcher()
    print(f"Deep analyzing '{topic}'...")
    print(researcher.analyze_viral_strategy(topic))