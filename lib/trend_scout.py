import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

class TrendScout:
    def __init__(self):
        self.youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))

    def fetch_trending_videos(self, region_code='KR', max_results=10):
        """Fetch top trending videos to report to the Factory Manager."""
        request = self.youtube.videos().list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=max_results
        )
        response = request.execute()
        
        report = []
        print("\n📢 [Trend Briefing] Current Viral Topics in Korea:\n")
        for i, item in enumerate(response['items']):
            title = item['snippet']['title']
            view_count = item['statistics'].get('viewCount', '0')
            video_id = item['id']
            report.append({"id": video_id, "title": title})
            print(f"{i+1}. {title} (Views: {view_count})")
        
        print("\n" + "="*50)
        user_input = input("👉 Enter the number to analyze, or type a custom keyword: ")
        
        # Logic to return selected title or custom keyword
        if user_input.isdigit() and 1 <= int(user_input) <= len(report):
            return report[int(user_input)-1]['title']
        return user_input

if __name__ == "__main__":
    scout = TrendScout()
    selected_topic = scout.fetch_trending_videos()
    print(f"\n🚀 Proceeding with: {selected_topic}")