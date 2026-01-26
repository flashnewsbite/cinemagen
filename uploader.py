from playwright.sync_api import sync_playwright
import json
import os
import time
import random
import sys
import argparse

# Windows 콘솔 인코딩 강제 설정
sys.stdout.reconfigure(encoding='utf-8')

# ====================================================
# 🚀 ULTIMATE AUTO UPLOADER (Stability & Bypass Ver)
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

# 브라우저 상태 초기화 (연쇄 오류 방지)
def reset_browser(page):
    try:
        print("      🔄 Resetting browser state...")
        page.evaluate("window.stop()") # 진행 중인 로딩 강제 중단
        page.goto("about:blank") # 빈 페이지로 이동
        time.sleep(1)
    except: pass

# ------------------------------------------------------------------
# 1. TikTok Upload (commit wait + Fallback)
# ------------------------------------------------------------------
def upload_tiktok(page, video_path, meta):
    print("   [TikTok] Starting upload...")
    try:
        # [Step 1] 메인 홈 진입 (commit 옵션으로 에러 무시하고 진입)
        print("      🌐 Step 1: Visiting TikTok Studio Direct Link...")
        try:
            # wait_until='commit': 서버 응답만 오면 HTML 로딩 안 끝나도 진행 (차단 회피 핵심)
            page.goto("https://www.tiktok.com/tiktokstudio/upload?from=webapp", timeout=60000, wait_until="commit")
        except Exception as e:
            print(f"      ⚠️ Initial Nav Warning (Ignored): {e}")
        
        # 실제 렌더링 대기
        time.sleep(5)
        
        # 팝업 닫기 시도
        try: page.locator('button').filter(has_text="Not now").click()
        except: pass
        page.mouse.click(500, 500)

        # [Step 2] UI 네비게이션
        current_url = page.url
        if "upload" in current_url or "tiktokstudio" in current_url:
             print("      ✅ Already on Upload Page (Skipping UI Nav).")
             upload_page_reached = True
        else:
            print("      🌐 Step 2: Navigating via UI (Home -> Upload)...")
            upload_page_reached = False

            # 1. 업로드 버튼 찾기
            upload_btn = page.locator('a[aria-label="Upload"], a[href*="/upload"]').first
            
            if not upload_btn.is_visible():
                 # 아이콘으로 찾기
                 upload_btn = page.locator('[data-e2e="upload-icon"]').first

            if upload_btn.is_visible():
                print("         ☁️ Found Upload button! Clicking...")
                try:
                    upload_btn.click()
                    # 클릭 후 페이지 이동 대기 (commit)
                    page.wait_for_url("**/upload**", timeout=10000, wait_until="commit")
                    upload_page_reached = True
                except: 
                    print("         ⚠️ Click processed, checking URL...")
        
        # 2. 버튼 실패 시 딥링크 이동 (Fallback)
        if not upload_page_reached or "upload" not in page.url:
            print("         ⚠️ UI Nav failed. Using Creator Center URL Fallback.")
            try:
                page.goto("https://www.tiktok.com/tiktokstudio/upload?from=creator_center", timeout=60000, wait_until="commit")
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
                    with page.expect_file_chooser(timeout=5000) as fc_info:
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
            try:
                page.set_input_files('input[type="file"]', video_path)
                file_uploaded = True
                print("      ✅ File injected (Main Page fallback).")
            except:
                print("      ❌ Critical: Could not upload file.")
                return False

        # 4. 캡션 입력
        caption = meta.get('tiktok_post', '')
        time.sleep(5) 
        editor = page.locator('.public-DraftEditor-content').first
        if not editor.is_visible():
            for frame in page.frames:
                if frame.locator('.public-DraftEditor-content').is_visible():
                    editor = frame.locator('.public-DraftEditor-content').first
                    break
        
        if editor.is_visible():
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

        # 5. 업로드 대기
        print("      ⏳ Waiting for upload & scrolling...")
        
        post_btn_selector = 'button[data-e2e="post_video_button"]'
        fallback_selector = 'button:text-is("Post")' 
        post_btn = None
        
        for i in range(60): 
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.keyboard.press("End")
            except: pass

            if page.locator(post_btn_selector).is_visible():
                post_btn = page.locator(post_btn_selector).first
            elif page.locator(fallback_selector).is_visible():
                post_btn = page.locator(fallback_selector).first
            else:
                for frame in page.frames:
                    if frame.locator(post_btn_selector).is_visible():
                        post_btn = frame.locator(post_btn_selector).first
                        break
                    if frame.locator(fallback_selector).is_visible():
                        post_btn = frame.locator(fallback_selector).first
                        break
            
            if post_btn and post_btn.is_visible() and not post_btn.is_disabled():
                print("      ✨ 'Post' button is ACTIVE!")
                break
            
            if i % 5 == 0: print(f"         ... Processing ({i*5}s)")
            time.sleep(5)

        # 6. Post Loop
        print("      🚀 Entering Post Loop...")
        success = False
        for attempt in range(15):
            try:
                exit_popup = page.locator('div').filter(has_text="Are you sure you want to exit?").first
                if exit_popup.is_visible():
                    print(f"         ⚠️ 'Exit' popup detected! Clicking Cancel...")
                    page.locator('button:has-text("Cancel")').click()
                    time.sleep(1)
                    page.keyboard.press("End")
            except: pass

            try:
                post_now_btn = page.locator('button').filter(has_text="Post now").first
                if post_now_btn.is_visible():
                    post_now_btn.click(force=True)
                    time.sleep(3)
            except: pass

            if post_btn and post_btn.is_visible() and not post_btn.is_disabled():
                print(f"         👇 Clicking 'Post' (Attempt {attempt+1})...")
                try:
                    post_btn.scroll_into_view_if_needed()
                    post_btn.click(force=True)
                except: pass
                time.sleep(5)

            try:
                if page.locator('div:has-text("Video published")').is_visible():
                    print("      🎉 Success! 'Video published' banner.")
                    success = True
                    break
                if page.locator('button:has-text("Upload another video")').is_visible():
                    print("      🎉 Success! 'Upload another video' button.")
                    success = True
                    break
                if "upload" not in page.url:
                    print("      🎉 Success! Page redirected.")
                    success = True
                    break
            except: pass
            
            print("         ⏳ Checking success markers...")
            time.sleep(2)

        if success:
            time.sleep(3)
            return True
        else:
            print("      ❌ TikTok Upload Verification Failed (Time out).")
            return False

    except Exception as e:
        print(f"   ❌ [TikTok] Failed: {e}")
        return False

