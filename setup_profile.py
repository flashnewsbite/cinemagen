from playwright.sync_api import sync_playwright
import os
import time

# ==============================================================================
# 🔑 LOGIN SESSION SAVER
# 이 스크립트는 브라우저 프로필(쿠키, 세션 등)을 'browser_profile' 폴더에 저장합니다.
# 실행 후 뜨는 브라우저에서 유튜브/틱톡/인스타에 직접 로그인하세요.
# 로그인이 끝나면 터미널에서 엔터를 눌러 종료하면 됩니다.
# ==============================================================================

# 프로필 저장 경로 (이 폴더가 생기면 성공입니다)
USER_DATA_DIR = os.path.join(os.getcwd(), "browser_profile")

def main():
    print("="*60)
    print("🔐 Browser Profile Setup Mode")
    print(f"📂 Profile Path: {USER_DATA_DIR}")
    print("="*60)

    with sync_playwright() as p:
        # 1. 영구 프로필 모드로 브라우저 열기 (headless=False: 화면 보임)
        # args 옵션은 봇 탐지를 피하기 위한 최소한의 설정입니다.
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            viewport={"width": 1280, "height": 720},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        
        page = context.pages[0] if context.pages else context.new_page()

        print("\n🚀 Browser Launched!")
        print("1. Go to YouTube.com and log in.")
        print("2. (Optional) Go to TikTok.com / Instagram.com and log in.")
        print("3. Make sure you can see your channel dashboard/profile.")
        print("\n🛑 When finished, come back here and PRESS ENTER to save & exit.")
        
        # 유튜브 로그인 페이지로 이동 (편의상)
        try:
            page.goto("https://www.youtube.com/upload")
        except:
            pass

        # 사용자가 엔터를 누를 때까지 무한 대기
        input()

        print("💾 Saving profile and closing...")
        context.close()
        print("✅ Done! Profile saved in 'browser_profile' folder.")

if __name__ == "__main__":
    main()