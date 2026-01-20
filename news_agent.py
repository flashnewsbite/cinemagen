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
        "washingtonpost.com", "wsj.com"
    ]

    # [핵심] 봇 차단을 뚫기 위한 다양한 신분증(User-Agents) 리스트
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    ]

    def get_daily_news(self):
        today = date.today().strftime("%Y-%m-%d")
        print(f"📰 [News] 주요 언론사 Deep Search 시작... ({today})")
        
        if Config.SERPER_KEY:
            try:
                query = f"Top breaking news headlines U.S. and World {today}"
                url = "https://google.serper.dev/news"
                payload = json.dumps({
                    "q": query, "gl": "us", "hl": "en", "num": 20, "tbs": "qdr:d"
                })
                headers = {'X-API-KEY': Config.SERPER_KEY, 'Content-Type': 'application/json'}
                response = requests.post(url, headers=headers, data=payload, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    full_reports = []
                    crawled_count = 0
                    
                    print("   👉 검색 완료. 메이저 언론사 위주로 접속 시도 (Anti-Bot 우회)...")

                    for item in data.get("news", []):
                        if crawled_count >= 4: break
                        
                        link = item.get("link")
                        source = item.get("source", "").lower()
                        domain = urlparse(link).netloc.lower()
                        
                        is_trusted = False
                        for trusted in self.TRUSTED_DOMAINS:
                            if trusted in domain or trusted in source:
                                is_trusted = True
                                break
                        
                        if is_trusted:
                            print(f"      📖 Reading: {item.get('title')}...")
                            # [중요] 봇 차단 방지 적용된 크롤링 함수 호출
                            article_content = self.get_news_from_url(link)
                            
                            if article_content:
                                full_reports.append(f"--- ARTICLE {crawled_count+1} ({item.get('source')}) ---\n{article_content}\n")
                                crawled_count += 1
                                # [중요] 너무 빨리 접속하면 차단되므로 1~2초 쉬었다가 다음 기사로 이동
                                time.sleep(random.uniform(1.0, 2.0))
                    
                    if full_reports:
                        return "\n".join(full_reports)
                    else:
                        print("   ⚠️ Deep Search 실패. 일반 요약으로 대체.")
                        return "\n".join([f"- {i['title']}: {i['snippet']}" for i in data.get("news", [])[:5]])

            except Exception as e:
                print(f"   ⚠️ Serper 실패 ({e}) -> RSS 백업 실행")

        return self.get_rss_news()

    def get_rss_news(self):
        # (기존 RSS 코드와 동일하지만, requests에도 헤더 추가)
        print("   👉 RSS Feed (CNN/BBC) 백업 실행...")
        rss_urls = ["http://rss.cnn.com/rss/edition.rss", "http://feeds.bbci.co.uk/news/world/rss.xml"]
        news_items = []
        
        # RSS 요청 때도 봇 차단 방지 헤더 사용
        headers = {'User-Agent': random.choice(self.USER_AGENTS)}
        
        for url in rss_urls:
            try:
                resp = requests.get(url, headers=headers, timeout=5)
                root = ET.fromstring(resp.content)
                count = 0
                for item in root.findall('.//item'):
                    title = item.find('title').text
                    desc = item.find('description').text
                    if desc: desc = desc.split('<')[0]
                    news_items.append(f"- {title}: {desc}")
                    count += 1
                    if count >= 5: break
                if news_items: break
            except: continue
            
        if not news_items: return "No news data available."
        return "\n".join(news_items)

    def get_news_from_url(self, url):
        """강력한 위장술이 적용된 크롤러"""
        
        # [핵심] 매번 접속할 때마다 신분(브라우저)을 랜덤으로 바꿈
        random_user_agent = random.choice(self.USER_AGENTS)
        
        config = NewsConfig()
        config.browser_user_agent = random_user_agent
        config.request_timeout = 10
        
        try:
            article = Article(url, config=config)
            article.download()
            article.parse()
            
            if len(article.text) < 200: return None
            return f"HEADLINE: {article.title}\nFULL TEXT: {article.text[:3000]}..."
        except Exception as e:
            # 403 Forbidden(차단됨) 에러가 나면 조용히 넘어감
            # print(f"      ❌ 접속 차단됨 (Skipping): {e}") 
            return None