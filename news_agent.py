import requests
import json
import xml.etree.ElementTree as ET
from newspaper import Article
from config import Config
from datetime import date
from urllib.parse import urlparse
import random
import time

class NewsAgent:
    # [유지] 분야별 메이저 언론사 도메인
    TRUSTED_DOMAINS = [
        # World & US
        "cnn.com", "foxnews.com", "reuters.com", "bbc.com", "bbc.co.uk",
        "cbsnews.com", "abcnews.go.com", "usatoday.com", "newsweek.com",
        "nbcnews.com", "apnews.com", "nytimes.com", "washingtonpost.com", 
        "wsj.com", "politico.com", "npr.org", "latimes.com",
        
        # Tech & Science
        "techcrunch.com", "wired.com", "theverge.com", "engadget.com", 
        "arstechnica.com", "nasa.gov", "space.com", "science.org", 
        "scientificamerican.com", "gizmodo.com", "cnet.com", "zdnet.com",
        
        # Finance
        "bloomberg.com", "cnbc.com", "forbes.com", "businessinsider.com", 
        "ft.com", "marketwatch.com", "economist.com", "wsj.com",
        
        # Sports
        "espn.com", "bleacherreport.com", "cbssports.com", "si.com", 
        "nba.com", "nfl.com", "mlb.com", "ufc.com", "fifa.com", "skysports.com",
        "foxsports.com", "nbcsports.com", "sbnation.com", "goal.com", "eurosport.com",
        "theathletic.com", "yahoo.com",
        
        # Arts, Culture & Entertainment
        "variety.com", "deadline.com", "hollywoodreporter.com", "billboard.com",
        "rollingstone.com", "vogue.com", "vanityfair.com", "elle.com", 
        "gq.com", "pitchfork.com", "artnews.com", "tmz.com", "people.com"
    ]

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1'
    ]

    def get_daily_news(self, category="world"):
        today = date.today().strftime("%m-%d-%Y")
        
        # 검색어 튜닝 (광고 필터링)
        queries = {
            "world": "Breaking news headlines U.S. World politics economy -betting",
            "tech": "Latest Technology Science news headlines AI Space gadgets",
            "finance": "Financial market news headlines economy stock market business",
            "art": "Latest Arts Culture Fashion news headlines lifestyle",
            "sports": "Top Sports news headlines NFL NBA MLB Soccer UFC -betting -odds -promo -bonus -code -vegas",
            "ent": "Entertainment news headlines movies music celebrity K-pop"
        }
        
        search_query = queries.get(category, queries["world"])
        print(f"📰 [News] Deep Search Started ({category.upper()})... ({today})")
        
        if Config.SERPER_KEY:
            try:
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
                    
                    spam_keywords = ["betting", "odds", "promo code", "bonus", "gambling", "casino", "parlay", "picks", "prediction"]

                    for item in data.get("news", []):
                        if crawled_count >= 8: break
                        
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        link = item.get("link")
                        source = item.get("source", "").lower()
                        
                        # 스팸 키워드 필터
                        if any(spam in title.lower() for spam in spam_keywords):
                            continue
                        
                        parsed_uri = urlparse(link)
                        domain = parsed_uri.netloc.lower()
                        if domain.startswith("www."): domain = domain[4:]
                        
                        is_trusted = False
                        for trusted in self.TRUSTED_DOMAINS:
                            if domain == trusted or domain.endswith("." + trusted) or trusted in source:
                                is_trusted = True
                                break
                        
                        if is_trusted:
                            print(f"      📖 Reading ({crawled_count+1}~8): {title[:30]}...")
                            article_content = self.get_news_from_url(link)
                            
                            if article_content:
                                full_reports.append(f"--- ARTICLE {crawled_count+1} ({item.get('source')}) ---\n{article_content}\n")
                                crawled_count += 1
                                time.sleep(random.uniform(1.0, 2.5))
                            else:
                                # 크롤링 실패 시 스니펫 대체
                                print(f"         ⚠️ Crawling failed. Using snippet backup.")
                                backup_content = f"HEADLINE: {title}\nFULL TEXT: {snippet} (Source: {source})"
                                full_reports.append(f"--- ARTICLE {crawled_count+1} ({item.get('source')}) ---\n{backup_content}\n")
                                crawled_count += 1
                    
                    # [핵심 수정] 신뢰할 수 있는 기사가 0개면 -> RSS 백업으로 강제 전환
                    if crawled_count == 0:
                        print(f"   ⚠️ No trusted articles found. Switching to Premium RSS Feeds ({category})...")
                        return self.get_rss_news(category)
                    
                    if full_reports:
                        return "\n".join(full_reports)

            except Exception as e:
                print(f"   ⚠️ Serper Error ({e}) -> Switching to RSS Backup")

        return self.get_rss_news(category)

    # [업그레이드] RSS 피드를 카테고리별로 분리
    def get_rss_news(self, category="world"):
        print(f"   👉 Running RSS Feed Backup ({category.upper()})...")
        
        rss_map = {
            "world": [
                "http://rss.cnn.com/rss/edition.rss",
                "http://feeds.bbci.co.uk/news/world/rss.xml",
                "https://feeds.reuters.com/reuters/worldNews"
            ],
            "tech": [
                "https://feeds.feedburner.com/TechCrunch/",
                "https://www.wired.com/feed/rss",
                "https://www.theverge.com/rss/index.xml"
            ],
            "finance": [
                "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
                "https://feeds.marketwatch.com/marketwatch/topstories/"
            ],
            "sports": [
                "https://www.espn.com/espn/rss/news",               # ESPN Top News
                "http://feeds.bbci.co.uk/sport/rss.xml",            # BBC Sports
                "https://sports.yahoo.com/rss/"                     # Yahoo Sports
            ],
            "ent": [
                "https://www.tmz.com/rss.xml",
                "https://editorial.rottentomatoes.com/feed/"
            ],
            "art": [
                "https://www.artnews.com/feed/",
                "https://www.vogue.com/feed/rss"
            ]
        }
        
        rss_urls = rss_map.get(category, rss_map["world"])
        
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
            
        if not news_items: 
            return "No news data available at the moment."
        
        print(f"   ✅ RSS Backup Success: Retrieved {len(news_items)} items.")
        return "\n".join(news_items)

    def get_news_from_url(self, url):
        try:
            headers = {
                'User-Agent': random.choice(self.USER_AGENTS),
                'Referer': 'https://www.google.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
                
            article = Article(url)
            article.download(input_html=response.text)
            article.parse()
            
            if len(article.text) < 100: 
                return None
            
            clean_text = article.text.strip()
            return f"HEADLINE: {article.title}\nFULL TEXT: {clean_text[:3000]}..."
            
        except Exception as e:
            return None