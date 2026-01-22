import os
from dotenv import load_dotenv
from config import Config
from news_agent import NewsAgent
from writer_agent import WriterAgent
from media_agent import MediaAgent
from editor import Editor

# 환경 변수 로드
load_dotenv()

def main():
    # [수정] Config.CHANNEL_NAME 대신 직접 텍스트 입력
    print(f"\n🤖 Flash News Bite AI Studio Initialized...")
    
    # 에이전트 인스턴스 생성
    news_agent = NewsAgent()
    writer = WriterAgent()
    media_agent = MediaAgent()
    editor = Editor()

    # =================================================================================
    # [Step 1] 사용자 입력 단계 (User Input Phase) - 모든 설정을 여기서 끝냄
    # =================================================================================
    
    # 1-1. 뉴스 소스 선택
    print("\n[Step 1] Select News Source")
    print("1. 📅 Daily News Summary (Category Select)")
    print("2. 🔗 Specific News URL")
    
    source_choice = input("👉 Select Option (1/2): ").strip()
    
    news_mode = "daily"
    target_category = "world"
    target_url = None

    if source_choice == '2':
        news_mode = "url"
        target_url = input("👉 Enter News URL: ").strip()
    else:
        # 카테고리 선택
        print("\n   [Select Category]")
        print("   1. 🌍 U.S. & World News")
        print("   2. 💻 Tech & Science News")
        print("   3. 💰 Finance News")
        print("   4. 🎨 Arts & Culture News")
        print("   5. 🏆 Sports News")
        print("   6. 🎬 Entertainment News")
        
        cat_map = {"1": "world", "2": "tech", "3": "finance", "4": "art", "5": "sports", "6": "ent"}
        cat_choice = input("   👉 Select Category (1-6): ").strip()
        target_category = cat_map.get(cat_choice, "world")

    # 1-2. 목소리 설정 (뉴스 검색 전에 미리 물어봄!)
    print("\n[Step 2] Voice Settings")
    
    # 성별 선택
    print("👉 Gender: 1. Male / 2. Female")
    g_choice = input("   Selection (default 2): ").strip()
    gender = "male" if g_choice == '1' else "female"
    
    # 톤 선택
    print("👉 Tone: 1. Mature(Trust) / 2. Neutral(Comfy) / 3. Bright(Youth)")
    t_choice = input("   Selection (default 2): ").strip()
    tone_map = {'1': '1', '2': '2', '3': '3'}
    tone = tone_map.get(t_choice, '2')

    print("\n" + "="*50)
    print("🚀 All Settings Complete. Starting Auto-Production...")
    print("="*50 + "\n")

    # =================================================================================
    # [Step 2] 자동 실행 단계 (Processing Phase) - 이제부터 사용자는 기다리기만 하면 됨
    # =================================================================================

    try:
        # 1. News Gathering (시간 소요됨)
        context = ""
        if news_mode == "url":
            print(f"📰 [News] Fetching content from URL...")
            context = news_agent.get_news_from_url(target_url)
        else:
            # get_daily_news 함수 내부의 로그들이 여기서 출력됨
            context = news_agent.get_daily_news(category=target_category)

        if not context:
            print("❌ Failed to gather news context. Aborting.")
            return

        # 2. Script Writing
        script_data = writer.generate_content(context, mode="shorts")
        
        if not script_data:
            print("❌ Script generation failed.")
            return
        
        # 메타데이터 저장
        if 'metadata' in script_data:
            writer.save_metadata_file(script_data['metadata'])

        # 3. Media Generation (TTS, Image)
        # 선택한 gender, tone 변수를 전달하여 오디오 생성 (1.2배속 적용됨)
        media_agent.get_audio(script_data, gender=gender, tone=tone)
        # 이미지 다운로드 (필터링 적용됨)
        media_agent.get_images(script_data['script']['scenes'])

        # 4. Video Editing
        # 영상 편집 (자막 위치 고정, 오디오 사이 0.6초 무음 적용됨)
        editor.make_shorts(script_data, category=target_category)

        print("\n🎉 All Done! Please check the 'results' folder.")

    except Exception as e:
        print(f"\n❌ Critical Error in Main Process: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()