# ------------------------------------------------------------------
# 2. Instagram Upload
# ------------------------------------------------------------------
def upload_instagram(page, video_path, meta):
    reset_browser(page) # 이전 에러 정리
    print("   [Instagram] Starting upload...")
    try:
        page.goto("https://www.instagram.com/", timeout=60000, wait_until="domcontentloaded")
        random_sleep(4, 6)
        
        try: page.locator('button:has-text("Not Now")').click()
        except: pass

        print("      👆 Hovering over '+' icon...")
        create_clicked = False
        
        # 1. 아이콘 (aria-label) 찾기
        plus_icon = page.locator('svg[aria-label="New post"], svg[aria-label="Create"]').first
        
        if plus_icon.is_visible():
            # [Step 1] Human-like Hover on '+'
            plus_icon.hover()
            print("         Hovered over '+' icon. Waiting...")
            time.sleep(0.8) # User requested ~0.5s+, using 0.8s for safety
            
            # [Step 2] Click 'Create'
            create_text_btn = page.locator('span, div, a').filter(has_text="Create").first
            
            if create_text_btn.is_visible():
                 print("         👇 Clicking 'Create' text button...")
                 create_text_btn.hover() # Move mouse to button first
                 time.sleep(0.2)
                 create_text_btn.click(force=True)
                 create_clicked = True
                 print("         Clicked 'Create'. Waiting...")
                 time.sleep(0.8) # User requested ~0.5s+
            else:
                 # Fallback
                 print("         ⚠️ 'Create' text not found, clicking the icon directly...")
                 plus_icon.click(force=True)
                 create_clicked = True
                 time.sleep(1)
        else:
             print("      ⚠️ '+' Icon not found.")

        # [Step 3] Click 'Post' and Verify Modal
        post_clicked = False
        if create_clicked:
            print("      📜 Checking for 'Post' menu item...")
            for attempt in range(3):
                try:
                    post_menu_item = page.locator('span, div').filter(has_text="Post").first
                    if post_menu_item.is_visible():
                        print(f"         👇 Clicking 'Post' (Attempt {attempt+1})...")
                        post_menu_item.hover()
                        time.sleep(0.3)
                        post_menu_item.click(force=True)
                        time.sleep(3)
                        
                        # 모달 확인 ("Create new post" or "Drag photos and videos here")
                        if page.locator('h1, span').filter(has_text="Create new post").is_visible() or \
                           page.locator('button').filter(has_text="Select from computer").is_visible():
                             print("         ✅ 'Create new post' modal detected!")
                             post_clicked = True
                             break
                        else:
                             print("         ⚠️ Modal not detected, retrying click...")
                    else:
                        print("         ⚠️ 'Post' menu item not visible.")
                        break
                except: pass
                time.sleep(1)

        # 파일 업로드 창 대기
        print("      📂 Waiting for 'Select from computer' button...")
        try:
             # 20초 대기 (네트워크 이슈 대비)
            page.wait_for_selector('button:has-text("Select from computer"), button:has-text("Select")', timeout=20000)
            
            select_btn = page.locator('button').filter(has_text="Select from computer").first
            if not select_btn.is_visible():
                 select_btn = page.locator('button').filter(has_text="Select").first
            
            with page.expect_file_chooser() as fc_info:
                select_btn.click()
            fc_info.value.set_files(video_path)
            print("      ✅ File selected via Chooser!")
        except Exception as e:
            print(f"      ⚠️ Standard select failed ({e}). Trying fallback input injection...")
            try:
                page.set_input_files('input[type="file"]', video_path)
                print("      ✅ Fallback injection success.")
            except: 
                print("      ❌ All file upload methods failed.")
                return False

        print("      ⏳ Waiting for upload preview...")
        try:
            page.wait_for_selector('div[role="dialog"] canvas', timeout=30000)
            print("      ✅ Upload processed.")
        except: return False

        print("      📐 Setting Aspect Ratio to 'Original'...")
        time.sleep(2)
        try:
            crop_btn = page.locator('button[type="button"] svg[aria-label="Select crop"]').first
            if not crop_btn.is_visible():
                crop_btn = page.locator('div[role="dialog"] button').nth(0)
            if crop_btn.is_visible():
                crop_btn.click()
                time.sleep(1) 
                original_btn = page.locator('span:has-text("Original")').first
                if not original_btn.is_visible():
                    original_btn = page.locator('div').filter(has_text="Original").last
                if original_btn.is_visible():
                    original_btn.click()
                    print("         ✅ Selected 'Original'.")
                page.mouse.click(0, 0)
        except: pass

        print("      ➡️ Clicking Next...")
        next_btn = page.locator('div[role="button"]:has-text("Next")')
        if next_btn.first.is_visible(): 
            next_btn.first.click()
            random_sleep(2, 3)
        if next_btn.first.is_visible(): 
            next_btn.first.click()
            random_sleep(2, 3)

        print("      📝 Writing Caption...")
        caption_area = page.locator('div[aria-label="Write a caption..."]').first
        if caption_area.is_visible():
            caption_area.click()
            caption_area.fill(meta.get('instagram_post', '')[:2200])
        
        print("      ✅ Clicking Share...")
        share_btn = page.locator('div[role="button"]:has-text("Share")').first
        share_btn.click()
        
        print("      ⏳ Waiting for upload completion...")
        time.sleep(15) 
        try: page.locator('svg[aria-label="Close"]').click()
        except: page.mouse.click(0, 0)
        return True
    except Exception as e:
        print(f"   ❌ [Instagram] Failed: {e}")
        return False

