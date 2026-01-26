import os
import time
import subprocess
import json
from datetime import datetime

# 업로더 모듈 가져오기
try:
    from uploaders.youtube_uploader import upload_video as youtube_upload
    from uploaders.x_uploader_browser import upload_video as x_upload
    from uploaders.threads_uploader_browser import upload_video as threads_upload
except ImportError:
    pass

BASE_DIR = os.getcwd()
RESULTS_DIR = os.path.join(BASE_DIR, "results")

def get_best_description(txt_path, meta_data):
    if os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if len(content) > 10: return content
        except: pass
    
    if meta_data and "youtube_description" in meta_data:
        return meta_data["youtube_description"]
    
    return "#shorts #art #news"

def find_video_file(category):
    """
    영상 파일 찾기 로직 (단수/복수형 자동 대응)
    """
    cat_upper = category.upper()
    candidates = [
        f"final_shorts_{cat_upper}.mp4",
        f"final_shorts_{cat_upper}S.mp4",
        f"final_shorts_{cat_upper.rstrip('S')}.mp4"
    ]
    
    for filename in sorted(list(set(candidates)), key=len):
        full_path = os.path.join(RESULTS_DIR, filename)
        if os.path.exists(full_path):
            print(f"      ✅ Found video file: {filename}")
            return full_path
    return None

def process_and_archive_files(category):
    timestamp = datetime.now().strftime("%m%d%Y_%H%M")
    
    # [수정] 파일 찾기
    src_video = find_video_file(category)
    
    src_meta  = os.path.join(RESULTS_DIR, "metadata.json")
    src_text  = os.path.join(RESULTS_DIR, "social_metadata.txt")

    new_base_name = f"final_shorts_{category.upper()}_{timestamp}"
    dst_video = os.path.join(RESULTS_DIR, f"{new_base_name}.mp4")
    dst_meta  = os.path.join(RESULTS_DIR, f"{new_base_name}.json")
    dst_text  = os.path.join(RESULTS_DIR, f"{new_base_name}.txt")

    archived_data = {'video': None, 'meta': {}, 'desc': ""}

    try:
        # 1. 메타데이터 읽기
        if os.path.exists(src_meta):
            with open(src_meta, 'r', encoding='utf-8') as f:
                archived_data['meta'] = json.load(f)
        else:
            print("⚠️ metadata.json not found (Creating dummy data)")
            archived_data['meta'] = {"youtube_title": f"{category} News", "x_post": "Update!"}

        # 2. 설명 확보
        archived_data['desc'] = get_best_description(src_text, archived_data['meta'])

        # 3. 파일 이름 변경 (Archiving)
        if os.path.exists(src_text):
            os.rename(src_text, dst_text)
            print(f"📦 Archived Text:  {os.path.basename(dst_text)}")

        if os.path.exists(src_meta):
            os.rename(src_meta, dst_meta)
            print(f"📦 Archived Meta:  {os.path.basename(dst_meta)}")

        if src_video and os.path.exists(src_video):
            os.rename(src_video, dst_video)
            print(f"📦 Archived Video: {os.path.basename(dst_video)}")
            archived_data['video'] = dst_video
        else:
            print(f"❌ Video not found. Category: {category}")
            return None, None, None

        return archived_data['video'], archived_data['meta'], archived_data['desc']

    except Exception as e:
        print(f"❌ Archive Error: {e}")
        return None, None, None

def run_full_test():
    print(f"\n🧪 Starting Art Category Test... {datetime.now().strftime('%H:%M:%S')}")
    
    target_category = "art"
    target_tone = "3" 

    # 1. 영상 생성
    print(f"\n🎬 [Step 1] Generating Video ({target_category.upper()})...")
    # 이미 생성된 파일로 테스트하려면 check=False 및 subprocess 주석 처리 고려
    subprocess.run(["python", "main.py", "--category", target_category, "--tone", target_tone], check=False)

    # 2. 파일 보관
    print("\n📦 [Step 2] Archiving Files...")
    video_path, meta, desc_text = process_and_archive_files(target_category)
    
    if not video_path:
        print("❌ Test Aborted: Video file missing.")
        return

    print(f"   ✅ Target File: {os.path.basename(video_path)}")
    
    # 3. 업로드
    yt_title = f"[TEST] {meta.get('youtube_title', 'Art News Title')}"
    yt_desc = desc_text 
    sns_text = f"[TEST] {meta.get('x_post', 'Art News Check this out!')}"

    # YouTube
    print("\n🟥 YouTube Upload...")
    try: 
        youtube_upload(video_path, category=target_category, title=yt_title, description=yt_desc)
    except Exception as e: 
        print(f"   -> Failed: {e}")
    
    # X (Twitter)
    print("\n⬛ X Upload...")
    try: 
        x_upload(video_path, text=sns_text)
    except Exception as e: 
        print(f"   -> Failed: {e}")
    
    time.sleep(3)

    # Threads
    print("\n🧵 Threads Upload...")
    try: 
        threads_upload(video_path, text=sns_text)
    except Exception as e: 
        print(f"   -> Failed: {e}")

    print("\n✨ Art Test Complete. Files are preserved.")

if __name__ == "__main__":
    run_full_test()