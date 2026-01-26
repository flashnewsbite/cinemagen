import os
import re
import argparse  # [NEW] 명령줄 인수 처리를 위해 추가
from dotenv import load_dotenv
from config import Config
from news_agent import NewsAgent
from writer_agent import WriterAgent
from media_agent import MediaAgent
from editor import Editor

# 환경 변수 로드
load_dotenv()

def sanitize_script(script_data):
    """
    [Hotfix] 2026년 기준 트럼프는 현직 대통령입니다.
    AI가 'Former' 또는 'Ex-'라고 잘못 쓴 표현을 강제로 교정합니다.
    """
    if not script_data: return script_data

    def replace_text(text):
        if not text: return ""
        # 대소문자 구분 없이(Ignore case) 패턴 찾아서 교체
        # 1. "Former President Trump" -> "President Trump"
        text = re.sub(r'(?i)former president\s+trump', 'President Trump', text)
        # 2. "Ex-President Trump" -> "President Trump"
        text = re.sub(r'(?i)ex-president\s+trump', 'President Trump', text)
        return text

    print("🧹 [Main] Sanitizing script terminology (Trump: Former -> President)...")

    # 1. 제목 교정
    if 'title' in script_data:
        script_data['title'] = replace_text(script_data['title'])

    # 2. 인트로/아웃트로 교정
    if 'intro_narration' in script_data:
        script_data['intro_narration'] = replace_text(script_data['intro_narration'])
    if 'outro_narration' in script_data:
        script_data['outro_narration'] = replace_text(script_data['outro_narration'])

    # 3. 본문 씬(Scene) 교정
    if 'script' in script_data and 'scenes' in script_data['script']:
        for scene in script_data['script']['scenes']:
            if 'narration' in scene:
                scene['narration'] = replace_text(scene['narration'])
            if 'image_prompt' in scene:
                scene['image_prompt'] = replace_text(scene['image_prompt'])

    return script_data

def main():
    print(f"\n🤖 Flash News Bite AI Studio Initialized...")

    # [NEW] 자동화 파라미터 설정 (argparse)
    parser = argparse.ArgumentParser(description="CinemaGen Automation")
    parser.add_argument("--category", type=str, help="Auto-run category: world, tech, finance, art, sports, ent")
    parser.add_argument("--gender", type=str, default="female", help="Voice gender: male or female")
    parser.add_argument("--tone", type=str, default="2", help="Voice tone: 1(Trust), 2(Neutral), 3(Bright)")
    
    args = parser.parse_args()

    # 에이전트 인스턴스 생성
    news_agent = NewsAgent()
    writer = WriterAgent()
    media_agent = MediaAgent()
    editor = Editor()

    # 변수 초기화
    news_mode = "daily"
    target_category = "world"
    target_url = None
    gender = "female"
    tone = "2"

    # =================================================================================
    # [Step 1] 사용자 입력 OR 자동 모드 판단
    # =================================================================================
    
    # 1. 자동 모드 (스케줄러가 --category 값을 줬을 때)
    if args.category:
        print(f"🚀 [Auto Mode] Starting automation for category: {args.category}")
        news_mode = "daily"
        target_category = args.category
        gender = args.gender
        tone = args.tone
        
    # 2. 수동 모드 (평소처럼 실행했을 때)
    else:
        print("\n[Step 1] Select News Source")
        print("1. 📅 Daily News Summary (Category Select)")
        print("2. 🔗 Specific News URL")
        
        source_choice = input("👉 Select Option (1/2): ").strip()
        
        if source_choice == '2':
            news_mode = "url"
            target_url = input("👉 Enter News URL: ").strip()
        else:
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

        print("\n[Step 2] Voice Settings")
        print("👉 Gender: 1. Male / 2. Female")
        g_choice = input("   Selection (default 2): ").strip()
        gender = "male" if g_choice == '1' else "female"
        
        print("👉 Tone: 1. Mature(Trust) / 2. Neutral(Comfy) / 3. Bright(Youth)")
        t_choice = input("   Selection (default 2): ").strip()
        tone_map = {'1': '1', '2': '2', '3': '3'}
        tone = tone_map.get(t_choice, '2')

    print("\n" + "="*50)
    print(f"🚀 Processing: [{news_mode.upper()}] Category=[{target_category}] Gender=[{gender}]")
    print("="*50 + "\n")

    # =================================================================================
    # [Step 2] 실행 단계 (자동/수동 공통)
    # =================================================================================

    try:
        # 1. News Gathering
        context = ""
        if news_mode == "url":
            print(f"📰 [News] Fetching content from URL...")
            context = news_agent.get_specific_news(target_url)
        else:
            # category가 문자열(world, tech...)인지 확인
            context = news_agent.get_daily_news(category=target_category)

        if not context:
            print("❌ Failed to gather news context. Aborting.")
            return

        # 2. Script Writing
        script_data = writer.generate_content(context, mode="shorts")
        
        if not script_data:
            print("❌ Script generation failed.")
            return

        # [Hotfix] 대본 교정 (Former -> President)
        script_data = sanitize_script(script_data)
        
        # [NEW] 메타데이터 저장 (writer_agent 수정본 적용 시 동작)
        if 'metadata' in script_data:
            # save_metadata_file 함수가 있다면 호출
            if hasattr(writer, 'save_metadata_file'):
                writer.save_metadata_file(script_data['metadata'])
            else:
                print("⚠️ writer.save_metadata_file not found. Skipping metadata save.")

        # 3. Media Generation (TTS, Image)
        media_agent.get_audio(script_data, gender=gender, tone=tone)
        media_agent.get_images(script_data['script']['scenes'])

        # 4. Video Editing
        editor.make_shorts(script_data, category=target_category)

        print("\n🎉 All Done! Please check the 'results' folder.")

    except Exception as e:
        print(f"\n❌ Critical Error in Main Process: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()