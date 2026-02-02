import os
import sys
from pathlib import Path

# 가상환경 경로 유지
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
        # 실제 사용 가능한 모델 매핑 유지
        self.fast_model = "gemini-2.0-flash-lite"
        self.main_model = "gemini-2.0-flash"
        self.heavy_model = "gemini-2.5-flash"

    def get_video_transcript(self, video_id):
        """기존 함수명 유지하되 댓글(Comments) 수집 기능 추가"""
        ydl_opts = {
            'skip_download': True, 
            'quiet': True,
            'get_comments': True, 
            'max_comments': 30,  # 효율성을 위해 베스트 댓글 30개
            'extract_flat': False
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                url = f"https://www.youtube.com/watch?v={video_id}" if len(video_id) == 11 else video_id
                info = ydl.extract_info(url, download=False)
                
                # 원본 변수명 content 유지 + 알고리즘 분석용 데이터 보강
                content = f"Title: {info.get('title')}\n"
                content += f"Description: {info.get('description')}\n"
                content += f"Tags: {info.get('tags', [])}\n"
                
                # 댓글 데이터 추가 (알고리즘 분석용)
                comments = info.get('comments', [])
                comment_text = "\n".join([f"- {c.get('text')}" for c in comments])
                content += f"\n[Viewer Reactions]\n{comment_text}"
                
                return content
        except Exception as e:
            return f"Error: {str(e)}"

    def analyze_viral_strategy(self, topic, force_update=False):
        """
        force_update=True: 매번 새로 분석 (로직 수정 중일 때 추천)
        force_update=False: 기존 데이터 있으면 재사용
        """

        # 1. 캐시 확인 (force_update가 False일 때만 작동)
        if not force_update:
            cached = supabase.table("research_cache").select("*").eq("topic", topic).execute()
            if cached.data:
                print(f"💡 기존 분석 데이터를 불러옵니다: {topic}")
                return cached.data[0]["deep_analysis"]

        # 2. 데이터 수집 및 분석 (업그레이드된 로직 가동)
        print(f"🚀 [신규/갱신] 알고리즘 정밀 분석 시작: {topic}")
        transcript_text = self.get_video_transcript(topic)
        
        # 모델 선택 로직 (데이터 길이에 따라)
        selected_model = self.main_model
        if len(transcript_text) > 8000:
            selected_model = self.heavy_model

        print(f"📡 가동 중인 모델: {selected_model}")
        
        # [수정] 영문 분석 + 한글 요약 이중 구조 프롬프트
        prompt_text = (
            f"Analyze the viral patterns and algorithmic success of this video: {topic}\n\n"
            f"Data Source:\n{transcript_text}\n\n"
            "--- INSTRUCTION ---\n"
            "1. First, provide a deep analysis in ENGLISH focusing on:\n"
            "   - Hook Strategy (0-30s) and Retention Pacing.\n"
            "   - Psychological triggers in the title/thumbnail.\n"
            "   - What compliment people gave and why they like it or helped.\n"
            "   - Script Structure: How does the narrative keep viewers hooked? (Analyze the opening, middle-climax, and closing).\n"
            "   - Retention Mechanics: Identify 'Pattern Interrupts' or 'Open Loops' used in the script.\n"
            "   - Psychological Triggers: Why did viewers stay until the end?\n"
            "   - Analyze with Script Engineering and pacing : Open Loop, Pattern Interrupt, High Stakes, Reward\n"
            "2. Then, provide a concise summary in KOREAN (한글 요약) including:\n"
            "   - 바이럴 핵심 키워드 및 시청자 열광 포인트.\n"
            "   - 우리 채널 대본 기획 시 반드시 적용해야 할 전략."
            "   - 대본 구성의 비밀: 시청자가 이탈하지 못하게 만든 문장 구조와 전개 방식.\n"
            "   - 텐션 유지 기술: 분위기를 환기 하거나 몰입도를 높인 핵심 장치.\n"
            "   - 우리 대본 적용점: 우리가 대본을 쓸 때 복제해야 할 '말하기 방식'과 '정보 배치 순서'.\n"
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
                print(f"⚠️ {selected_model} 쿼터 초과! {fallback} 엔진 전환.")
                response = self.client.models.generate_content(model=fallback, contents=prompt_text)
                analysis_result = response.text
            else:
                raise e

        # on_conflict='topic'을 통해 URL이 같으면 덮어쓰기 합니다.
        if 'analysis_result' in locals() and analysis_result:
            try:
                supabase.table("research_cache").upsert({
                    "topic": topic,
                    "deep_analysis": analysis_result,
                    "raw_transcript": transcript_text,
                    "updated_at": "now()" # 데이터가 언제 갱신되었는지 기록
                }, on_conflict='topic').execute()
                print("✅ 성공적으로 분석 데이터가 갱신되었습니다.")
            except Exception as e:
                print(f"⚠️ 저장 중 오류 발생: {e}")

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