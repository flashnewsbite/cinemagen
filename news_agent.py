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
    # [업그레이드] 분야별 메이저 언론사 도메인 대거 추가
    TRUSTED_DOMAINS = [
        # World & US
        "cnn.com", "foxnews.com", "reuters.com", "bbc.com", "bbc.co.uk",
        "cbsnews.com", "abcnews.go.com", "usatoday.com", "newsweek.com",
        "nbcnews.com", "apnews.com", "nytimes.com", "washingtonpost.com", 
        "wsj.com", "politico.com", "npr.org",
        
        # Tech & Science
        "techcrunch.com", "wired.com", "theverge.com", "engadget.com", 
        "arstechnica.com", "nasa.gov", "space.com", "science.org", 
        "scientificamerican.com", "gizmodo.com", "cnet.com",
        
        # Finance
        "bloomberg.com", "cnbc.com", "forbes.com", "businessinsider.com", 
        "ft.com", "marketwatch.com", "economist.com",
        
        # Sports
        "espn.com", "bleacherreport.com", "cbssports.com", "si.com", # Sports Illustrated
        "nba.com", "nfl.com", "mlb.com", "ufc.com", "fifa.com", "skysports.com",
        
        # Arts, Culture & Entertainment
        "variety.com", "deadline.com", "hollywoodreporter.com", "billboard.com",
        "rollingstone.com", "vogue.com", "vanityfair.com", "elle.com", 
        "gq.com", "pitchfork.com", "artnews.com"
    ]

    # [봇 차단 우회] 다양한 브라우저 및 OS 신분증 (유지)
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1'
    ]

    def get_daily_news(self, category="world"):
        today = date.today().strftime("%Y-%m-%d")
        
        # [카테고리별 검색어 매핑]
        queries = {
            "world": "Breaking news headlines U.S. World politics economy",
            "tech": "Latest Technology Science news headlines AI Space gadgets",
            "finance": "Financial market news headlines economy stock market business",
            "art": "Latest Arts Culture Fashion news headlines lifestyle",
            "sports": "Top Sports news headlines NFL NBA MLB Soccer UFC stats",
            "ent": "Entertainment news headlines movies music celebrity K-pop"
        }
        
        search_query = queries.get(category, queries["world"])
        print(f"📰 [News] Deep Search Started ({category.upper()})... ({today})")
        
        if Config.SERPER_KEY:
            try:
                # [쿼리 최적화] Min 4개 보장을 위해 후보군 40개 유지
                url = "https://google.serper.dev/news"
                payload = json.dumps({
                    "q": search_query, "gl": "us", "hl": "en", "num": 40, "tbs": "qdr:d"
                })
                headers = {'X-API-KEY': Config.SERPER_KEY, 'Content-Type': 'application/json'}
                response = requests.post(url, headers=headers, data=payload, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    full_reports = []
                    crawled_count = 0
                    
                    print(f"   👉 Search complete. Filtering for trusted '{category}' sources...")

                    for item in data.get("news", []):
                        # [핵심 로직] Max 8개 도달 시 즉시 중단 (유지)
                        if crawled_count >= 8: break
                        
                        link = item.get("link")
                        source = item.get("source", "").lower()
                        
                        # 도메인 추출
                        parsed_uri = urlparse(link)
                        domain = parsed_uri.netloc.lower()
                        if domain.startswith("www."): domain = domain[4:]
                        
                        is_trusted = False
                        for trusted in self.TRUSTED_DOMAINS:
                            # [보안 강화] 도메인 검사 로직 유지
                            if domain == trusted or domain.endswith("." + trusted) or trusted in source:
                                is_trusted = True
                                break
                        
                        if is_trusted:
                            print(f"      📖 Reading ({crawled_count+1}~8): {item.get('title')}...")
                            # [봇 차단 우회] 고급 크롤러 호출
                            article_content = self.get_news_from_url(link)
                            
                            if article_content:
                                full_reports.append(f"--- ARTICLE {crawled_count+1} ({item.get('source')}) ---\n{article_content}\n")
                                crawled_count += 1
                                # 탐지 회피 딜레이 유지
                                time.sleep(random.uniform(1.0, 2.5))
                    
                    # [최소 수량 체크]
                    if crawled_count < 4:
                         print(f"   ⚠️ Warning: Only {crawled_count} trusted articles found. (Target: Min 4)")
                    
                    if full_reports:
                        return "\n".join(full_reports)
                    else:
                        print("   ⚠️ Deep Search failed (No trusted content). Using snippets.")
                        return "\n".join([f"- {i['title']}: {i['snippet']}" for i in data.get("news", [])[:8]])

            except Exception as e:
                print(f"   ⚠️ Serper Error ({e}) -> Switching to RSS Backup")

        return self.get_rss_news()

    def get_rss_news(self):
        # RSS 백업은 가장 일반적인 World News로 유지 (안정성)
        print("   👉 Running RSS Feed Backup (World News)...")
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
                    if desc: desc = desc.split('<')[0]
                    news_items.append(f"- {title}: {desc}")
                    count += 1
                    if count >= 4: break 
                if len(news_items) >= 8: break
            except: continue
            
        if not news_items: return "No news data available at the moment."
        return "\n".join(news_items)

    def get_news_from_url(self, url):
        """
        [Advanced Crawler - 유지]
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
            
            # 2. HTML 직접 다운로드
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
                
            # 3. newspaper3k에게 HTML 주입
            article = Article(url)
            article.download(input_html=response.text)
            article.parse()
            
            if len(article.text) < 200: return None
            
            clean_text = article.text.strip()
            return f"HEADLINE: {article.title}\nFULL TEXT: {clean_text[:3000]}..."
            
        except Exception as e:
            return None