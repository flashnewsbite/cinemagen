from playwright.sync_api import sync_playwright
import os
import time
import random

# ====================================================
# 🧵 Threads Browser Uploader (Monitoring Mode: 800x600)
# ====================================================

BASE_DIR = os.getcwd()
USER_DATA_DIR = os.path.join(BASE_DIR, "browser_profile")

def random_sleep(min_sec=2, max_sec=5):
    time.sleep(random.uniform(min_sec, max_sec))

def apply_stealth(context):
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    context.add_init_script("window.chrome = { runtime: {} };")
    context.add_init_script("""
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    """)

def upload_video(video_path, text):
    print(f"🧵 [Threads Browser] Uploading: {video_path}")
    
    if not os.path.exists(USER_DATA_DIR):
        print("❌ Error: 'browser_profile' not found.")
        return False

    with sync_playwright() as p:
        # [수정] 800x600 모니터링 모드 설정
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False, 
            channel="chrome",
            viewport={"width": 800, "height": 600}, # 뷰포트 축소
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--window-size=800,600" # 창 크기 고정
                # "--start-maximized" 제거됨
            ]
        )
        apply_stealth(context)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            # 1. 스레드 접속
            page.goto("https://www.threads.net/", timeout=60000)
            random_sleep(3, 5)

            # [Step 1] 상단 'What's new?' 영역 클릭
            print("      1️⃣ Clicking top bar ('What's new?')...")
            
            top_bar = page.get_by_text("What's new?", exact=False).first
            if not top_bar.is_visible():
                top_bar = page.get_by_placeholder("What's new?").first
            
            top_bar.click()
            time.sleep(2)

            if not page.get_by_text("New thread").is_visible():
                print("      ❌ Failed to open modal. Trying fallback click...")
                # 좌표도 작아진 화면에 맞춰 중앙 근처로 조정 (400, 150)
                page.mouse.click(400, 150)
                time.sleep(2)

            # [Step 2] 텍스트 입력
            print("      2️⃣ Typing text inside modal...")
            page.keyboard.type(text)
            random_sleep(1, 2)

            print("      🧹 Clicking empty space to dismiss hashtag menu...")
            page.get_by_text("New thread").first.click()
            time.sleep(1)

            # [Step 3] 미디어 아이콘 클릭
            print("      3️⃣ Clicking Media Icon...")
            try:
                with page.expect_file_chooser() as fc_info:
                    media_btn = page.locator('svg[aria-label="Attach media"]').first
                    if not media_btn.is_visible():
                         media_btn = page.locator('svg[aria-label="미디어 첨부"]').first
                    if not media_btn.is_visible():
                        media_btn = page.locator('div[role="button"]:has(svg)').nth(1)
                    media_btn.click()
                
                fc_info.value.set_files(video_path)
                print("      📂 File selected. Uploading...")
            except Exception as e:
                print(f"      ⚠️ Icon click failed ({e}). Trying fallback input...")
                page.set_input_files('input[type="file"]', video_path)

            # [Step 4] 업로드 대기
            print("      ⏳ Waiting for preview & Post button...")
            
            post_btn = page.get_by_text("Post", exact=True).last
            if not post_btn.is_visible():
                post_btn = page.get_by_role("button", name="Post").last
            
            uploaded = False
            for i in range(60):
                if not post_btn.is_disabled():
                    print("      ✅ Button is active!")
                    uploaded = True
                    break
                if i % 5 == 0: print(f"        ... processing video ({i}s)")
                time.sleep(1)
            
            if not uploaded:
                print("❌ Timeout: Post button never became active.")
                return False

            page.get_by_text("New thread").first.click()
            time.sleep(1)

            # Post 클릭
            print("      🚀 Clicking 'Post'...")
            post_btn.click()

            # [Step 5] 'Posted' 확인
            print("      📤 Posting... Waiting for 'Posted' confirmation...")
            
            try:
                page.wait_for_selector('text="Posted"', timeout=30000)
                print("      ✅ Confirmation received: 'Posted'")
            except:
                print("      ⚠️ No 'Posted' text found, but checking if modal closed...")
                if not page.get_by_text("New thread").is_visible():
                     print("      ✅ Modal closed. Assuming success.")
                else:
                     print("      ❌ Modal still open. Something went wrong.")
                     return False

            time.sleep(3)
            print("✅ [Threads] Process Finished Successfully!")
            return True

        except Exception as e:
            print(f"❌ [Threads Browser] Failed: {e}")
            return False
        finally:
            context.close()