from playwright.sync_api import sync_playwright
# [CRITICAL] 틱톡 차단 방지를 위해 필수
from playwright_stealth import stealth_sync 
import json
import os
import time
import random
import sys
import argparse

# Windows 콘솔 인코딩 강제 설정
sys.stdout.reconfigure(encoding='utf-8')

# ====================================================
# 🚀 ULTIMATE AUTO UPLOADER (24/7 Stable Version)
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

# ------------------------------------------------------------------
# 1. TikTok Upload (Stealth + Home Entry + Fallback)
# ------------------------------------------------------------------
def upload_tiktok(page, video_path, meta):
    print("   [TikTok] Starting upload...")
    try:
        # [Step 1] 메인 홈 진입 (Stealth 모드 적용됨)
        print("      🌐 Step 1: Visiting TikTok Home...")
        try:
            # wait_until='commit': 서버 응답만 오면 진행 (차단 회피에 유리)
            page.goto("https://www.tiktok.com/", timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"      ⚠️ Initial Nav Warning: {e}")
        
        time.sleep(5)
        
        # 팝업 닫기
        try: page.locator('button').filter(has_text="Not now").click()
        except: pass
        try: page.mouse.click(500, 500)
        except: pass

        # [Step 2] UI 네비게이션
        print("      🌐 Step 2: Navigating via UI (Home -> Upload)...")
        upload_page_reached = False

        # 1. 업로드 버튼 찾기
        upload_btn = page.locator('a[aria-label="Upload"], a[href*="/upload"]').first
        if not upload_btn.is_visible():
             upload_btn = page.locator('[data-e2e="upload-icon"]').first

        if upload_btn.is_visible():
            print("         ☁️ Found Upload button! Clicking...")
            try:
                upload_btn.click()
                time.sleep(8) # 페이지 이동 대기
                if "upload" in page.url:
                    upload_page_reached = True
            except: pass
        
        # 2. 버튼 실패 시 딥링크 이동 (Creator Center)
        if not upload_page_reached:
            print("         ⚠️ UI Nav failed. Using Creator Center URL Fallback.")
            try:
                page.goto("https://www.tiktok.com/tiktokstudio/upload?from=creator_center", timeout=60000, wait_until="domcontentloaded")
                time.sleep(5)
            except: pass
        
        print("      ⏳ Waiting for page layout...")
        time.sleep(5)

        # [Step 3] 파일 업로드
        print("      📂 Searching for 'Select video' button...")
        file_uploaded = False

        # 전략 A: 버튼 클릭
        for frame in page.frames:
            try:
                select_btn = frame.locator('button').filter(has_text="Select video").first
                if not select_btn.is_visible():
                    select_btn = frame.locator('button[aria-label="Select file"]').first
                
                if select_btn.is_visible():
                    print(f"         Found select button in frame: {frame.url}")
                    with page.expect_file_chooser(timeout=10000) as fc_info:
                        select_btn.click(force=True)
                    fc_info.value.set_files(video_path)
                    file_uploaded = True
                    print("      ✅ File selected via Button!")
                    break
            except: continue

        # 전략 B: 직접 주입
        if not file_uploaded:
            print("      ⚠️ Button click failed. Trying Direct Input Injection...")
            for frame in page.frames:
                try:
                    input_loc = frame.locator('input[type="file"]')
                    if input_loc.count() > 0:
                        input_loc.set_input_files(video_path)
                        file_uploaded = True
                        print("      ✅ File injected directly into input!")
                        break
                except: continue

        if not file_uploaded:
            # 최후의 수단: 메인 페이지 강제 주입
            try:
                page.set_input_files('input[type="file"]', video_path)
                file_uploaded = True
                print("      ✅ File injected (Main Page fallback).")
            except:
                print("      ❌ Critical: Could not upload file.")
                return False

        # 4. 캡션 입력
        caption = meta.get('tiktok_post', '')
        time.sleep(8) # 업로드 처리 대기
        
        editor = None
        if page.locator('.public-DraftEditor-content').is_visible():
            editor = page.locator('.public-DraftEditor-content').first
        else:
            for frame in page.frames:
                if frame.locator('.public-DraftEditor-content').is_visible():
                    editor = frame.locator('.public-DraftEditor-content').first
                    break
        
        if editor:
            print("      📝 Clearing filename & typing caption...")
            try:
                editor.click()
                time.sleep(0.5)
                page.keyboard.press("Control+A")
                time.sleep(0.5)
                page.keyboard.press("Backspace")
                time.sleep(0.5)
                editor.fill(caption)
            except: pass
        
        page.mouse.click(0, 0)

        # 5. 업로드 대기 & Post
        print("      ⏳ Waiting for upload & scrolling...")
        post_btn_selector = 'button[data-e2e="post_video_button"]'
        
        for i in range(60): 
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.keyboard.press("End")
            except: pass

            # Post now (저작권 확인 등) 팝업 처리
            try:
                post_now = page.locator('button').filter(has_text="Post now").first
                if post_now.is_visible():
                    post_now.click(force=True)
            except: pass

            post_btn = None
            if page.locator(post_btn_selector).is_visible():
                post_btn = page.locator(post_btn_selector).first
            else:
                for frame in page.frames:
                    if frame.locator(post_btn_selector).is_visible():
                        post_btn = frame.locator(post_btn_selector).first
                        break
            
            if post_btn and not post_btn.is_disabled():
                print("      ✨ 'Post' button is ACTIVE! Clicking...")
                try:
                    post_btn.click(force=True)
                    time.sleep(5)
                except: pass
                
                # 성공 체크
                if page.locator('div:has-text("Video published")').is_visible() or \
                   page.locator('button:has-text("Upload another video")').is_visible() or \
                   "upload" not in page.url:
                    print("      🎉 Success! Video published.")
                    return True
            
            if i % 5 == 0: print(f"         ... Processing ({i*5}s)")
            time.sleep(5)

        print("      ❌ TikTok Upload Timed Out.")
        return False

    except Exception as e:
        print(f"   ❌ [TikTok] Failed: {e}")
        return False

