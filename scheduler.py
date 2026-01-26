import schedule
import time
import subprocess
import sys
from datetime import datetime
import ctypes

# ====================================================
# 🎬 CinemaGen Master Scheduler (Create -> Upload)
# ====================================================

def prevent_sleep():
    """PC 절전 모드 방지 (모니터는 꺼져도 됨)"""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        print("🔋 [Power] Anti-Sleep Mode Activated!")
    except Exception as e:
        print(f"⚠️ [Power] Failed to set Anti-Sleep: {e}")

def run_job(category, gender="female", tone="2"):
    print(f"\n⏰ [Scheduler] It's time! Starting workflow for: {category.upper()}")
    
    try:
        # 1. 영상 제작 (main.py)
        print(f"   🔨 [1/2] Generating Video ({category})...")
        subprocess.run([
            sys.executable, "main.py", 
            "--category", category,
            "--gender", gender,
            "--tone", tone
        ], check=True)
        
        # 2. 영상 업로드 (uploader.py) - 인스타그램 제외됨
        print(f"   🚀 [2/2] Uploading Video ({category})...")
        subprocess.run([
            sys.executable, "uploader.py", 
            "--category", category
        ], check=True)

        print(f"✅ [Scheduler] Workflow Finished: {category.upper()}\n")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ [Scheduler] Process Error: {e}")
    except Exception as e:
        print(f"❌ [Scheduler] Unexpected Error: {e}\n")

def start_schedule():
    print("="*60)
    print("📡 CinemaGen 24/7 Automation Station is ON AIR")
    print(f"🕒 Current System Time: {datetime.now().strftime('%H:%M:%S')}")
    print("❌ To STOP: Press 'Ctrl + C' in this terminal.")
    print("="*60)
    
    prevent_sleep()

    # ----------------------------------------------------
    # 📅 편성표 (영상 생성 -> 업로드)
    # ----------------------------------------------------
    
    # 1. 🌍 World
    schedule.every().day.at("08:00").do(run_job, category="world")
    schedule.every().day.at("18:00").do(run_job, category="world")

    # 2. 💻 Tech
    schedule.every().day.at("07:00").do(run_job, category="tech")
    schedule.every().day.at("15:00").do(run_job, category="tech")
    schedule.every().day.at("23:00").do(run_job, category="tech")

    # 3. 💰 Finance
    schedule.every().day.at("02:00").do(run_job, category="finance")
    schedule.every().day.at("08:30").do(run_job, category="finance")
    schedule.every().day.at("16:30").do(run_job, category="finance")
    schedule.every().day.at("20:30").do(run_job, category="finance")

    # 4. 🎨 Arts
    schedule.every().day.at("13:00").do(run_job, category="art")

    # 5. 🎬 Ent
    schedule.every().day.at("19:00").do(run_job, category="ent")

    # 6. 🏆 Sports
    schedule.every().day.at("22:00").do(run_job, category="sports")

    # ----------------------------------------------------
    # 무한 루프
    # ----------------------------------------------------
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    start_schedule()