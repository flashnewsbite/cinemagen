import schedule
import time
import subprocess
import sys
from datetime import datetime

# ====================================================
# 🎬 CinemaGen Master Scheduler
# ====================================================

def run_job(category, gender="female", tone="2"):
    """
    지정된 시간에 main.py를 실행하는 함수입니다.
    """
    print(f"\n⏰ [Scheduler] It's time! Starting production for: {category.upper()}")
    
    # main.py를 서브 프로세스로 실행 (독립적으로 실행되어 에러가 나도 스케줄러는 죽지 않음)
    try:
        # 명령어 예: python main.py --category world --gender female --tone 2
        subprocess.run([
            sys.executable, "main.py", 
            "--category", category,
            "--gender", gender,
            "--tone", tone
        ], check=True)
        print(f"✅ [Scheduler] Job Finished: {category.upper()}\n")
        
    except Exception as e:
        print(f"❌ [Scheduler] Job Failed: {e}\n")

def start_schedule():
    print("="*60)
    print("📡 CinemaGen 24/7 Automation Station is ON AIR")
    print(f"🕒 Current System Time: {datetime.now().strftime('%H:%M:%S')}")
    print("❌ To STOP: Press 'Ctrl + C' in this terminal.")
    print("="*60)

    # ----------------------------------------------------
    # 📅 편성표 설정 (Global Target Schedule)
    # ----------------------------------------------------
    
    # 1. 🌍 World (2회)
    schedule.every().day.at("08:00").do(run_job, category="world")
    schedule.every().day.at("18:00").do(run_job, category="world")

    # 2. 💻 Tech (3회)
    schedule.every().day.at("07:00").do(run_job, category="tech")
    schedule.every().day.at("15:00").do(run_job, category="tech")
    schedule.every().day.at("23:00").do(run_job, category="tech")

    # 3. 💰 Finance (4회)
    schedule.every().day.at("02:00").do(run_job, category="finance")
    schedule.every().day.at("08:30").do(run_job, category="finance")
    schedule.every().day.at("16:30").do(run_job, category="finance")
    schedule.every().day.at("20:30").do(run_job, category="finance")

    # 4. 🎨 Arts (1회)
    schedule.every().day.at("13:00").do(run_job, category="art")

    # 5. 🎬 Ent (1회)
    schedule.every().day.at("19:00").do(run_job, category="ent")

    # 6. 🏆 Sports (1회)
    schedule.every().day.at("22:00").do(run_job, category="sports")

    # ----------------------------------------------------
    # 무한 루프 (시계 감시)
    # ----------------------------------------------------
    while True:
        # 예약된 작업이 있는지 1초마다 확인
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    start_schedule()