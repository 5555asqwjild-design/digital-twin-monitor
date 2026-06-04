"""
资讯监控器 - 数据抓取模块
支持 RSS、API、HTML 三种抓取方式
覆盖：数字孪生 + 全球局势
"""
import re
import time
import json
import hashlib
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import asdict
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import SOURCES, MAX_ARTICLES_PER_BATCH


class Article:
    """标准化文章结构"""
    def __init__(self, title: str, url: str, source: str, published: Optional[datetime] = None,
                 summary: str = "", content: str = "", author: str = "", category: str = "digital_twin"):
        self.title = title
        self.url = url
        self.source = source
        self.published = published or datetime.now()
        self.summary = summary
        self.content = content
        self.author = author
        self.category = category
        self.id = hashlib.md5(f"{title}:{url}".encode()).hexdigest()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published": self.published.isoformat() if self.published else None,
            "summary": self.summary,
            "author": self.author,
            "category": self.category,
        }

    def __repr__(self):
        return f"<Article [{self.category}] {self.source}: {self.title[:50]}...>"


class BaseScraper:
    """基础抓取器"""
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    def __init__(self, source):
        self.source = source
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def fetch(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"[ERROR] 抓取失败 {url}: {e}")
            return None

    def parse(self, html: str) -> List[Article]:
        raise NotImplementedError

    def scrape(self) -> List[Article]:
        html = self.fetch(self.source.url)
        if not html:
            return []
        articles = self.parse(html)
        for a in articles:
            a.source = self.source.name
            a.category = self.source.category
        return articles


# ============================================================
# 数字孪生数据源抓取器
# ============================================================

class DigitalTwinConsortiumScraper(BaseScraper):
    """Digital Twin Consortium Blog"""
    def parse(self, html: str) -> List[Article]:
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        for item in soup.select(".entry")[:10]:
            link = item.find("a", href=True)
            if not link:
                continue
            title = link.get_text(strip=True)
            url = link["href"]
            if not url.startswith("http"):
                url = urljoin(self.source.url, url)
            date_match = re.search(r'/(\d{4})/(\d{2})/', url)
            published = None
            if date_match:
                try:
                    published = datetime(int(date_match.group(1)), int(date_match.group(2)), 1)
                except:
                    pass
            articles.append(Article(title=title, url=url, published=published, source=""))
        return articles


class OGCScraper(BaseScraper):
    """OGC Blog"""
    def parse(self, html: str) -> List[Article]:
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        for item in soup.select(".e-loop-item")[:10]:
            link = item.find("a", href=True)
            if not link:
                continue
            title = link.get_text(strip=True)
            url = link["href"]
            if not url.startswith("http"):
                url = urljoin(self.source.url, url)
            articles.append(Article(title=title, url=url, source=""))
        return articles


class UnrealEngineScraper(BaseScraper):
    """Unreal Engine Blog - 使用 RSS Feed，带关键词过滤"""
    def scrape(self) -> List[Article]:
        feed_url = "https://www.unrealengine.com/rss"
        try:
            feed = feedparser.parse(feed_url)
            articles = []
            for entry in feed.entries[:15]:
                title = re.sub(r'<[^>]+>', '', entry.title)
                if not any(kw.lower() in title.lower() for kw in self.source.keywords):
                    continue
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                articles.append(Article(
                    title=title, url=entry.link, published=published, source=""
                ))
            return articles
        except Exception as e:
            print(f"[ERROR] UE RSS解析失败: {e}")
            return []


class NVIDIAScraper(BaseScraper):
    """NVIDIA Developer Blog"""
    def parse(self, html: str) -> List[Article]:
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        seen = set()
        for item in soup.select(".js-post-card")[:60]:
            link = item.find("a", href=True)
            if not link:
                continue
            title = link.get_text(strip=True)
            url = link["href"]
            if url in seen:
                continue
            seen.add(url)
            if not any(kw.lower() in title.lower() for kw in self.source.keywords):
                continue
            articles.append(Article(title=title, url=url, source=""))
        return articles


class CesiumScraper(BaseScraper):
    """Cesium Blog"""
    def parse(self, html: str) -> List[Article]:
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        seen = set()
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if not re.search(r'/blog/\d{4}/\d{2}/\d{2}/', href):
                continue
            title = link.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            url = href if href.startswith("http") else urljoin("https://cesium.com", href)
            if url in seen:
                continue
            seen.add(url)
            articles.append(Article(title=title, url=url, source=""))
            if len(articles) >= 10:
                break
        return articles


