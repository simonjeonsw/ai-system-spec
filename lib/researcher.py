import os
import yt_dlp
import google.generativeai as genai
from googleapiclient.discovery import build
from .supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()

# API Keys
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class YouTubeResearcher:
    def __init__(self):
        self.youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    def get_transcript(self, video_id):
        """yt-dlp를 사용하여 자막(스크립트) 추출"""
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'skip_download': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['ko', 'en'],
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # 자막 데이터 확인 로직 (간소화)
                return f"Video Title: {info.get('title')}\nDescription: {info.get('description')[:500]}"
        except Exception as e:
            return f"Transcript unavailable: {str(e)}"

    def analyze_with_gemini(self, transcript_data):
        """제미나이를 이용한 흥행 공식 분석"""
        prompt = f"""
        Analyze the following YouTube video content and provide a deep analysis for creators:
        1. Intro Hook: How did the video start to grab attention?
        2. Retention Strategy: How did it keep viewers engaged in the middle?
        3. Call to Action: How did it encourage subscribers or likes?
        
        Content Data:
        {transcript_data}
        
        Return the result in Korean.
        """
        response = model.generate_content(prompt)
        return response.text

    def search_and_analyze(self, query, max_results=3):
        search_response = self.youtube.search().list(
            q=query, part="snippet", maxResults=max_results, type="video", order="viewCount"
        ).execute()

        results = []
        for item in search_response['items']:
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            
            print(f"Analyzing: {title}...")
            raw_data = self.get_transcript(video_id)
            analysis = self.analyze_with_gemini(raw_data)

            data = {
                "video_id": video_id,
                "title": title,
                "topic": "youtube_benchmarking",
                "deep_analysis": {
                    "raw_content": raw_data,
                    "ai_insight": analysis
                }
            }
            # Supabase 저장
            supabase.table("research_cache").insert(data).execute()
            results.append(data)
            
        return results

if __name__ == "__main__":
    researcher = YouTubeResearcher()
    researcher.search_and_analyze("경제 위기 전망", max_results=2)