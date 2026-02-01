import os
import yt_dlp
# 1. 올바른 최신 SDK 부품을 가져옵니다. (구형 google.generativeai 삭제)
from googleapiclient.discovery import build
from .supabase_client import supabase
from dotenv import load_dotenv
try:
    from google.genai import Client
except ImportError:
    # 혹시라도 설치 경로 문제라면 여기서 강제로 찾게 할 수 있습니다.
    import sys
    sys.path.append(r"C:\Users\simon\AppData\Local\Programs\Python\Python313\Lib\site-packages")
    from google.genai import Client

load_dotenv()

class DeepResearcher:
    def __init__(self):
        # 2. 구글 유튜브 API 설정
        self.youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))
        # 3. 최신 SDK 클라이언트 초기화
        self.client = Client(api_key=os.getenv("GEMINI_API_KEY"))
        # 사용할 모델명 (무료 가성비 모델)
        self.model_id = "gemini-2.5-flash-lite"

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
                # 우선 설명(description)을 가져오도록 설정되어 있습니다.
                return info.get('description', '') 
        except Exception as e:
            return f"Transcript extraction failed: {str(e)}"

    def analyze_viral_strategy(self, topic):
        """Search videos and analyze their transcripts."""
        # 4. 유튜브에서 해당 주제 영상 검색
        search_res = self.youtube.search().list(q=topic, part="snippet", maxResults=1, type="video").execute()
        
        if not search_res.get('items'):
            return "No videos found for this topic."

        for item in search_res['items']:
            v_id = item['id']['videoId']
            transcript = self.get_video_transcript(v_id)
            
            # 5. 최신 SDK 문법으로 분석 요청
            prompt = f"Analyze this YouTube transcript for viral patterns (Provide results in English and Korean): {transcript}"
            
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            
            # 6. 결과 텍스트 추출 (response.text 사용)
            analysis_text = response.text
            
            # 7. Supabase 저장
            supabase.table("research_cache").insert({
                "topic": topic,
                "deep_analysis": {"insight": analysis_text, "video_id": v_id}
            }).execute()
            
            return analysis_text

if __name__ == "__main__":
    # 실행 시 trend_scout에서 주제를 가져옴
    try:
        from .trend_scout import TrendScout
        scout = TrendScout()
        topic = scout.fetch_trending_videos()
        
        if topic:
            researcher = DeepResearcher()
            print(f"\n🚀 Deep analyzing '{topic}'...")
            print(researcher.analyze_viral_strategy(topic))
    except ImportError:
        print("TrendScout module not found. Please check your file structure.")