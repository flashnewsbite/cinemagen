import requests
import json
import xml.etree.ElementTree as ET
from newspaper import Article, Config as NewsConfig
from config import Config
from datetime import date
from urllib.parse import urlparse
import random
import time

class NewsAgent:
    TRUSTED_DOMAINS = [
        "cnn.com", "foxnews.com", "reuters.com", "bbc.com", "bbc.co.uk",
        "cbsnews.com", "abcnews.go.com", "usatoday.com", "newsweek.com",
        "bloomberg.com", "nbcnews.com", "apnews.com", "nytimes.com", 
        "washingtonpost.com", "wsj.com", "cnbc.com", "politico.com"
    ]

    # [봇 차단 우회] 다양한 브라우저 및 OS 신분증
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1'
    ]

    def get_daily_news(self):
        today = date.today().strftime("%Y-%m-%d")
        print(f"📰 [News] Deep Search Started... ({today})")
        
        if Config.SERPER_KEY:
            try:
                # [쿼리 최적화] 날짜 텍스트 제거하고 tbs 파라미터로 최신성 보장
                query = "Breaking news headlines U.S. World politics economy"
                url = "https://google.serper.dev/news"
                payload = json.dumps({
                    "q": query, "gl": "us", "hl": "en", "num": 20, "tbs": "qdr:d" # qdr:d = 지난 24시간
                })
                headers = {'X-API-KEY': Config.SERPER_KEY, 'Content-Type': 'application/json'}
                response = requests.post(url, headers=headers, data=payload, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    full_reports = []
                    crawled_count = 0
                    
                    print("   👉 Search complete. Attempting to access major sources...")

                    for item in data.get("news", []):
                        if crawled_count >= 4: break
                        
                        link = item.get("link")
                        source = item.get("source", "").lower()
                        
                        # 도메인 추출
                        parsed_uri = urlparse(link)
                        domain = parsed_uri.netloc.lower()
                        # www. 제거 (매칭 정확도 향상)
                        if domain.startswith("www."): domain = domain[4:]
                        
                        is_trusted = False
                        for trusted in self.TRUSTED_DOMAINS:
                            # [보안 강화] 'fake-cnn.com' 방지를 위해 endswith 사용
                            if domain == trusted or domain.endswith("." + trusted) or trusted in source:
                                is_trusted = True
                                break
                        
                        if is_trusted:
                            print(f"      📖 Reading: {item.get('title')}...")
                            article_content = self.get_news_from_url(link)
                            
                            if article_content:
                                full_reports.append(f"--- ARTICLE {crawled_count+1} ({item.get('source')}) ---\n{article_content}\n")
                                crawled_count += 1
                                time.sleep(random.uniform(1.5, 3.0)) # 딜레이 약간 증가
                    
                    if full_reports:
                        return "\n".join(full_reports)
                    else:
                        print("   ⚠️ Deep Search failed (No trusted content). Using snippets.")
                        return "\n".join([f"- {i['title']}: {i['snippet']}" for i in data.get("news", [])[:5]])

            except Exception as e:
                print(f"   ⚠️ Serper Error ({e}) -> Switching to RSS Backup")

        return self.get_rss_news()

    def get_rss_news(self):
        print("   👉 Running RSS Feed Backup...")
        # RSS 소스 추가
        rss_urls = [
            "http://rss.cnn.com/rss/edition.rss",
            "http://feeds.bbci.co.uk/news/world/rss.xml",
            "https://feeds.reuters.com/reuters/worldNews"
        ]
        news_items = []
        headers = {'User-Agent': random.choice(self.USER_AGENTS)}
        
        for url in rss_urls:
            try:
                resp = requests.get(url, headers=headers, timeout=5)
                root = ET.fromstring(resp.content)
                count = 0
                for item in root.findall('.//item'):
                    title = item.find('title').text
                    desc = item.find('description').text
                    if desc: desc = desc.split('<')[0] # HTML 태그 제거
                    news_items.append(f"- {title}: {desc}")
                    count += 1
                    if count >= 3: break # 소스당 3개씩
                if len(news_items) >= 5: break
            except: continue
            
        if not news_items: return "No news data available at the moment."
        return "\n".join(news_items)

    def get_news_from_url(self, url):
        """
        [Advanced Crawler]
        requests로 HTML을 먼저 가져오고(헤더 조작), 
        newspaper3k는 파싱만 담당하게 하여 차단을 회피함.
        """
        try:
            # 1. 헤더 조작 (브라우저인 척)
            headers = {
                'User-Agent': random.choice(self.USER_AGENTS),
                'Referer': 'https://www.google.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }
            
            # 2. HTML 직접 다운로드 (requests 사용)
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
                
            # 3. newspaper3k에게 HTML 넘겨주기
            article = Article(url)
            article.download(input_html=response.text) # 다운로드 단계 건너뛰고 HTML 주입
            article.parse()
            
            if len(article.text) < 200: return None
            
            # 텍스트 정리
            clean_text = article.text.strip()
            return f"HEADLINE: {article.title}\nFULL TEXT: {clean_text[:3000]}..."
            
        except Exception as e:
            # print(f"      ❌ Access Denied or Error: {e}")
            return None