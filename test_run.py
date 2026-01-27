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

def get_exact_files(category, timestamp):
    """
    [NEW] 스케줄러와 동일한 방식으로 정확한 파일을 찾습니다.
    """
    cat_upper = category.upper()
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
    if txt_path and os.path.exists(txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if len(content) > 10:
                    return content
        except: pass
    return "#shorts #news"

def run_full_test():
    print(f"\n🧪 Starting Test Run... {datetime.now().strftime('%H:%M:%S')}")
    
    # [설정] 테스트하고 싶은 카테고리 선택
    target_category = "finance"  # world, tech, finance, art, sports, ent
    target_gender = "male"
    target_tone = "1"
    
    # [핵심] 테스트용 타임스탬프 생성
    timestamp = datetime.now().strftime("%m%d%Y_%H%M")
    
    print(f"   ℹ️ Test Config: Category={target_category}, ID={timestamp}")

    # 1. 영상 생성 (main.py 호출 시 timestamp 전달)
    print(f"\n🎬 [Step 1] Generating Video...")
    try:
        subprocess.run([
            "python", "main.py", 
            "--category", target_category, 
            "--gender", target_gender, 
            "--tone", target_tone,
            "--timestamp", timestamp  # [중요] 시간을 지정해서 명령
        ], check=True)
    except Exception as e:
        print(f"❌ Main Process Failed: {e}")
        return

    # 2. 파일 확보
    print("\n📦 [Step 2] Verifying Files...")
    video_path, text_path = get_exact_files(target_category, timestamp)
    
    if not video_path:
        print("❌ Test Aborted: Video file missing.")
        return

    # 3. 업로드 데이터 준비
    yt_title = f"Daily {target_category.capitalize()} News ⚡"
    yt_desc = get_description_content(text_path)
    # X/Threads용 텍스트 (너무 길면 자르기)
    sns_text = yt_desc if len(yt_desc) < 280 else (yt_desc[:250] + "...")

    print(f"\n📝 [Check] Description Preview:\n{'-'*30}\n{yt_desc[:100]}...\n{'-'*30}")

    # 4. 업로드 테스트
    # (원하지 않는 플랫폼은 주석 처리하세요)
    
    # YouTube
    print("\n🟥 YouTube Upload...")
    try: youtube_upload(video_path, category=target_category, title=yt_title, description=yt_desc)
    except Exception as e: print(f"   -> Failed: {e}")
    
    # X (Twitter)
    print("\n⬛ X Upload...")
    try: x_upload(video_path, text=sns_text)
    except Exception as e: print(f"   -> Failed: {e}")
    
    # Threads
    print("\n🧵 Threads Upload...")
    try: threads_upload(video_path, text=sns_text)
    except Exception as e: print(f"   -> Failed: {e}")

    print("\n✨ Test Run Complete.")

if __name__ == "__main__":
    run_full_test()