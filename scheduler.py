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
    [수정됨] 스케줄러가 지정한 timestamp로 정확한 파일 경로를 반환합니다.
    검색(guessing)하지 않고, 지정된 경로를 확인합니다.
    """
    cat_upper = category.upper()
    
    # main.py가 생성하기로 약속된 정확한 파일명 규칙
    base_name = f"final_shorts_{cat_upper}_{timestamp}"
    
    video_path = os.path.join(RESULTS_DIR, f"{base_name}.mp4")
    text_path = os.path.join(RESULTS_DIR, f"{base_name}.txt")
    
    if not os.path.exists(video_path):
        print(f"      ❌ Critical: Expected video file not found!")
        print(f"         Target: {video_path}")
        return None, None

    print(f"      ✅ Verified file exists: {os.path.basename(video_path)}")
    return video_path, text_path

def get_description_content(txt_path):
    """
    TXT 파일 내용을 읽어서 설명을 반환
    """
    if txt_path and os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if len(content) > 10:
                    return content
        except: pass
    
    return "#shorts #news"

def run_job(category):
    """
    스케줄러 잡 실행 함수
    """
    # 1. 작업 ID(Timestamp) 생성 - 스케줄러가 주도권을 가짐
    timestamp = datetime.now().strftime("%m%d%Y_%H%M")
    
    gender, tone = get_voice_settings(category)
    current_time = datetime.now().strftime('%H:%M')
    
    print(f"\n🎬 [{current_time}] Starting Job: Category='{category}' (ID: {timestamp})")
    print(f"   🎙️ Voice Director: Gender='{gender.upper()}', Tone='{tone}'")

    # 2. 영상 생성 요청 (timestamp 전달)
    # main.py에게 "이 시간으로 파일 이름 지어!"라고 명령
    try:
        subprocess.run([
            "python", "main.py", 
            "--category", category, 
            "--gender", gender, 
            "--tone", tone,
            "--timestamp", timestamp  # [핵심] 스케줄러가 시간을 지정해서 전달
        ], check=True)
    except Exception as e:
        print(f"❌ Generation Failed: {e}")
        return

    # 3. [수정됨] 정확한 파일명으로 가져오기
    video_path, text_path = get_exact_files(category, timestamp)
    
    if not video_path:
        print(f"❌ Aborting upload. Job failed for {category}.")
        return

    # 4. 업로드 데이터 준비
    yt_title = f"Daily {category.capitalize()} News ⚡"
    yt_desc = get_description_content(text_path)
    sns_text = yt_desc if len(yt_desc) < 280 else (yt_desc[:250] + "...")

    print(f"\n📝 [Check] Description Preview:\n{'-'*30}\n{yt_desc[:100]}...\n{'-'*30}")

    # ==========================================
    # 🚀 [업로드 순서] YouTube -> X -> Threads
    # ==========================================
    
    # 1. YouTube
    print("   🚀 [1/3] Uploading to YouTube...")
    youtube_upload(video_path, category=category, title=yt_title, description=yt_desc)

    # 2. X (Twitter)
    print("   🚀 [2/3] Uploading to X...")
    x_upload(video_path, text=sns_text)
    
    # 3. Threads
    print("   🚀 [3/3] Uploading to Threads...")
    time.sleep(5)
    threads_upload(video_path, text=sns_text)
    
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