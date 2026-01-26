import os
import time
import schedule
import subprocess
import json
from datetime import datetime

# 업로더 모듈
try:
    from uploaders.youtube_uploader import upload_video as youtube_upload
    from uploaders.x_uploader_browser import upload_video as x_upload
    from uploaders.threads_uploader_browser import upload_video as threads_upload
except ImportError:
    pass

BASE_DIR = os.getcwd()
RESULTS_DIR = os.path.join(BASE_DIR, "results")

def get_description_content(txt_path, meta_data):
    """
    유튜브 설명(Description)을 결정하는 함수
    TXT 파일 내용을 최우선으로 반환합니다.
    """
    # 1순위: social_metadata.txt 직접 읽기
    if os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if len(content) > 10:
                    print("      ✅ Found valid description in social_metadata.txt")
                    return content
        except Exception as e:
            print(f"      ⚠️ Error reading text file: {e}")
    
    # 2순위: metadata.json
    if meta_data and "youtube_description" in meta_data:
        print("      ℹ️ Using description from metadata.json")
        return meta_data["youtube_description"]
    
    print("      ⚠️ No description found. Using default tags.")
    return "#shorts #news"

def find_video_file(category):
    """
    생성된 영상 파일을 찾기 위해 여러 가지 이름 조합을 시도합니다.
    예: 'art' -> 'final_shorts_ART.mp4', 'final_shorts_ARTS.mp4'
    """
    cat_upper = category.upper()
    
    # 가능한 파일명 후보들
    candidates = [
        f"final_shorts_{cat_upper}.mp4",       # 기본 (예: ART, SPORTS)
        f"final_shorts_{cat_upper}S.mp4",      # S 추가 (예: ARTS)
        f"final_shorts_{cat_upper.rstrip('S')}.mp4" # S 제거 (예: SPORTS -> SPORT)
    ]
    
    # 중복 제거 (set) 후 순서 유지하며 확인
    for filename in sorted(list(set(candidates)), key=len): # 짧은 이름부터? 혹은 그냥 순서대로
        full_path = os.path.join(RESULTS_DIR, filename)
        if os.path.exists(full_path):
            print(f"      ✅ Found video file: {filename}")
            return full_path
            
    return None

def process_and_archive_files(category):
    timestamp = datetime.now().strftime("%m%d%Y_%H%M")
    
    # [수정] 영상 파일 찾기 (단수/복수형 자동 감지)
    src_video = find_video_file(category)
    
    src_meta  = os.path.join(RESULTS_DIR, "metadata.json")
    src_text  = os.path.join(RESULTS_DIR, "social_metadata.txt")

    # 저장될 파일명 (항상 사용자가 입력한 category 기준 단일 포맷으로 통일)
    new_base_name = f"final_shorts_{category.upper()}_{timestamp}"
    
    dst_video = os.path.join(RESULTS_DIR, f"{new_base_name}.mp4")
    dst_meta  = os.path.join(RESULTS_DIR, f"{new_base_name}.json")
    dst_text  = os.path.join(RESULTS_DIR, f"{new_base_name}.txt")

    final_data = {'video_path': None, 'meta': {}, 'description': ""}

    # 1. 메타데이터(JSON) 로드
    if os.path.exists(src_meta):
        with open(src_meta, 'r', encoding='utf-8') as f:
            final_data['meta'] = json.load(f)

    # 2. 설명(Description) 확보
    final_data['description'] = get_description_content(src_text, final_data['meta'])

    # 3. 파일 이름 변경 (Archiving)
    try:
        # 텍스트
        if os.path.exists(src_text):
            os.rename(src_text, dst_text)
            
        # 메타데이터
        if os.path.exists(src_meta):
            os.rename(src_meta, dst_meta)
        
        # 영상
        if src_video and os.path.exists(src_video):
            os.rename(src_video, dst_video)
            print(f"📦 [Archived] {os.path.basename(dst_video)}")
            final_data['video_path'] = dst_video
        else:
            print(f"❌ Video file missing. (Checked variants for category: {category})")
            return None
            
    except Exception as e:
        print(f"❌ Error moving files: {e}")
        return None

    return final_data

def run_job(category, tone):
    start_time = datetime.now().strftime('%H:%M')
    print(f"\n🎬 [{start_time}] Starting Job: Category='{category}', Tone='{tone}'")

    # 1. 영상 생성
    try:
        subprocess.run(["python", "main.py", "--category", category, "--tone", tone], check=True)
    except:
        print("❌ Generation Failed.")
        return

    # 2. 파일 처리 & 데이터 확보
    data = process_and_archive_files(category)
    if not data or not data['video_path']: return

    # 3. 업로드 데이터 준비
    video_path = data['video_path']
    yt_title = data['meta'].get("youtube_title", f"Daily {category} News")
    yt_desc = data['description'] 
    sns_text = data['meta'].get("x_post", "#Shorts")

    print(f"\n📝 [Check] YouTube Description Preview:\n{'-'*30}\n{yt_desc[:100]}...\n{'-'*30}")

    # 4. YouTube Upload
    print("   🚀 Uploading to YouTube...")
    youtube_upload(video_path, category=category, title=yt_title, description=yt_desc)
    
    # 5. X Upload
    print("   🚀 Uploading to X...")
    x_upload(video_path, text=sns_text)
    
    # 6. Threads Upload
    time.sleep(5)
    print("   🚀 Uploading to Threads...")
    threads_upload(video_path, text=sns_text)
    
    print(f"✨ Job Finished for {category}.\n")

# 24시간 스케줄 설정
schedule.every().day.at("07:00").do(run_job, category="world", tone="1")
schedule.every().day.at("08:00").do(run_job, category="sports", tone="2")
schedule.every().day.at("09:30").do(run_job, category="finance", tone="1")
schedule.every().day.at("13:00").do(run_job, category="tech", tone="2")
schedule.every().day.at("14:00").do(run_job, category="art", tone="3")
schedule.every().day.at("16:30").do(run_job, category="finance", tone="1")
schedule.every().day.at("17:00").do(run_job, category="world", tone="1")
schedule.every().day.at("19:00").do(run_job, category="ent", tone="3")
schedule.every().day.at("20:00").do(run_job, category="tech", tone="2")
schedule.every().day.at("21:00").do(run_job, category="finance", tone="1")

# 추가 시간대
schedule.every().day.at("03:00").do(run_job, category="finance", tone="1")
schedule.every().day.at("04:00").do(run_job, category="tech", tone="2")

if __name__ == "__main__":
    print("🤖 Scheduler Started...")
    while True:
        schedule.run_pending()
        time.sleep(60)