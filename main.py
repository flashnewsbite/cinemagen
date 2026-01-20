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
    
    # 1. 뉴스 소스 선택
    print("[Step 1] Select News Source")
    print("1. 📅 Daily News Summary (Category Select)")
    print("2. 🔗 Specific News URL")
    choice = input("👉 Select Option (1/2): ")
    
    news_agent = NewsAgent()
    context = ""
    mode = "daily"
    category = "world" # 기본값
    
    if choice == "1":
        print("\n   [Select Category]")
        print("   1. 🌍 U.S. & World News")
        print("   2. 💻 Tech & Science News")
        print("   3. 💰 Finance News")
        print("   4. 🎨 Arts & Culture News")
        print("   5. 🏆 Sports News")
        print("   6. 🎬 Entertainment News")
        
        sub_choice = input("   👉 Select Category (1-6): ")
        
        cat_map = {
            "1": "world",
            "2": "tech",
            "3": "finance",
            "4": "art",
            "5": "sports",
            "6": "ent"
        }
        category = cat_map.get(sub_choice, "world")
        
        context = news_agent.get_daily_news(category=category)
        
    elif choice == "2":
        url = input("👉 Enter News URL: ")
        context = news_agent.get_news_from_url(url)
        mode = "url"
    else:
        print("Invalid choice")
        return

    if not context:
        print("❌ Failed to fetch news.")
        return

    # 2. 성우 설정
    print("\n[Step 2] Voice Settings")
    print("👉 Gender: 1. Male / 2. Female")
    g_input = input("   Selection (default 2): ")
    gender = "male" if g_input == "1" else "female"

    print("👉 Tone: 1. Mature(Trust) / 2. Neutral(Comfy) / 3. Bright(Youth)")
    t_input = input("   Selection (default 2): ")
    tone = t_input if t_input in ["1", "2", "3"] else "2"

    # 3. 대본 작성
    writer = WriterAgent()
    data = writer.generate_content(context, mode)
    
    if not data:
        print("❌ AI Generation Failed")
        return

    timestamp = time.strftime("%Y%m%d_%H%M")
    writer.save_metadata_file(data['metadata'], f"metadata_{timestamp}.txt")

    # 4. 미디어 생성
    media = MediaAgent()
    media.get_images(data['script']['scenes'])
    media.get_audio(data, gender=gender, tone=tone)

    # 5. 편집
    editor = Editor()
    
    # [핵심 수정] 여기서 category를 넘겨줘야 파일명에 반영됩니다!
    editor.make_shorts(data, category=category)
    
    print("\n🎉 All Done! Check 'results' folder.")

if __name__ == "__main__":
    main()