from playwright.sync_api import sync_playwright
import json
import os
import time
import random
import sys
import argparse

# Windows 콘솔 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# ====================================================
# 🚀 ULTIMATE AUTO UPLOADER (Chrome Version)
# ====================================================

USER_DATA_DIR = os.path.join(os.getcwd(), "browser_profile")

PLAYLIST_MAP = {
    "world": "Daily Top U.S. & World News",
    "tech": "Daily Tech & Science",
    "finance": "Daily Finance & Market",
    "art": "Top Art & Culture Updates",
    "sports": "Daily Sports & Esports",
    "ent": "Quick Entertainment News & Updates"
}

def load_metadata():
    try:
        with open("results/metadata.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def get_latest_video(category):
    suffix_map = {
        "world": "USWORLD", "tech": "TECH", "finance": "FINANCE", 
        "art": "ARTS", "sports": "SPORTS", "ent": "ENT"
    }
    suffix = suffix_map.get(category, "USWORLD")
    target_name = f"final_shorts_{suffix}.mp4"
    
    path = os.path.join("results", target_name)
    if os.path.exists(path):
        return os.path.abspath(path)
    return None

def random_sleep(min_sec=2, max_sec=5):
    time.sleep(random.uniform(min_sec, max_sec))

def reset_browser(page):
    try:
        page.evaluate("window.stop()") 
        page.goto("about:blank") 
        time.sleep(1)
    except: pass

# [CORE] Chrome Stealth Config
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

# ------------------------------------------------------------------
# [Helper] YouTube Security Handler
# ------------------------------------------------------------------
def handle_youtube_security(page):
    print("      🛡️ Checking for YouTube Security Popup...")
    try:
        if page.get_by_text("Verify it's you").is_visible() or \
           page.locator('h1').filter(has_text="Verify").is_visible():
            
            print("      🚨 'Verify it's you' Popup Detected!")
            time.sleep(2)

            next_btn = page.locator('div[role="dialog"]').get_by_role("button", name="Next").first
            
            if not next_btn.is_visible():
                next_btn = page.get_by_role("button", name="Next").last
            
            if not next_btn.is_visible():
                next_btn = page.locator('span, div').filter(has_text="Next").last
            
            if next_btn.is_visible():
                print("      👇 Clicking 'Next' button...")
                next_btn.click(force=True)
                time.sleep(5)
                return True
            else:
                print("      ⚠️ Button unavailable. Trying Keyboard Enter...")
                page.keyboard.press("Enter")
                time.sleep(5)
                return True
    except: pass
    return False

# ------------------------------------------------------------------
# [Helper] X Cloudflare Handler
# ------------------------------------------------------------------
def handle_x_human_verify(page):
    print("      🛡️ Checking for X.com Human Verification...")
    time.sleep(2)
    try:
        if page.get_by_text("Verify you are human").count() > 0:
            print("      🚨 Cloudflare Challenge Detected!")
            for frame in page.frames:
                try:
                    checkbox = frame.locator('input[type="checkbox"]').first
                    if checkbox.is_visible():
                        checkbox.click(force=True)
                        print("      ✅ Clicked Verify Checkbox!")
                        time.sleep(8)
                        return True
                    
                    stage = frame.locator('#challenge-stage').first
                    if stage.is_visible():
                        stage.click(force=True)
                        print("      ✅ Clicked Challenge Stage!")
                        time.sleep(8)
                        return True
                except: continue
    except: pass
    return False

# ------------------------------------------------------------------
# 1. TikTok Upload
# ------------------------------------------------------------------
def upload_tiktok(page, video_path, meta):
    print("   [TikTok] Starting upload...")
    try:
        print("      🌐 Step 1: Visiting TikTok Home...")
        try: page.goto("https://www.tiktok.com/", timeout=60000, wait_until="domcontentloaded")
        except: pass
        time.sleep(5)
        
        try: page.locator('button').filter(has_text="Not now").click()
        except: pass
        try: page.mouse.click(500, 500)
        except: pass

        print("      🌐 Step 2: Navigating via UI...")
        upload_page_reached = False
        upload_btn = page.locator('a[aria-label="Upload"], a[href*="/upload"]').first
        if not upload_btn.is_visible(): upload_btn = page.locator('[data-e2e="upload-icon"]').first

        if upload_btn.is_visible():
            try:
                upload_btn.click()
                time.sleep(8)
                if "upload" in page.url: upload_page_reached = True
            except: pass
        
        if not upload_page_reached:
            try:
                page.goto("https://www.tiktok.com/tiktokstudio/upload?from=creator_center", timeout=60000, wait_until="domcontentloaded")
                time.sleep(5)
            except: pass
        
        file_uploaded = False
        for frame in page.frames:
            try:
                select_btn = frame.locator('button').filter(has_text="Select video").first
                if not select_btn.is_visible(): select_btn = frame.locator('button[aria-label="Select file"]').first
                if select_btn.is_visible():
                    with page.expect_file_chooser(timeout=10000) as fc_info:
                        select_btn.click(force=True)
                    fc_info.value.set_files(video_path)
                    file_uploaded = True
                    break
            except: continue

        if not file_uploaded:
            try:
                page.set_input_files('input[type="file"]', video_path)
                file_uploaded = True
            except: return False

        caption = meta.get('tiktok_post', '')
        time.sleep(8) 
        
        editor = None
        if page.locator('.public-DraftEditor-content').is_visible():
            editor = page.locator('.public-DraftEditor-content').first
        else:
            for frame in page.frames:
                if frame.locator('.public-DraftEditor-content').is_visible():
                    editor = frame.locator('.public-DraftEditor-content').first
                    break
        
        if editor:
            try:
                editor.click()
                time.sleep(0.5)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                editor.fill(caption)
            except: pass
        
        page.mouse.click(0, 0)
        
        for i in range(60): 
            try: page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            except: pass
            
            try:
                if page.locator('button:has-text("Post now")').is_visible():
                    page.locator('button:has-text("Post now")').click()
            except: pass

            post_btn = page.locator('button[data-e2e="post_video_button"]').first
            if not post_btn.is_visible():
                for frame in page.frames:
                    if frame.locator('button[data-e2e="post_video_button"]').is_visible():
                        post_btn = frame.locator('button[data-e2e="post_video_button"]').first
                        break
            
            if post_btn and not post_btn.is_disabled():
                try:
                    post_btn.click(force=True)
                    time.sleep(5)
                except: pass
                if "upload" not in page.url: return True
            time.sleep(5)
        return False
    except: return False

# ------------------------------------------------------------------
# 2. YouTube Upload
# ------------------------------------------------------------------
def upload_youtube(page, video_path, meta, category):
    reset_browser(page)
    print(f"   [YouTube] Starting upload for category: {category}...")
    try:
        page.goto("https://studio.youtube.com/channel/UC/videos/upload?d=ud", timeout=60000, wait_until="domcontentloaded")
        random_sleep(3, 5)

        handle_youtube_security(page)

        try:
            with page.expect_file_chooser(timeout=30000) as fc_info:
                if page.locator('#select-files-button').is_visible():
                    page.click('#select-files-button')
                else:
                    page.click('div#content > input[type="file"]')
            fc_info.value.set_files(video_path)
        except:
            page.set_input_files('input[type="file"]', video_path)

        time.sleep(5) 
        handle_youtube_security(page)

        print("      ⏳ Waiting for upload processing...")
        try:
            page.wait_for_selector('#textbox', state="visible", timeout=60000)
        except:
            if handle_youtube_security(page):
                page.wait_for_selector('#textbox', state="visible", timeout=30000)
            else:
                print("      ⚠️ TextBox not found.")

        random_sleep()

        print("      📝 Inputting Details...")
        title = meta.get('youtube_title', '')[:95]
        try:
            page.locator('#textbox').first.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.type(title, delay=30)
        except: pass
        
        try:
            desc_box = page.locator('#description-container #textbox').first
            if desc_box.is_visible():
                desc_box.fill(meta.get('youtube_description', ''))
                page.get_by_text("Thumbnail", exact=True).first.click()
        except: pass

        playlist_name = PLAYLIST_MAP.get(category)
        if playlist_name:
            try:
                page.locator('span:has-text("Select")').click()
                time.sleep(1)
                page.locator(f'li:has-text("{playlist_name}")').click()
                page.locator('button:has-text("Done")').click()
            except: page.mouse.click(0, 0)

        try: page.locator('[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]').click(force=True)
        except: 
            try: page.locator('div[role="radio"]').filter(has_text="No").first.click(force=True)
            except: pass
        
        random_sleep(2, 3)

        for _ in range(10):
            handle_youtube_security(page)
            if page.locator('h1').filter(has_text="Visibility").is_visible(): break
            
            next_btn = page.locator('#next-button').last
            if not next_btn.is_visible(): next_btn = page.get_by_role("button", name="Next").last
            if next_btn.is_visible(): next_btn.click()
            time.sleep(2)

        print("      🌍 Publishing...")
        try: page.locator('[name="PUBLIC"]').click(force=True)
        except: page.locator('div[role="radio"]').filter(has_text="Public").first.click(force=True)
        time.sleep(2)

        wait_count = 0
        while wait_count < 60:
            status = page.locator("span.progress-label").first
            if status.is_visible() and "Uploading" in status.inner_text():
                print(f"         ⏳ {status.inner_text()}")
                time.sleep(10)
                wait_count += 1
                continue
            break

        publish_btn = page.locator('#done-button').first
        if not publish_btn.is_visible(): publish_btn = page.get_by_role("button", name="Publish").first
        publish_btn.click()
        time.sleep(5)
        
        try: page.locator('button[aria-label="Close"]').click()
        except: pass

        return True
    except Exception as e:
        print(f"   ❌ [YouTube] Failed: {e}")
        return False

# ------------------------------------------------------------------
# 3. X (Twitter) Upload
# ------------------------------------------------------------------
def upload_x(page, video_path, meta):
    reset_browser(page)
    print("   [X / Twitter] Starting upload...")
    try:
        page.goto("https://x.com/compose/post", timeout=60000, wait_until="domcontentloaded")
        random_sleep(4, 6)

        handle_x_human_verify(page)

        try:
            with page.expect_file_chooser(timeout=5000) as fc_info:
                page.locator('button[aria-label="Add photos or video"]').click()
            fc_info.value.set_files(video_path)
        except:
            page.set_input_files('input[type="file"]', video_path)
        
        text = meta.get('x_post', '')
        page.keyboard.type(text)
        time.sleep(5)
        
        post_btn = page.locator('button[data-testid="tweetButton"]')
        for _ in range(30): 
            if not post_btn.is_disabled(): break
            time.sleep(2)
        
        post_btn.click(force=True)
        random_sleep(5, 7)
        return True
    except Exception as e:
        print(f"   ❌ [X] Failed: {e}")
        return False

# ------------------------------------------------------------------
# 4. Threads Upload
# ------------------------------------------------------------------
def upload_threads(page, video_path, meta):
    reset_browser(page)
    print("   [Threads] Starting upload...")
    try:
        page.goto("https://www.threads.net/", timeout=60000, wait_until="domcontentloaded")
        random_sleep(4, 6)
        
        create_btn = page.locator('a[href="/create"], svg[aria-label="Create"]').first
        if create_btn.is_visible(): create_btn.click()
        else: return False

        time.sleep(3) 
        page.keyboard.type(meta.get('threads_post', ''))
        
        try: page.set_input_files('input[type="file"]', video_path)
        except: pass

        time.sleep(5)
        for _ in range(3):
            post_btn = page.locator('div[role="dialog"]').get_by_role("button", name="Post").first
            if post_btn.is_visible():
                post_btn.click(force=True)
                break
            time.sleep(2)

        time.sleep(5)
        if page.get_by_text("Posted").is_visible(): return True
        return True
    except Exception as e:
        print(f"   ❌ [Threads] Failed: {e}")
        return False

# ------------------------------------------------------------------
# 🚀 MAIN CONTROLLER
# ------------------------------------------------------------------
def run_upload_process(category):
    print(f"\n🎬 [Uploader] Starting Multi-Platform Upload for [{category.upper()}]")
    
    video_path = get_latest_video(category)
    meta = load_metadata()
    meta_path = "results/metadata.json"

    if not video_path:
        print("❌ Video file NOT found.")
        return
    if not meta:
        print("❌ Metadata missing.")
        return

    print(f"   📂 Target Video: {video_path}")
    all_completed = False

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            # [CHANGE] Chrome Channel & UA
            channel="chrome",
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-infobars", "--start-maximized"]
        )
        
        apply_stealth(context)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            # 1. Instagram (Skipped)
            # upload_instagram(page, video_path, meta)
            
            # 2. YouTube
            upload_youtube(page, video_path, meta, category)
            
            # 3. X
            upload_x(page, video_path, meta)
            
            # 4. Threads
            upload_threads(page, video_path, meta)

            # 5. TikTok
            upload_tiktok(page, video_path, meta)
            
            print("\n✨ All Upload Tasks Finished!")
            all_completed = True 

        except Exception as e:
            print(f"\n❌ Critical Error during loop: {e}")

        finally:
            context.close()
            if all_completed:
                print("🧹 [Cleanup] Deleting files...")
                try:
                    if os.path.exists(video_path): os.remove(video_path)
                    if os.path.exists(meta_path): os.remove(meta_path)
                    print("✅ Files deleted successfully.")
                except: pass
            else:
                print("🛑 [Safety] Files retained.")

def upload_to_youtube(category="world"):
    run_upload_process(category)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, default="world")
    args = parser.parse_args()
    run_upload_process(args.category)