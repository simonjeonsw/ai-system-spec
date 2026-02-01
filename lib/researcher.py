import os
import sys
from pathlib import Path

# 가상환경 및 패키지 경로 강제 지정
venv_path = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages"
sys.path.append(str(venv_path))

from google.genai import Client
from .supabase_client import supabase
from .trend_scout import TrendScout
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

class VideoResearcher:
    def __init__(self):
        self.client = Client(api_key=os.getenv("GEMINI_API_KEY"))
        # 실제 사용 가능한 모델 매핑
        self.fast_model = "gemini-2.0-flash-lite"
        self.main_model = "gemini-2.0-flash"
        self.heavy_model = "gemini-2.5-flash"

    def get_video_transcript(self, video_id):
        ydl_opts = {'skip_download': True, 'quiet': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                url = f"https://www.youtube.com/watch?v={video_id}" if len(video_id) == 11 else video_id
                info = ydl.extract_info(url, download=False)
                content = f"Title: {info.get('title')}\nDescription: {info.get('description')}\nTags: {info.get('tags', [])}"
                return content
        except Exception as e:
            return f"Error: {str(e)}"

    def analyze_viral_strategy(self, topic):
        # 1. 캐시 확인
        cached = supabase.table("research_cache").select("*").eq("topic", topic).execute()
        if cached.data:
            return cached.data[0]["deep_analysis"]

        # 2. 데이터 수집
        transcript_text = self.get_video_transcript(topic)
        
        # 모델 선택 로직 (데이터 길이에 따라)
        selected_model = self.main_model
        if len(transcript_text) > 8000:
            selected_model = self.heavy_model

        print(f"📡 가동 중인 모델: {selected_model}")
        
        prompt_text = f"Analyze viral patterns of this video: {topic}\n\n{transcript_text}"
        analysis_result = ""

        try:
            # [수정] prompt= 를 contents= 로 변경
            response = self.client.models.generate_content(
                model=selected_model,
                contents=prompt_text
            )
            analysis_result = response.text
        except Exception as e:
            if "429" in str(e):
                fallback = self.heavy_model if selected_model != self.heavy_model else "gemini-pro-latest"
                print(f"⚠️ {selected_model} 쿼터 초과! {fallback} 엔진으로 전환합니다.")
                response = self.client.models.generate_content(
                    model=fallback,
                    contents=prompt_text
                )
                analysis_result = response.text
            else:
                raise e

        # 3. DB 저장 (기존에는 return 뒤에 있어서 실행이 안 됐습니다)
        if analysis_result:
            supabase.table("research_cache").insert({
                "topic": topic,
                "deep_analysis": analysis_result
                "raw_transcript": transcript_text
            }).execute()

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
    print("👉 번호(1-10) 입력 또는 유튜브 URL 붙여넣기:")
    user_input = input("👉 입력: ").strip()

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

    print(f"\n🚀 분석 공정 가동: {target_id}...")
    result = researcher.analyze_viral_strategy(target_id)
    print("\n" + "="*50)
    print(result)