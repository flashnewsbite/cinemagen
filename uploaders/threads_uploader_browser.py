from playwright.sync_api import sync_playwright
import os
import time
import random

# ====================================================
# 🧵 Threads Browser Uploader (User Custom Logic)
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
        # headless=False: 브라우저가 뜨는 것을 직접 확인
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False, 
            channel="chrome",
            viewport={"width": 1920, "height": 1080},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-infobars", "--start-maximized"]
        )
        apply_stealth(context)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            # 1. 스레드 접속
            page.goto("https://www.threads.net/", timeout=60000)
            random_sleep(3, 5)

            # [Step 1] 상단 'What's new?' 영역 클릭하여 팝업 띄우기
            print("      1️⃣ Clicking top bar ('What's new?')...")
            
            # 페이지 상단에 있는 "What's new?" 텍스트(또는 입력창 모양)를 찾음
            # placeholder나 text로 찾습니다.
            top_bar = page.get_by_text("What's new?", exact=False).first
            
            # 혹시 못 찾을 경우를 대비해 placeholder도 시도
            if not top_bar.is_visible():
                top_bar = page.get_by_placeholder("What's new?").first
            
            top_bar.click()
            time.sleep(2) # 모달이 뜰 때까지 대기

            # 모달이 떴는지 확인 ('New thread' 라는 제목이 보여야 함)
            if not page.get_by_text("New thread").is_visible():
                print("      ❌ Failed to open modal. Trying fallback click...")
                # 실패 시 강제로 중앙 상단 좌표 클릭 시도 (최후의 수단)
                page.mouse.click(960, 150)
                time.sleep(2)

            # [Step 2 & 3] 모달 내부에서 글 쓰고, 미디어 아이콘 누르기
            print("      2️⃣ Typing text inside modal...")
            
            # 모달 내부의 입력창 클릭
            # (이제 모달이 떴으므로 포커스가 가 있을 확률이 높지만 확실히 하기 위해)
            page.keyboard.type(text)
            random_sleep(1, 2)

            # [중요] 해시태그 드롭다운 메뉴 닫기 (빈 공간 클릭)
            print("      🧹 Clicking empty space to dismiss hashtag menu...")
            # 'New thread' 라는 모달 제목(빈 공간 역할)을 클릭해서 드롭다운을 닫음
            page.get_by_text("New thread").first.click()
            time.sleep(1)

            # [Step 3] 미디어(사진) 아이콘 클릭하여 영상 업로드
            print("      3️⃣ Clicking Media Icon...")
            
            try:
                with page.expect_file_chooser() as fc_info:
                    # 사진 아이콘(갤러리 모양)을 찾음. 보통 svg aria-label이 "Attach media" 이거나 유사함
                    # 사용자가 보여준 위치(입력창 아래)의 첫 번째 svg 버튼을 공략
                    
                    # 방법 A: aria-label로 찾기 (가장 정확)
                    media_btn = page.locator('svg[aria-label="Attach media"]').first
                    if not media_btn.is_visible():
                         media_btn = page.locator('svg[aria-label="미디어 첨부"]').first

                    # 방법 B: 그래도 없으면 아이콘 위치로 추정 (입력창 근처)
                    if not media_btn.is_visible():
                        # role=button 이면서 svg를 포함한 요소 중 두번째 것(첫번째는 보통 프로필)
                        media_btn = page.locator('div[role="button"]:has(svg)').nth(1)

                    media_btn.click()
                
                # 파일 선택
                fc_info.value.set_files(video_path)
                print("      📂 File selected. Uploading...")
            
            except Exception as e:
                print(f"      ⚠️ Icon click failed ({e}). Trying fallback input...")
                page.set_input_files('input[type="file"]', video_path)

            # [Step 4] 업로드 대기 및 'Post' 버튼 활성화 확인
            print("      ⏳ Waiting for preview & Post button...")
            
            # Post 버튼 찾기
            post_btn = page.get_by_text("Post", exact=True).last
            if not post_btn.is_visible():
                post_btn = page.get_by_role("button", name="Post").last
            
            # 버튼이 활성화될 때까지 대기 (최대 60초)
            # 영상이 크면 미리보기가 뜰 때까지 시간이 걸림
            uploaded = False
            for i in range(60):
                # 버튼이 disabled 상태가 아니면 클릭 가능
                if not post_btn.is_disabled():
                    print("      ✅ Button is active!")
                    uploaded = True
                    break
                if i % 5 == 0: print(f"        ... processing video ({i}s)")
                time.sleep(1)
            
            if not uploaded:
                print("❌ Timeout: Post button never became active.")
                return False

            # 한번 더 빈 공간 클릭 (안전장치)
            page.get_by_text("New thread").first.click()
            time.sleep(1)

            # Post 클릭
            print("      🚀 Clicking 'Post'...")
            post_btn.click()

            # [Step 5] 'Posted' 확인 후 종료
            print("      📤 Posting... Waiting for 'Posted' confirmation...")
            
            # 'Posting...' -> 'Posted' 로 바뀌는 것을 감지
            # 혹은 모달이 사라지고 피드에 내 글이 나타나는 것을 확인
            try:
                # 30초 동안 'Posted' 텍스트나 알림을 기다림
                page.wait_for_selector('text="Posted"', timeout=30000)
                print("      ✅ Confirmation received: 'Posted'")
            except:
                print("      ⚠️ No 'Posted' text found, but checking if modal closed...")
                # 모달이 닫혔으면 성공으로 간주
                if not page.get_by_text("New thread").is_visible():
                     print("      ✅ Modal closed. Assuming success.")
                else:
                     print("      ❌ Modal still open. Something went wrong.")
                     return False

            time.sleep(3) # 안정적인 종료를 위해 대기
            print("✅ [Threads] Process Finished Successfully!")
            return True

        except Exception as e:
            print(f"❌ [Threads Browser] Failed: {e}")
            return False
        finally:
            context.close()

if __name__ == "__main__":
    # 테스트 코드
    results_dir = os.path.join(BASE_DIR, "results")
    # 가장 최근에 생성된(타임스탬프가 찍힌) 파일을 찾아서 테스트
    files = [f for f in os.listdir(results_dir) if f.endswith(".mp4")]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(results_dir, x)), reverse=True)
    
    if files:
        target = os.path.join(results_dir, files[0])
        upload_video(target, "User Custom Logic Test 🧵 #Python")
    else:
        print("⚠️ No video file found for testing.")