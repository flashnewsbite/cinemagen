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
    is_morning = 0 <= current_hour < 12  # 오전(00:00 ~ 11:59)
    
    cat_lower = category.lower()
    
    # 1. 뉴스 & 금융 (World, Finance)
    if cat_lower in ['world', 'finance', 'fin', 'us']:
        gender = "male" if is_morning else "female"
        tone = "1"
        
    # 2. 테크 & 과학 (Tech, Science)
    elif cat_lower in ['tech', 'science']:
        gender = "male"
        tone = "2"
        
    # 3. 스포츠 (Sports)
    elif cat_lower in ['sport', 'sports']:
        gender = random.choice(["male", "female"])
        tone = "2"
        
    # 4. 엔터 & 아트 (Ent, Art)
    elif cat_lower in ['ent', 'art', 'arts', 'entertainment']:
        gender = "female"
        tone = "3"
        
    # 기본값
    else:
        gender = "female"
        tone = "2"
        
    return gender, tone

def get_best_description(txt_path, meta_data):
    """
    유튜브 설명을 위한 최적의 텍스트 추출 (우선순위 수정됨)
    1순위: metadata.json의 'youtube_description' (깔끔한 설명)
    2순위: social_metadata.txt (전체 텍스트, 비상용)
    """
    # [수정됨] 1순위: JSON 데이터 먼저 확인
    if meta_data and "youtube_description" in meta_data:
        desc = meta_data["youtube_description"]
        # 내용이 있고(None이 아님) 길이가 충분할 때만 사용
        if desc and len(desc) > 10:
            print("      ✅ Using structured description from metadata.json")
            return desc
    
    # [수정됨] 2순위: TXT 파일 (JSON에 내용이 없을 경우에만 실행)
    if os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if len(content) > 10: 
                    print("      ⚠️ JSON description missing. Using full text file as fallback.")
                    return content
        except: pass
    
    print("      ⚠️ No description found. Using default tags.")
    return "#shorts #news"

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
    """생성된 파일을 찾아서 날짜/시간 이름으로 변경 및 보관"""
    timestamp = datetime.now().strftime("%m%d%Y_%H%M")
    
    src_video = find_video_file(category)
    src_meta  = os.path.join(RESULTS_DIR, "metadata.json")
    src_text  = os.path.join(RESULTS_DIR, "social_metadata.txt")

    new_base_name = f"final_shorts_{category.upper()}_{timestamp}"
    dst_video = os.path.join(RESULTS_DIR, f"{new_base_name}.mp4")
    dst_meta  = os.path.join(RESULTS_DIR, f"{new_base_name}.json")
    dst_text  = os.path.join(RESULTS_DIR, f"{new_base_name}.txt")

    final_data = {'video_path': None, 'meta': {}, 'description': ""}

    # 1. 메타데이터 읽기
    if os.path.exists(src_meta):
        with open(src_meta, 'r', encoding='utf-8') as f:
            final_data['meta'] = json.load(f)

    # 2. 설명 확보 (수정된 함수 사용)
    final_data['description'] = get_best_description(src_text, final_data['meta'])

    # 3. 파일 이동 (Archiving)
    try:
        if os.path.exists(src_text): os.rename(src_text, dst_text)
        if os.path.exists(src_meta): os.rename(src_meta, dst_meta)
        
        if src_video and os.path.exists(src_video):
            os.rename(src_video, dst_video)
            print(f"📦 [Archived] {os.path.basename(dst_video)}")
            final_data['video_path'] = dst_video
        else:
            print(f"❌ Video not found. Category: {category}")
            return None
    except Exception as e:
        print(f"❌ Error moving files: {e}")
        return None

    return final_data

def run_job(category):
    """
    스케줄러 잡 실행 함수
    """
    # 1. AI Director: 성별/톤 결정
    gender, tone = get_voice_settings(category)
    current_time = datetime.now().strftime('%H:%M')
    
    print(f"\n🎬 [{current_time}] Starting Job: Category='{category}'")
    print(f"   🎙️ Voice Director: Gender='{gender.upper()}', Tone='{tone}'")

    # 2. 영상 생성 (main.py 호출)
    try:
        subprocess.run([
            "python", "main.py", 
            "--category", category, 
            "--gender", gender, 
            "--tone", tone
        ], check=True)
    except Exception as e:
        print(f"❌ Generation Failed: {e}")
        return

    # 3. 파일 처리 & 데이터 확보
    data = process_and_archive_files(category)
    if not data or not data['video_path']: return

    # 4. 업로드 데이터 준비
    video_path = data['video_path']
    yt_title = data['meta'].get("youtube_title", f"Daily {category} News")
    yt_desc = data['description'] 
    sns_text = data['meta'].get("x_post", "#Shorts")

    print(f"\n📝 [Check] YouTube Description Preview:\n{'-'*30}\n{yt_desc[:100]}...\n{'-'*30}")

    # 5. YouTube Upload
    print("   🚀 Uploading to YouTube...")
    youtube_upload(video_path, category=category, title=yt_title, description=yt_desc)
    
    # 6. X Upload
    print("   🚀 Uploading to X...")
    x_upload(video_path, text=sns_text)
    
    # 7. Threads Upload
    time.sleep(5)
    print("   🚀 Uploading to Threads...")
    threads_upload(video_path, text=sns_text)
    
    print(f"✨ Job Finished for {category}.\n")

# ====================================================
# ⏳ 24-Hour Schedule Configuration
# ====================================================

# 1. 🌍 U.S. & World News (2회)
schedule.every().day.at("07:00").do(run_job, category="world") # Morning (Male)
schedule.every().day.at("17:00").do(run_job, category="world") # Evening (Female)

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
    print("   (Voice & Tone will be auto-selected based on time & category)")
    
    # [즉시 테스트용] 아래 주석을 풀면 바로 실행해볼 수 있습니다.
    # run_job("world") 

    while True:
        schedule.run_pending()
        time.sleep(60)