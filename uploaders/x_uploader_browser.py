from playwright.sync_api import sync_playwright
import os
import time
import random

# ====================================================
# ⬛ X (Twitter) Browser Uploader (Fix: Force Click)
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

def handle_human_verify(page):
    time.sleep(2)
    try:
        if page.get_by_text("Verify you are human").count() > 0:
            print("      🚨 Cloudflare Challenge Detected!")
            for frame in page.frames:
                try:
                    checkbox = frame.locator('input[type="checkbox"]').first
                    if checkbox.is_visible():
                        checkbox.click(force=True)
                        time.sleep(3)
                        return True
                except: continue
    except: pass
    return False

def upload_video(video_path, text):
    print(f"🚀 [X Browser] Uploading: {video_path}")
    
    if not os.path.exists(USER_DATA_DIR):
        print("❌ Error: 'browser_profile' not found.")
        return False

    with sync_playwright() as p:
        # 800x600 모니터링 모드 유지
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            channel="chrome",
            viewport={"width": 800, "height": 600},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--window-size=800,600"
            ]
        )
        apply_stealth(context)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto("https://x.com/compose/post", timeout=60000)
            random_sleep(3, 5)
            handle_human_verify(page)

            # 1. 파일 선택
            print("      📂 Selecting video file...")
            try:
                with page.expect_file_chooser(timeout=5000) as fc_info:
                    page.locator('button[aria-label="Add photos or video"]').click()
                fc_info.value.set_files(video_path)
            except:
                page.set_input_files('input[type="file"]', video_path)

            # 2. 텍스트 입력
            print("      📝 Typing caption...")
            page.keyboard.type(text)
            
            # 3. 업로드 완료 대기
            print("      ⏳ Waiting for video upload to complete...")
            
            dialog = page.locator('div[role="dialog"]')
            post_btn = dialog.locator('button[data-testid="tweetButton"]')
            
            if post_btn.count() == 0:
                post_btn = page.locator('button[data-testid="tweetButton"]').last

            is_ready = False
            for i in range(120): 
                if not post_btn.is_disabled():
                    print(f"      ✅ Upload 100% Complete! ({i}s)")
                    is_ready = True
                    break
                if i % 5 == 0: print(f"         ... uploading ({i}s)")
                time.sleep(1)
            
            if not is_ready:
                print("❌ Timeout: Upload took too long.")
                return False

            time.sleep(2)

            # 4. [수정됨] 키보드 단축키로 전송 (강제 클릭 적용)
            print("      ⌨️ Sending Post via Keyboard Shortcut (Ctrl+Enter)...")
            
            # [FIX] force=True: 투명 레이어가 가려도 뚫고 클릭해서 포커스 잡기
            page.locator('div[role="textbox"]').first.click(force=True)
            time.sleep(0.5)
            
            page.keyboard.press("Control+Enter")
            
            # 5. 확인 로직
            print("      📤 Sending... Waiting for confirmation...")
            
            success = False
            for i in range(40):
                if page.locator('text="Your post was sent"').is_visible():
                    print("      ✅ Confirmed: 'Your post was sent' toast message.")
                    success = True
                    break
                
                if page.locator('div[role="dialog"]').count() == 0:
                    if "compose/post" not in page.url:
                        print("      ✅ Confirmed: Modal closed.")
                        success = True
                        break
                
                # 혹시 단축키가 씹혔으면 물리 클릭 시도
                if i == 5 and not success:
                    print("      ⚠️ Shortcut didn't work immediately. Trying physical click as backup...")
                    if post_btn.is_visible() and not post_btn.is_disabled():
                        post_btn.click(force=True)

                time.sleep(1)

            if not success:
                print("      ⚠️ Warning: Confirmation not found, but process finished.")
            
            time.sleep(3)
            print("✅ [X] Process Finished Successfully!")
            return True

        except Exception as e:
            print(f"❌ [X Browser] Failed: {e}")
            return False
        finally:
            context.close()