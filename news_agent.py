import feedparser
import re
import json
import requests
from datetime import datetime
from config import Config

class NewsAgent:
    def __init__(self):
        pass

    def clean_html(self, raw_html):
        """HTML 태그 및 불필요한 공백 제거"""
        # 1. 스크립트/스타일 태그 내용 제거 (본문과 섞이지 않게)
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
            "art": f"{base_url}/search?q=Arts+Culture+Design&hl=en-US&gl=US&ceid=US:en"
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
            "ent": "entertainment news headlines today"
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
        [기능 추가] 특정 URL의 본문을 직접 긁어오는 Deep Crawling
        """
        print(f"🔗 [News] Deep Analyzing specific URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        try:
            # 5초 타임아웃을 두고 접속 시도
            response = requests.get(url, headers=headers, timeout=10)
            
            # 403/404 등 에러 체크
            if response.status_code != 200:
                print(f"   ⚠️ URL Access Failed (Status: {response.status_code})")
                return f"User provided specific URL: {url}. (Access denied, please generate generic script based on this topic)."

            # HTML 태그 제거 및 텍스트 정제
            clean_text = self.clean_html(response.text)
            
            # 본문이 너무 길면 AI 토큰 절약을 위해 앞부분 4000자만 사용
            final_text = clean_text[:4000]
            
            print(f"   ✅ Content fetched successfully ({len(final_text)} chars)")
            return f"Source Article Content from {url}:\n\n{final_text}..."

        except Exception as e:
            print(f"   ❌ URL Crawling Error: {e}")
            # 크롤링 실패 시에도 에러로 죽지 않고, URL 주제로 대본을 쓰도록 유도
            return f"User provided specific URL: {url}. (Crawling failed due to {e}, please generate script based on this link's context)."