# ------------------------------------------------------------------
# 2. YouTube Upload
# ------------------------------------------------------------------
def upload_youtube(page, video_path, meta, category):
    print(f"   [YouTube] Starting upload for category: {category}...")
    try:
        page.goto("https://studio.youtube.com/channel/UC/videos/upload?d=ud", timeout=60000, wait_until="domcontentloaded")
        random_sleep(3, 5)

        try:
            with page.expect_file_chooser(timeout=30000) as fc_info:
                if page.locator('#select-files-button').is_visible():
                    page.click('#select-files-button')
                else:
                    page.click('div#content > input[type="file"]')
            fc_info.value.set_files(video_path)
        except:
            page.set_input_files('input[type="file"]', video_path)

        print("      ⏳ Waiting for upload processing...")
        page.wait_for_selector('#textbox', state="visible", timeout=60000)
        random_sleep()

        print("      📝 Inputting Details...")
        title = meta.get('youtube_title', '')[:95]
        page.locator('#textbox').first.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        page.keyboard.type(title, delay=30)
        
        desc = meta.get('youtube_description', '')
        try:
            desc_box = page.locator('#description-container #textbox').first
            if desc_box.is_visible():
                desc_box.click()
                time.sleep(0.5)
                desc_box.fill(desc)
                time.sleep(1)
                page.get_by_text("Thumbnail", exact=True).first.click()
        except: pass

        # 아동용 설정
        not_kids = page.locator('[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]').first
        if not_kids.is_visible(): not_kids.click(force=True)
        else: 
            radio = page.locator('div[role="radio"]').filter(has_text="No, it's not made for kids").first
            if radio.is_visible(): radio.click(force=True)
        
        random_sleep(2, 3)

        # Visibility 단계로 이동
        for _ in range(10):
            if page.locator('h1').filter(has_text="Visibility").is_visible(): break
            next_btn = page.locator('#next-button').first
            if not next_btn.is_visible(): next_btn = page.get_by_role("button", name="Next").first
            if next_btn.is_visible(): next_btn.click()
            time.sleep(2)

        # 공개
        print("      🌍 Publishing...")
        public_btn = page.locator('[name="PUBLIC"]').first
        if not public_btn.is_visible(): public_btn = page.locator('div[role="radio"]').filter(has_text="Public").first
        public_btn.click(force=True)
        time.sleep(2)

        # 완료 대기
        wait_count = 0
        while wait_count < 60:
            status_text = page.locator("span.progress-label").first
            if status_text.is_visible() and "Uploading" in status_text.inner_text():
                print(f"         ⏳ Uploading... {status_text.inner_text()}")
                time.sleep(10)
                wait_count += 1
                continue
            break

        publish_btn = page.locator('#done-button').first
        if not publish_btn.is_visible(): publish_btn = page.get_by_role("button", name="Publish").first
        publish_btn.click()
        time.sleep(5)
        
        return True

    except Exception as e:
        print(f"   ❌ [YouTube] Failed: {e}")
        return False

# ------------------------------------------------------------------
# 3. X (Twitter) Upload
# ------------------------------------------------------------------
def upload_x(page, video_path, meta):
    print("   [X / Twitter] Starting upload...")
    try:
        page.goto("https://x.com/compose/post", timeout=60000, wait_until="domcontentloaded")
        random_sleep(4, 6)

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
    print("   [Threads] Starting upload...")
    try:
        page.goto("https://www.threads.net/", timeout=60000, wait_until="domcontentloaded")
        random_sleep(4, 6)
        
        create_btn = page.locator('a[href="/create"], svg[aria-label="Create"]').first
        if create_btn.is_visible(): create_btn.click()
        else: 
            print("      ⚠️ Create button not found.")
            return False

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
        # 성공 확인
        if page.get_by_text("Posted").is_visible() or page.get_by_text("Posting...").is_visible():
             print("      🎉 Threads Success!")
             return True
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
        print(f"❌ Video file NOT found for category: '{category}'")
        return
    if not meta:
        print("❌ Metadata file missing.")
        return

    print(f"   📂 Target Video: {video_path}")

    all_completed = False

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            # [CRITICAL] 1920x1080 + Stealth
            viewport={"width": 1920, "height": 1080},
            channel="msedge",
            # 일반 User-Agent
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-infobars", "--start-maximized"]
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        # [CRITICAL] 봇 탐지 회피 (스텔스 모드 적용)
        stealth_sync(page)

        try:
            # 1. Instagram (사용자 요청으로 제외)
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
            # 파일 삭제 (모두 완료 시에만)
            if all_completed:
                print("🧹 [Cleanup] Deleting files...")
                try:
                    if os.path.exists(video_path): os.remove(video_path)
                    if os.path.exists(meta_path): os.remove(meta_path)
                    print("✅ Files deleted successfully.")
                except Exception as e:
                    print(f"⚠️ Cleanup failed: {e}")
            else:
                print("🛑 [Safety] Files were NOT deleted because the process did not finish.")

def upload_to_youtube(category="world"):
    run_upload_process(category)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", type=str, default="world", help="Target category (world, tech, finance, art, sports, ent)")
    args = parser.parse_args()
    run_upload_process(args.category)