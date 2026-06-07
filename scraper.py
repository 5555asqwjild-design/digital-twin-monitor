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

# ============================================================
# 国内数字孪生数据源抓取器
# ============================================================

class TaiboScraper(BaseScraper):
    """泰伯网 - 国内GIS/数字孪生行业媒体"""
    def parse(self, html: str) -> List[Article]:
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        seen = set()
        # 泰伯网文章链接模式: /p/{id} 或 /newsflashes/{id}
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if not re.search(r'/(p|newsflashes)/\d+', href):
                continue
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            url = href if href.startswith("http") else urljoin("https://www.taibo.cn", href)
            if url in seen:
                continue
            seen.add(url)
            # 关键词过滤
            if not any(kw in title for kw in self.source.keywords):
                continue
            articles.append(Article(title=title, url=url, source=""))
            if len(articles) >= 10:
                break
        return articles


class GovScraper(BaseScraper):
    """政府网站通用抓取器 - 工信部/住建部/自然资源部"""
    def parse(self, html: str) -> List[Article]:
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        seen = set()
        # 政府网站常见列表结构
        selectors = [
            ".news_list li", ".list li", ".TRS_Editor a", 
".news-item", ".item", "table a", ".gl-list li"
        ]
        items = []
        for sel in selectors:
            items = soup.select(sel)
            if items:
                break
        
        for item in items[:15]:
            link = item.find("a", href=True) if hasattr(item, 'find') else item
            if not link or not link.get("href"):
                continue
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            href = link["href"]
            url = href if href.startswith("http") else urljoin(self.source.url, href)
            if url in seen:
                continue
            seen.add(url)
            # 关键词过滤
            if not any(kw in title for kw in self.source.keywords):
                continue
            articles.append(Article(title=title, url=url, source=""))
        return articles


class CAICTScraper(BaseScraper):
    """中国信通院 - 研究报告"""
    def parse(self, html: str) -> List[Article]:
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        seen = set()
        # 信通院报告列表
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # 过滤PDF链接和报告详情页
            if not (".pdf" in href or "/kxyj/" in href or "/qwfb/" in href):
                continue
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            url = href if href.startswith("http") else urljoin("http://www.caict.ac.cn", href)
            if url in seen:
                continue
            seen.add(url)
            if not any(kw in title for kw in self.source.keywords):
                continue
            articles.append(Article(title=title, url=url, source=""))
            if len(articles) >= 8:
                break
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
            # 先用 requests 获取内容（支持反爬处理）
            resp = self.session.get(self.source.url, timeout=30, allow_redirects=True)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            
            if not feed.entries:
                print(f"[WARN] {self.source.name} RSS 返回 0 条 (status={resp.status_code}, url={resp.url})")
                return []
            
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
            print(f"[INFO] {self.source.name} RSS: {len(feed.entries)} 条, 匹配 {len(articles)} 条")
            return articles
        except Exception as e:
            print(f"[ERROR] RSS抓取失败 {self.source.name}: {e}")
            return []


# ============================================================
# 映射表
# ============================================================

SCRAPER_MAP = {
    # 国内数字孪生
    "泰伯网": TaiboScraper,
    "工信部": GovScraper,
    "住建部": GovScraper,
    "自然资源部": GovScraper,
    "中国信通院": CAICTScraper,
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
