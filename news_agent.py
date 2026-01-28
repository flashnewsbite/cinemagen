import feedparser
import re
import json
import requests
import time
import random
from datetime import datetime
from config import Config
# [필수] Playwright 라이브러리 (pip install playwright && playwright install)
from playwright.sync_api import sync_playwright

class NewsAgent:
    def __init__(self):
        pass

    def clean_html(self, raw_html):
        """RSS Feed용: HTML 태그 및 불필요한 공백 제거"""
        # 1. 스크립트/스타일 태그 내용 제거
        script_pattern = re.compile(r'<(script|style).*?>.*?</\1>', re.DOTALL)
        text = re.sub(script_pattern, ' ', raw_html)
        
        # 2. HTML 태그 제거
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, ' ', text)
        
        # 3. 다중 공백 제거
        return " ".join(cleantext.split())

    # =========================================================================
    # [Option 1] Google News RSS (1순위: Daily News용)
    # =========================================================================
    def get_google_news_rss(self, category="world"):
        print(f"📡 [News] Attempting Primary Source: Google News RSS ({category.upper()})...")
        
        base_url = "https://news.google.com/rss"
        rss_urls = {
            "world": f"{base_url}/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
            "tech": f"{base_url}/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
            "finance": f"{base_url}/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
            "sports": f"{base_url}/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en",
            "ent": f"{base_url}/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en",
            "art": f"{base_url}/search?q=Arts+Culture+Design&hl=en-US&gl=US&ceid=US:en",
            # [추가] Health 카테고리 (RSS 포맷으로 변환됨)
            "health": "https://news.google.com/rss/topics/CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3QwTlRFU0FtVnVLQUFQAQ?hl=en-US&gl=US&ceid=US:en"
        }

        try:
            target_url = rss_urls.get(category, rss_urls["world"])
            feed = feedparser.parse(target_url)
            
            if not feed.entries:
                print("   ⚠️ RSS feed empty. Switching to backup...")
                return None

            top_entries = feed.entries[:8]
            news_context = f"Top {len(top_entries)} Headlines for {category.upper()} News ({datetime.now().strftime('%Y-%m-%d')}):\n\n"

            for i, entry in enumerate(top_entries):
                title = entry.title
                desc = self.clean_html(entry.description) if 'description' in entry else ""
                
                news_context += f"{i+1}. {title}\n"
                news_context += f"   - Snippet: {desc[:200]}...\n\n"
                print(f"   📖 [RSS] Item {i+1}: {title[:40]}...")

            return news_context

        except Exception as e:
            print(f"   ⚠️ RSS Error: {e}")
            return None

    # =========================================================================
    # [Option 2] Serper Search & Snippet (2순위: Daily News 백업용)
    # =========================================================================
    def get_serper_backup(self, category="world"):
        print(f"🔍 [News] Attempting Secondary Source: Serper Search ({category.upper()})...")
        
        url = "https://google.serper.dev/search"
        query_map = {
            "world": "top world news today",
            "tech": "latest technology news today",
            "finance": "top finance business news today",
            "art": "latest arts and culture news today",
            "sports": "top sports news headlines today",
            "ent": "entertainment news headlines today",
            # [추가] Health 백업 검색어
            "health": "top health news headlines medical updates today"
        }
        
        query = query_map.get(category, "latest news today")
        payload = json.dumps({"q": query, "num": 10})
        headers = {'X-API-KEY': Config.SERPER_KEY, 'Content-Type': 'application/json'}

        try:
            response = requests.post(url, headers=headers, data=payload)
            results = response.json()
            
            if "organic" not in results:
                print("   ❌ Backup search failed.")
                return None
                
            items = results["organic"]
            news_context = f"[BACKUP SOURCE] Search Results for {category.upper()} News:\n\n"
            
            count = 0
            for item in items:
                if count >= 8: break
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                
                if len(title) < 5: continue
                
                news_context += f"{count+1}. {title}\n"
                news_context += f"   - Snippet: {snippet}\n"
                news_context += f"   - Source: {link}\n\n"
                print(f"   📖 [Backup] Item {count+1}: {title[:40]}...")
                count += 1
                
            return news_context

        except Exception as e:
            print(f"   ❌ Backup Error: {e}")
            return None

    # =========================================================================
    # 메인 호출 함수 (Main Entry Point)
    # =========================================================================
    def get_daily_news(self, category="world"):
        # 1. RSS 시도
        context = self.get_google_news_rss(category)
        
        # 2. 실패시 백업 시도
        if not context:
            print("⚠️ Primary (RSS) failed. Using Backup (Serper)...")
            context = self.get_serper_backup(category)
            
        if not context:
            print("❌ All news sources failed.")
            return None
            
        return context

    def get_specific_news(self, url):
        """
        [UPGRADED] 특정 URL 딥 크롤링 (Playwright + Visible Browser 모드)
        """
        print(f"🔗 [News] Deep Analyzing with VISIBLE Browser: {url}")
        
        try:
            with sync_playwright() as p:
                # headless=False: 브라우저 창을 실제로 띄웁니다.
                browser = p.chromium.launch(headless=False)
                
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    viewport=None
                )

                context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                page = context.new_page()
                
                print("   ⏳ Loading page (Please do not close the popup)...")
                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    time.sleep(5)
                    try: page.keyboard.press("Escape")
                    except: pass

                    all_paragraphs = page.locator("p").all_inner_texts()
                    valid_paragraphs = [p for p in all_paragraphs if len(p) > 60]
                    content_text = "\n\n".join(valid_paragraphs)
                    
                except Exception as e:
                    print(f"   ⚠️ Page interaction warning: {e}")
                    content_text = ""
                finally:
                    browser.close()

                if len(content_text) < 200:
                    print(f"   ⚠️ Scraped text snippet: {content_text[:100]}...") 
                    raise Exception("Still blocked or content empty.")

                final_text = content_text[:4000]
                final_text = " ".join(final_text.split())

                print(f"   ✅ Content fetched successfully ({len(final_text)} chars)")
                return f"Source Article Content from {url}:\n\n{final_text}..."

        except Exception as e:
            print(f"   ❌ Final Crawling Error: {e}")
            return f"User provided specific URL: {url}. (Crawling failed. Please generate a creative script based on the URL keywords)."