class HackerNewsScraper(BaseScraper):
    """Hacker News - 通过 Algolia API"""
    def scrape(self) -> List[Article]:
        search_terms = ["digital twin", "3D Tiles", "WebRTC", "Cesium"]
        articles = []
        for term in search_terms:
            try:
                url = f"https://hn.algolia.com/api/v1/search_by_date?query={term}&tags=story&hitsPerPage=5"
                resp = self.session.get(url, timeout=30)
                data = resp.json()
                for hit in data.get("hits", []):
                    title = hit.get("title", "")
                    story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                    created_at = datetime.fromtimestamp(hit.get("created_at_i", 0))
                    if datetime.now() - created_at > timedelta(days=7):
                        continue
                    articles.append(Article(
                        title=title, url=story_url, published=created_at, source=""
                    ))
            except Exception as e:
                print(f"[ERROR] HN搜索失败 {term}: {e}")
        return articles


# ============================================================
# 全球局势数据源抓取器
# ============================================================

class WikipediaScraper(BaseScraper):
    """Wikipedia - 通过 MediaWiki API 获取当前事件相关变更"""
    def scrape(self) -> List[Article]:
        articles = []
        try:
            params = {
                "action": "query",
                "titles": "Portal:Current_events",
                "prop": "revisions",
                "rvprop": "content",
                "format": "json",
            }
            resp = self.session.get(
                "https://en.wikipedia.org/w/api.php",
                params=params,
                timeout=30,
                verify=False,
            )
            data = resp.json()

            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                revisions = page.get("revisions", [])
                if not revisions:
                    continue
                content = revisions[0].get("*", "")

                lines = content.split("\n")
                for line in lines:
                    line = line.strip()
                    event_match = re.match(r'\*+\s*\[\[(.+?)\]\]', line)
                    if event_match:
                        event_title = event_match.group(1).split("|")[0]
                        event_url = f"https://en.wikipedia.org/wiki/{event_title.replace(' ', '_')}"
                        if not any(kw.lower() in event_title.lower() for kw in self.source.keywords):
                            continue
                        articles.append(Article(
                            title=event_title,
                            url=event_url,
                            published=datetime.now(),
                            source=""
                        ))

            print(f"[INFO] Wikipedia -> {len(articles)} 条相关事件")
        except Exception as e:
            print(f"[ERROR] Wikipedia API失败: {e}")
        return articles[:15]


class RSSScraper(BaseScraper):
    """通用 RSS 抓取器 - 用于 Economist/Al Jazeera/Rest of World/Foreign Affairs"""
    def scrape(self) -> List[Article]:
        try:
            feed = feedparser.parse(self.source.url)
            articles = []
            for entry in feed.entries[:15]:
                title = entry.title
                # 关键词过滤
                if not any(kw.lower() in title.lower() for kw in self.source.keywords):
                    continue
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                articles.append(Article(
                    title=title,
                    url=entry.link,
                    published=published,
                    source=""
                ))
            return articles
        except Exception as e:
            print(f"[ERROR] RSS解析失败 {self.source.name}: {e}")
            return []


# ============================================================
# 映射表
# ============================================================

SCRAPER_MAP = {
    # 数字孪生
    "Digital Twin Consortium": DigitalTwinConsortiumScraper,
    "OGC Standards": OGCScraper,
    "Unreal Engine Blog": UnrealEngineScraper,
    "NVIDIA Developer Blog": NVIDIAScraper,
    "Cesium Blog": CesiumScraper,
    "Hacker News": HackerNewsScraper,
    # 全球局势
    "The Economist": RSSScraper,
    "Wikipedia Current Events": WikipediaScraper,
    "Al Jazeera": RSSScraper,
    "Rest of World": RSSScraper,
    "Foreign Affairs": RSSScraper,
}


def scrape_all() -> List[Article]:
    """抓取所有数据源"""
    all_articles = []
    for source in SOURCES:
        print(f"[INFO] 正在抓取: {source.name} ({source.category})")
        scraper_class = SCRAPER_MAP.get(source.name, BaseScraper)
        scraper = scraper_class(source)
        try:
            articles = scraper.scrape()
            print(f"[INFO] {source.name} -> {len(articles)} 条")
            all_articles.extend(articles)
        except Exception as e:
            print(f"[ERROR] {source.name} 抓取异常: {e}")
        time.sleep(1)
    return all_articles


if __name__ == "__main__":
    articles = scrape_all()
    print(f"\n共抓取 {len(articles)} 条文章")
    for a in articles[:15]:
        cat = "🌍" if a.category == "global_affairs" else "🏗️"
        print(f"{cat} [{a.source}] {a.title[:60]}...")
