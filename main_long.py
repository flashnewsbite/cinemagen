import os
import argparse
import json
from datetime import datetime
from config import Config
from news_agent import NewsAgent
from writer_agent import WriterAgent
from media_agent import MediaAgent
from editor_long import EditorLong
# 기존 YouTube Uploader 재사용
from youtube_uploader import upload_video 

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

    # 3. 보이스 설정
    print("\n[Voice Settings]")
    print("👉 Gender: 1. Male / 2. Female")
    g_input = input("Selection (default 1): ").strip()
    gender = "male" if g_input == '1' else "female"
    
    print("👉 Tone: 1. Trust / 2. Neutral / 3. Bright")
    t_input = input("Selection (default 1): ").strip()
    tone_map = {'1':'1', '2':'2', '3':'3'}
    tone = tone_map.get(t_input, '1')

    # 4. 대본 작성 (Long Mode)
    # script_data 안에 메타데이터(Title, Desc 등)가 포함됨
    script_data = writer.generate_content(context, mode="long", source_type=source_type)
    if not script_data:
        print("❌ Script generation failed.")
        return
    
    # 카테고리 설정 (YouTube Playlist용) - 기본값 Education
    # Writer가 JSON에 category를 주면 좋지만, 없으면 기본값 사용
    video_category = script_data.get("category", "tech") 
    
    print(f"\n📄 Title: {script_data.get('title')}")
    print(f"📄 Scenes: {len(script_data['script']['scenes'])}")

    # 5. 미디어 생성 (오디오 + 비디오/이미지)
    # 오디오 생성
    media_agent.get_audio(script_data, gender=gender, tone=tone)
    
    # 비주얼 에셋 다운로드 (Pexels Video + Serper Image 혼합)
    media_agent.get_mixed_media(script_data['script']['scenes'])

    print("\n✅ Assets Ready! Starting Editor...")
    
    # 6. 편집 및 렌더링
    output_file = editor.make_video(script_data)
    
    if output_file and os.path.exists(output_file):
        print("\n" + "="*50)
        print("🚀 [Upload] Uploading to YouTube...")
        print("="*50)
        
        # 메타데이터 추출
        final_title = script_data.get('title', 'New Video')
        # 설명에 해시태그 추가
        final_desc = script_data.get('description', '')
        if 'metadata' in script_data and 'tags' in script_data['metadata']:
            tags = script_data['metadata']['tags']
            hash_tags = " ".join([f"#{t.replace(' ', '')}" for t in tags])
            final_desc += f"\n\n{hash_tags}"

        # YouTube 업로드 실행
        # playlist_id는 youtube_uploader.py 내부 딕셔너리(PLAYLIST_IDS)에 의존
        # 따라서 category 이름을 잘 넘겨주는 것이 중요함.
        # WriterPrompt에서 category를 명시적으로 주지 않았다면, 
        # 사용자가 입력한 Topic이나 URL 내용에 따라 추론된 category를 쓰거나 'tech' 등을 기본값으로.
        
        success = upload_video(
            video_path=output_file,
            category=video_category, # youtube_uploader의 PLAYLIST_IDS 키 값과 매칭 (예: world, tech, health...)
            title=final_title[:100], # 유튜브 제목 길이 제한
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