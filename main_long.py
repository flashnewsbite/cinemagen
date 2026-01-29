import os
import argparse
import json
from datetime import datetime
from config import Config
from news_agent import NewsAgent
from writer_agent import WriterAgent
from media_agent import MediaAgent
from editor_long import EditorLong
from uploaders.youtube_uploader import upload_video

def main():
    print(f"\n🎬 [CinemaGen Long-Form Studio] Initialized...")
    print("="*50)

    # 1. 입력 모드 선택
    print("Select Mode:")
    print("1. 🔗 URL based (News/Fact - Uses Images)")
    print("2. 📝 Topic based (Story/General - Uses Stock Videos)")
    mode_choice = input("👉 Select (1/2): ").strip()
    
    source_type = "news" if mode_choice == '1' else "topic"
    context = ""
    
    # 에이전트 초기화
    news_agent = NewsAgent()
    writer = WriterAgent()
    media_agent = MediaAgent()
    editor = EditorLong()

    # 2. Context 확보
    if source_type == "news":
        url = input("👉 Enter Article URL: ").strip()
        print("⏳ Fetching article...")
        context = news_agent.get_specific_news(url)
    else:
        title = input("👉 Enter Topic Title: ").strip()
        desc = input("👉 Enter Brief Description: ").strip()
        context = f"Topic: {title}\nDescription: {desc}"

    if not context:
        print("❌ Failed to get context.")
        return

    # [NEW] 2.5 영상 길이 선택
    print("\n[Target Duration]")
    print("1. Short (2~4 mins)")
    print("2. Medium (6~10 mins)")
    print("3. Long (12~18 mins)")
    print("4. Feature (20~30 mins)")
    dur_input = input("👉 Select Duration (1-4): ").strip()
    
    duration_map = {
        '1': '2-4 minutes',
        '2': '6-10 minutes',
        '3': '12-18 minutes',
        '4': '20-30 minutes'
    }
    target_duration = duration_map.get(dur_input, '2-4 minutes')
    print(f"✅ Target Duration Set: {target_duration}")

    # 3. 보이스 설정
    print("\n[Voice Settings]")
    print("👉 Gender: 1. Male / 2. Female")
    g_input = input("Selection (default 1): ").strip()
    gender = "male" if g_input == '1' else "female"
    
    print("👉 Tone: 1. Trust / 2. Neutral / 3. Bright")
    t_input = input("Selection (default 1): ").strip()
    tone_map = {'1':'1', '2':'2', '3':'3'}
    tone = tone_map.get(t_input, '1')

    # 4. 대본 작성 (Long Mode + Duration 전달)
    script_data = writer.generate_content(context, mode="long", source_type=source_type, duration=target_duration)
    if not script_data:
        print("❌ Script generation failed.")
        return
    
    video_category = script_data.get("category", "tech") 
    
    print(f"\n📄 Title: {script_data.get('title')}")
    print(f"📄 Scenes: {len(script_data['script']['scenes'])}")

    # 5. 미디어 생성
    media_agent.get_audio(script_data, gender=gender, tone=tone)
    media_agent.get_mixed_media(script_data['script']['scenes'])

    print("\n✅ Assets Ready! Starting Editor...")
    
    # 6. 편집 및 렌더링
    output_file = editor.make_video(script_data)
    
    if output_file and os.path.exists(output_file):
        print("\n" + "="*50)
        print("🚀 [Upload] Uploading to YouTube...")
        print("="*50)
        
        final_title = script_data.get('title', 'New Video')
        final_desc = script_data.get('description', '')
        if 'metadata' in script_data and 'tags' in script_data['metadata']:
            tags = script_data['metadata']['tags']
            hash_tags = " ".join([f"#{t.replace(' ', '')}" for t in tags])
            final_desc += f"\n\n{hash_tags}"

        success = upload_video(
            video_path=output_file,
            category=video_category, 
            title=final_title[:100],
            description=final_desc
        )
        
        if success:
            print("\n🎉 [Success] Video Created & Uploaded!")
        else:
            print("\n⚠️ [Warning] Video Created but Upload Failed.")
    else:
        print("❌ Video rendering failed.")

if __name__ == "__main__":
    main()