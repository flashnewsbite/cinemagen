from playwright.sync_api import sync_playwright
import os
import time
import sys

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# 🔑 LOGIN SESSION SAVER (Chrome Version)
# ==============================================================================

USER_DATA_DIR = os.path.join(os.getcwd(), "browser_profile")

# [CORE] 스텔스 모드 (Chrome용)
def apply_stealth(context):
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    context.add_init_script("window.chrome = { runtime: {} };")
    context.add_init_script("""
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    """)
    context.add_init_script("""
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: 'denied' }) :
            originalQuery(parameters)
        );
    """)

def main():
    print("="*60)
    print("🔐 Browser Profile Setup Mode (Google Chrome)")
    print(f"📂 Profile Path: {USER_DATA_DIR}")
    print("="*60)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            viewport={"width": 1920, "height": 1080},
            # [CHANGE] Chrome 사용
            channel="chrome", 
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized",
                "--disable-infobars"
            ]
        )
        
        apply_stealth(context)
        page = context.pages[0] if context.pages else context.new_page()

        print("\n🚀 Browser Launched (Chrome)!")
        print("👇 Please perform the following steps manually:")
        print("1. Go to YouTube.com/upload -> If 'Verify it's you' appears, PASS IT manually.")
        print("2. Go to X.com -> Solve any Cloudflare checks or login challenges.")
        print("3. Go to TikTok.com -> Upload button -> Ensure no captchas appear.")
        print("4. Go to Instagram.com -> Ensure you are logged in.")
        print("\n🛑 When fully logged in on all sites, come back here and PRESS ENTER.")
        
        try:
            page.goto("https://studio.youtube.com/")
        except: pass

        input()

        print("💾 Saving cookies/session and closing...")
        context.close()
        print("✅ Done! Profile updated.")

if __name__ == "__main__":
    main()