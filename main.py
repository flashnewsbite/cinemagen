import sys
from news_agent import NewsAgent
from writer_agent import WriterAgent
from media_agent import MediaAgent
from editor import Editor
import time

def main():
    print("========================================")
    print("🎥 CinemaGen: News Shorts Automation")
    print("========================================")
    print("1. 📅 Daily News Summary")
    print("2. 🔗 Specific News URL")
    
    choice = input("👉 Select Option (1/2): ")
    
    # 1. 뉴스 수집
    news_agent = NewsAgent()
    context = ""
    mode = "daily"
    
    if choice == "1":
        context = news_agent.get_daily_news()
    elif choice == "2":
        url = input("👉 Enter News URL: ")
        context = news_agent.get_news_from_url(url)
        mode = "url"
    else:
        print("Invalid choice")
        return

    if not context:
        print("❌ 뉴스 내용을 가져오지 못했습니다.")
        return

    # 2. 대본 및 메타데이터 작성
    writer = WriterAgent()
    data = writer.generate_content(context, mode)
    
    if not data:
        print("❌ AI 생성 실패")
        return

    script = data['script']
    metadata = data['metadata']
    
    # 메타데이터 파일 저장
    timestamp = time.strftime("%Y%m%d_%H%M")
    writer.save_metadata_file(metadata, f"metadata_{timestamp}.txt")

    # 3. 미디어 생성
    media = MediaAgent()
    media.get_images(script['scenes'])
    media.get_audio(script['scenes'])

    # 4. 편집
    editor = Editor()
    editor.make_shorts(script['scenes'])
    
    print("\n🎉 All Done! Check 'results' folder.")

if __name__ == "__main__":
    main()