# ------------------------------------------------------------------
# 3. YouTube Upload
# ------------------------------------------------------------------
def upload_youtube(page, video_path, meta, category):
    reset_browser(page)
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

        print("      📝 Inputting Title...")
        title = meta.get('youtube_title', '')[:95]
        page.locator('#textbox').first.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        page.keyboard.type(title, delay=30)
        page.mouse.click(0, 0) 

        print("      📝 Inputting Description...")
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

        playlist_name = PLAYLIST_MAP.get(category)
        if playlist_name:
            print(f"      📂 Selecting Playlist: {playlist_name}")
            try:
                dropdown = page.locator('span:has-text("Select")').first
                if not dropdown.is_visible():
                     dropdown = page.locator('#basics').get_by_text("Select").first
                dropdown.click()
                time.sleep(1)
                target_playlist = page.locator(f'li:has-text("{playlist_name}")').first
                if target_playlist.is_visible():
                    target_playlist.click()
                page.locator('button:has-text("Done")').click()
            except: page.mouse.click(0, 0)

        print("      👶 Checking 'Not made for kids'...")
        not_kids = page.locator('[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]').first
        if not_kids.is_visible(): 
            not_kids.scroll_into_view_if_needed()
            not_kids.click(force=True)
        else: 
            radio = page.locator('div[role="radio"]').filter(has_text="No, it's not made for kids").first
            if radio.is_visible():
                radio.scroll_into_view_if_needed()
                radio.click(force=True)
        
        random_sleep(2, 3)

        print("      ➡️ Navigating to 'Visibility' step...")
        for attempt in range(10):
            if page.locator('h1').filter(has_text="Visibility").is_visible():
                print("         ✅ Reached Visibility step!")
                break
            
            next_btn = page.locator('#next-button').first
            if not next_btn.is_visible():
                next_btn = page.get_by_role("button", name="Next").first
            
            if next_btn.is_visible() and not next_btn.is_disabled():
                next_btn.click()
                time.sleep(2)
                page.mouse.click(0, 0)
            else:
                time.sleep(2)

        print("      🌍 Setting visibility to Public...")
        time.sleep(2)
        public_btn = page.locator('[name="PUBLIC"]').first
        if not public_btn.is_visible():
             public_btn = page.locator('div[role="radio"]').filter(has_text="Public").first
        
        if public_btn.is_visible():
            public_btn.click(force=True)
            print("         ✅ Selected Public.")

        time.sleep(2)

        print("      🛡️ Checking upload status before publishing...")
        wait_count = 0
        while wait_count < 60:
            status_text = page.locator("span.progress-label").first
            if not status_text.is_visible():
                if page.get_by_text("Uploading").count() > 0:
                    print(f"         ⏳ Still uploading... (Wait {wait_count*10}s)")
                    time.sleep(10)
                    wait_count += 1
                    continue
            else:
                text = status_text.inner_text()
                if "Uploading" in text:
                    print(f"         ⏳ Upload in progress: {text}")
                    time.sleep(10)
                    wait_count += 1
                    continue
            print("         ✅ Upload appears complete. Proceeding to Publish.")
            break

        print("      ✅ Clicking Publish...")
        publish_btn = page.locator('#done-button').first
        if not publish_btn.is_visible():
             publish_btn = page.get_by_role("button", name="Publish").first
        publish_btn.click()
        
        print("      👀 Looking for Close button...")
        close_clicked = False
        for i in range(20):
            close_text_btn = page.get_by_role("button", name="Close").first
            close_icon = page.locator('#close-icon-button').first
            
            if close_text_btn.is_visible() and not close_text_btn.is_disabled():
                close_text_btn.click()
                print("         🔘 Clicked 'Close' (Text).")
                close_clicked = True
                break
            
            if close_icon.is_visible():
                close_icon.click()
                print("         🔘 Clicked 'Close' (Icon).")
                close_clicked = True
                break
            time.sleep(0.5)
            
        if not close_clicked:
            print("         ⚠️ Close button disabled/missing. Trying ESC key...")
            page.keyboard.press("Escape")
            time.sleep(1)

        time.sleep(1)
        return True

    except Exception as e:
        print(f"   ❌ [YouTube] Failed: {e}")
        return False

