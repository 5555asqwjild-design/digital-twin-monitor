"""
数字孪生行业资讯监控器 - 数据抓取模块
支持 RSS、API、HTML 三种抓取方式
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
                 summary: str = "", content: str = "", author: str = ""):
        self.title = title
        self.url = url
        self.source = source
        self.published = published or datetime.now()
        self.summary = summary
        self.content = content
        self.author = author
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
        }

    def __repr__(self):
        return f"<Article {self.source}: {self.title[:50]}...>"


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
        # 标记来源
        for a in articles:
            a.source = self.source.name
        return articles


class DigitalTwinConsortiumScraper(BaseScraper):
    """Digital Twin Consortium Blog"""
    def parse(self, html: str) -> List[Article]:
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        # DTC blog 文章在 .entry 中
        for item in soup.select(".entry")[:10]:
            link = item.find("a", href=True)
            if not link:
                continue
            title = link.get_text(strip=True)
            url = link["href"]
            if not url.startswith("http"):
                url = urljoin(self.source.url, url)
            # 提取日期从URL /2026/04/...
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
        # OGC blog 文章在 .e-loop-item 中
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
    """Unreal Engine Blog - 使用 RSS Feed"""
    def scrape(self) -> List[Article]:
        feed_url = "https://www.unrealengine.com/rss"
        try:
            feed = feedparser.parse(feed_url)
            articles = []
            for entry in feed.entries[:10]:
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                # 清理标题中的HTML标签
                title = re.sub(r'<[^>]+>', '', entry.title)
                articles.append(Article(
                    title=title,
                    url=entry.link,
                    published=published,
                    source=""
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
        # NVIDIA blog 文章卡片 - .js-post-card，检查更多卡片
        for item in soup.select(".js-post-card")[:60]:
            link = item.find("a", href=True)
            if not link:
                continue
            title = link.get_text(strip=True)
            url = link["href"]
            if url in seen:
                continue
            seen.add(url)
            # 过滤只保留数字孪生相关
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
        # Cesium blog 文章链接包含 /blog/20xx/ 模式
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
                    # 只取最近7天的
                    if datetime.now() - created_at > timedelta(days=7):
                        continue
                    articles.append(Article(
                        title=title,
                        url=story_url,
                        published=created_at,
                        source=""
                    ))
            except Exception as e:
                print(f"[ERROR] HN搜索失败 {term}: {e}")
        return articles


# 映射表：数据源 -> 抓取器
SCRAPER_MAP = {
    "Digital Twin Consortium": DigitalTwinConsortiumScraper,
    "OGC Standards": OGCScraper,
    "Unreal Engine Blog": UnrealEngineScraper,
    "NVIDIA Developer Blog": NVIDIAScraper,
    "Cesium Blog": CesiumScraper,
    "Hacker News": HackerNewsScraper,
}


def scrape_all() -> List[Article]:
    """抓取所有数据源"""
    all_articles = []
    for source in SOURCES:
        print(f"[INFO] 正在抓取: {source.name}")
        scraper_class = SCRAPER_MAP.get(source.name, BaseScraper)
        scraper = scraper_class(source)
        try:
            articles = scraper.scrape()
            print(f"[INFO] {source.name} -> {len(articles)} 条")
            all_articles.extend(articles)
        except Exception as e:
            print(f"[ERROR] {source.name} 抓取异常: {e}")
        time.sleep(1)  # 礼貌间隔
    return all_articles


if __name__ == "__main__":
    articles = scrape_all()
    print(f"\n共抓取 {len(articles)} 条文章")
    for a in articles[:10]:
        print(f"- [{a.source}] {a.title[:60]}... ({a.url})")
