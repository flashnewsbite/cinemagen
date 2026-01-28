import os
import time
import schedule
import subprocess
import json
import random
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

# ====================================================
# 🧠 AI Director Logic (Voice & File Management)
# ====================================================

def get_voice_settings(category):
    """
    [기획 반영] 카테고리와 현재 시간(오전/오후)에 따라 최적의 목소리(성별, 톤) 결정
    """
    current_hour = datetime.now().hour
    is_morning = 0 <= current_hour < 12
    
    cat_lower = category.lower()
    
    if cat_lower in ['world', 'finance', 'fin', 'us']:
        gender = "male" if is_morning else "female"
        tone = "1"
    elif cat_lower in ['tech', 'science']:
        gender = "male"
        tone = "2"
    elif cat_lower in ['sport', 'sports']:
        gender = random.choice(["male", "female"])
        tone = "2"
    elif cat_lower in ['ent', 'art', 'arts', 'entertainment']:
        gender = "female"
        tone = "3"
    else:
        gender = "female"
        tone = "2"
        
    return gender, tone

def get_exact_files(category, timestamp):
    """
    [NEW] 스케줄러가 지정한 timestamp로 정확한 파일 경로를 반환합니다.
    (MP4 영상, TXT 파일, JSON 메타데이터 3가지를 모두 찾습니다)
    """
    cat_upper = category.upper()
    
    # main.py가 생성하기로 약속된 정확한 파일명 규칙
    base_name = f"final_shorts_{cat_upper}_{timestamp}"
    
    video_path = os.path.join(RESULTS_DIR, f"{base_name}.mp4")
    text_path = os.path.join(RESULTS_DIR, f"{base_name}.txt")
    json_path = os.path.join(RESULTS_DIR, f"{base_name}.json") # [추가] JSON 경로 확보
    
    # 비디오 파일 존재 여부 확인 (필수)
    if not os.path.exists(video_path):
        print(f"      ❌ Critical: Expected video file not found!")
        print(f"         Target: {video_path}")
        return None, None, None

    print(f"      ✅ Verified file exists: {os.path.basename(video_path)}")
    return video_path, text_path, json_path

def load_json_metadata(json_path):
    """
    JSON 파일을 안전하게 읽어오는 함수
    """
    if json_path and os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"      ⚠️ Error loading JSON: {e}")
    return {}

def run_job(category):
    """
    스케줄러 잡 실행 함수
    """
    # 1. 작업 ID(Timestamp) 생성 - 스케줄러가 주도권을 가짐 (Timestamp Injection)
    timestamp = datetime.now().strftime("%m%d%Y_%H%M")
    
    gender, tone = get_voice_settings(category)
    current_time = datetime.now().strftime('%H:%M')
    
    print(f"\n🎬 [{current_time}] Starting Job: Category='{category}' (ID: {timestamp})")
    print(f"   🎙️ Voice Director: Gender='{gender.upper()}', Tone='{tone}'")

    # 2. 영상 생성 요청 (timestamp 전달)
    try:
        subprocess.run([
            "python", "main.py", 
            "--category", category, 
            "--gender", gender, 
            "--tone", tone,
            "--timestamp", timestamp
        ], check=True)
    except Exception as e:
        print(f"❌ Generation Failed: {e}")
        return

    # 3. [수정됨] 정확한 파일명으로 가져오기 (JSON 포함)
    video_path, text_path, json_path = get_exact_files(category, timestamp)
    
    if not video_path:
        print(f"❌ Aborting upload. Job failed for {category}.")
        return

    # 4. [핵심 수정] JSON 데이터 로드 및 플랫폼별 내용 분배
    meta_data = load_json_metadata(json_path)
    
    # (A) YouTube 데이터
    # JSON에 제목이 없으면 기본 제목 사용
    yt_title = meta_data.get('youtube_title', f"Daily {category.capitalize()} News ⚡")
    
    # 설명 + 해시태그 결합
    yt_desc = meta_data.get('youtube_description', "")
    hashtags = meta_data.get('hashtags', "")
    if hashtags and hashtags not in yt_desc:
        yt_desc += f"\n\n{hashtags}"
    
    # (B) X (Twitter) 데이터
    x_text = meta_data.get('x_post', "")
    if not x_text: # 만약 비어있다면 유튜브 설명의 앞부분 사용
        x_text = yt_desc[:200]

    # (C) Threads 데이터
    threads_text = meta_data.get('threads_post', "")
    if not threads_text:
        threads_text = yt_desc[:400]

    print(f"\n📝 [Check] Metadata Loaded:")
    print(f"   📺 YouTube Title: {yt_title}")
    print(f"   ❌ X Post: {x_text[:50]}...")
    print(f"   🧵 Threads Post: {threads_text[:50]}...")

    # ==========================================
    # 🚀 [업로드 순서] YouTube -> X -> Threads
    # ==========================================
    
    # 1. YouTube
    print("   🚀 [1/3] Uploading to YouTube...")
    youtube_upload(video_path, category=category, title=yt_title, description=yt_desc)

    # 2. X (Twitter)
    print("   🚀 [2/3] Uploading to X...")
    x_upload(video_path, text=x_text)
    
    # 3. Threads
    print("   🚀 [3/3] Uploading to Threads...")
    time.sleep(5)
    threads_upload(video_path, text=threads_text)
    
    print(f"✨ Job Finished for {category}.\n")

# ====================================================
# ⏳ 24-Hour Schedule Configuration
# ====================================================

# 1. 🌍 U.S. & World News (2회)
schedule.every().day.at("07:00").do(run_job, category="world") 
schedule.every().day.at("17:00").do(run_job, category="world") 

# 2. 💻 Tech & Science News (3회)
schedule.every().day.at("04:00").do(run_job, category="tech")
schedule.every().day.at("13:00").do(run_job, category="tech")
schedule.every().day.at("20:00").do(run_job, category="tech")

# 3. 💰 Finance News (4회)
schedule.every().day.at("03:00").do(run_job, category="finance")
schedule.every().day.at("09:30").do(run_job, category="finance")
schedule.every().day.at("16:30").do(run_job, category="finance")
schedule.every().day.at("21:00").do(run_job, category="finance")

# 4. 🎨 Arts & Culture News (1회)
schedule.every().day.at("14:00").do(run_job, category="art")

# 5. 🏆 Sports News (1회)
schedule.every().day.at("08:00").do(run_job, category="sports")

# 6. 🎬 Entertainment News (1회)
schedule.every().day.at("19:00").do(run_job, category="ent")

if __name__ == "__main__":
    print("🤖 Scheduler Started...")
    print("📅 24-Hour Smart News Cycle Initialized.")
    print("   Order: YouTube -> X -> Threads")
    
    while True:
        schedule.run_pending()
        time.sleep(60)