# ------------------------------------------------------------------
# 4. X (Twitter) Upload
# ------------------------------------------------------------------
def upload_x(page, video_path, meta):
    reset_browser(page)
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
        time.sleep(1)

        print("      🛡️ Dismissing hashtag menu...")
        try: page.locator('div[aria-label="Everyone can reply"]').click()
        except: page.mouse.click(0, 0)
        time.sleep(1)
        
        print("      ⏳ Waiting for video upload...")
        post_btn = page.locator('button[data-testid="tweetButton"]')
        
        for i in range(30): 
            if not post_btn.is_disabled():
                print("      🚀 Upload complete! Button is active.")
                break
            time.sleep(2)
        
        time.sleep(1)
        post_btn.click(force=True)
        random_sleep(5, 7)
        print("      ✅ [X] Upload Success!")
        return True
    except Exception as e:
        print(f"   ❌ [X] Failed: {e}")
        return False

# ------------------------------------------------------------------
# 5. Threads Upload
# ------------------------------------------------------------------
def upload_threads(page, video_path, meta):
    reset_browser(page)
    print("   [Threads] Starting upload...")
    try:
        page.goto("https://www.threads.net/", timeout=60000, wait_until="domcontentloaded")
        random_sleep(4, 6)
        
        print("      👆 Clicking 'Create'...")
        create_btn = page.locator('a[href="/create"]').first
        if not create_btn.is_visible():
            create_btn = page.locator('svg[aria-label="Create"]').first
        if not create_btn.is_visible():
            create_btn = page.locator('div').filter(has_text="What's new?").first

        if create_btn.is_visible():
            create_btn.click()
        else:
            print("      ⚠️ Could not find Create button.")
            return False

        time.sleep(3) 

        print("      📝 Modal opened. Typing caption...")
        page.keyboard.type(meta.get('threads_post', ''))
        time.sleep(1)

        print("      🛡️ Closing hashtag menu (Space key)...")
        page.keyboard.press("Space") 
        time.sleep(1)
        
        save_draft_modal = page.locator('div').filter(has_text="Save to drafts?").first
        if save_draft_modal.is_visible():
            print("      ⚠️ 'Save to drafts' popup detected! Clicking Cancel...")
            page.get_by_role("button", name="Cancel").click()
            time.sleep(1)

        print("      📂 Clicking Media Icon...")
        try:
            with page.expect_file_chooser(timeout=10000) as fc_info:
                media_icon = page.locator('div[role="dialog"] div[role="button"] svg').first
                if media_icon.is_visible():
                    media_icon.click()
                else:
                    print("         ⚠️ Icon invisible, trying hidden input...")
                    page.set_input_files('input[type="file"]', video_path)
            
            fc_info.value.set_files(video_path)
            print("      ✅ File selected.")
        except:
            try: page.set_input_files('input[type="file"]', video_path)
            except: pass

        print("      ⏳ Waiting for video processing overlay to clear (5s)...")
        time.sleep(5)

        print("      🚀 Attempting to Post...")
        for attempt in range(3):
            save_draft_modal = page.locator('div').filter(has_text="Save to drafts?").first
            if save_draft_modal.is_visible():
                print(f"         ⚠️ 'Save to drafts' popup detected (Attempt {attempt+1})! Clicking Cancel...")
                page.get_by_role("button", name="Cancel").click()
                time.sleep(1.5)
            
            post_btn = page.locator('div[role="dialog"]').get_by_role("button", name="Post").first
            if post_btn.is_visible():
                print(f"         👇 Clicking Post button (Attempt {attempt+1})...")
                post_btn.click(force=True)
                
                print("         ⏳ Waiting for upload to finish (Modal closing)...")
                try:
                    page.wait_for_selector('div[role="dialog"]', state="hidden", timeout=60000)
                    break
                except:
                    print("         ⚠️ Modal stuck open. Retrying click or checking for errors...")
            else:
                print("         ⏳ Post button not visible yet...")
                time.sleep(2)

        print("      🔭 Watching for 'Posting...' and 'Posted'...")
        for i in range(150): 
            if page.get_by_text("Posted", exact=True).is_visible():
                print("      🎉 Success! Found 'Posted' confirmation.")
                return True
            if page.get_by_text("Posting...").is_visible():
                if i % 5 == 0: print(f"         ⏳ Still 'Posting...' ({i*2}s)...")
                time.sleep(2)
                continue
            time.sleep(1)

        print("      ⚠️ Timed out waiting for 'Posted' text, but proceeding.")
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

    # [SAFETY LOCK] 완료 확인 플래그
    all_completed = False

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            # [CRITICAL] 1920x1080 Force for Wide UI + Stealth
            viewport={"width": 1920, "height": 1080},
            channel="msedge",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-infobars", "--start-maximized"]
        )
        
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.pages[0] if context.pages else context.new_page()

        try:
            # 1. Instagram (Fixed: Menu Dropdown + Reset)
            upload_instagram(page, video_path, meta)
            
            # 2. YouTube
            upload_youtube(page, video_path, meta, category)
            
            # 3. X
            upload_x(page, video_path, meta)
            
            # 4. Threads
            upload_threads(page, video_path, meta)

            # 5. TikTok (Fixed: Home -> Upload Nav)
            upload_tiktok(page, video_path, meta)
            
            print("\n✨ All Upload Tasks Finished!")
            all_completed = True 

        except Exception as e:
            print(f"\n❌ Critical Error during loop: {e}")

        finally:
            context.close()
            # [SAFETY] 모든 프로세스가 완료된 경우에만 삭제
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