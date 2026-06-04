"""
数字孪生行业资讯监控器 - 主控模块
协调抓取 -> 去重 -> AI摘要 -> 推送 全流程
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Set

from config import SOURCES, HISTORY_FILE, MAX_ARTICLES_PER_BATCH
from scraper import scrape_all, Article
from ai_processor import AIProcessor
from feishu_bot import FeishuBot


class HistoryManager:
    """已推送文章历史管理"""

    def __init__(self, filepath: str = HISTORY_FILE):
        self.filepath = filepath
        self.history: Set[str] = set()
        self.data: Dict = {"articles": [], "last_check": None}
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                    self.history = {a["id"] for a in self.data.get("articles", [])}
            except Exception as e:
                print(f"[WARN] 历史记录加载失败: {e}")

    def save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def is_new(self, article_id: str) -> bool:
        return article_id not in self.history

    def add(self, article: Article):
        self.data["articles"].append(article.to_dict())
        self.history.add(article.id)
        # 只保留最近100条
        self.data["articles"] = self.data["articles"][-100:]
        self.data["last_check"] = datetime.now().isoformat()
        self.save()


def fetch_article_content(url: str) -> str:
    """获取文章正文内容（用于AI摘要）"""
    import requests
    from bs4 import BeautifulSoup
    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")
        # 尝试提取正文
        for selector in ["article", "main", ".content", ".post-content", ".entry-content"]:
            content = soup.select_one(selector)
            if content:
                return content.get_text(separator="\n", strip=True)[:5000]
        # 兜底：取所有段落
        paragraphs = soup.find_all("p")
        return "\n".join(p.get_text(strip=True) for p in paragraphs[:20])
    except Exception as e:
        print(f"[WARN] 获取文章内容失败 {url}: {e}")
        return ""


def run_monitor(dry_run: bool = False):
    """运行监控流程"""
    print(f"\n{'='*60}")
    print(f"🚀 数字孪生资讯监控启动 @ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # 1. 加载历史
    history = HistoryManager()
    print(f"[INFO] 历史记录: {len(history.history)} 条已推送")

    # 2. 抓取所有源
    articles = scrape_all()
    if not articles:
        print("[WARN] 未抓取到任何文章")
        return

    # 3. 过滤新文章 + 时间过滤（只取最近3天）
    cutoff = datetime.now() - timedelta(days=3)
    new_articles = []
    for art in articles:
        if history.is_new(art.id):
            if art.published and art.published < cutoff:
                continue
            new_articles.append(art)

    if not new_articles:
        print("[INFO] 没有新文章需要推送")
        return

    print(f"[INFO] 发现 {len(new_articles)} 条新文章")

    # 4. AI 生成摘要
    ai = AIProcessor()
    to_push = []
    for art in new_articles[:MAX_ARTICLES_PER_BATCH]:
        print(f"[INFO] 正在处理: {art.title[:60]}...")
        content = fetch_article_content(art.url)
        summary = ai.summarize(art.title, content)
        art.summary = summary
        to_push.append(art)

    # 5. 推送到飞书
    if not dry_run:
        bot = FeishuBot()
        push_data = [{
            "title": a.title,
            "summary": a.summary,
            "url": a.url,
            "source": a.source,
        } for a in to_push]

        if len(push_data) == 1:
            # 单条实时推送
            bot.send_single_article(
                push_data[0]["title"],
                push_data[0]["summary"],
                push_data[0]["url"],
                push_data[0]["source"],
            )
        else:
            # 批量汇总推送
            bot.send_rich_text(
                f"数字孪生精选 ({datetime.now().strftime('%m-%d')})",
                push_data,
            )

        # 6. 记录历史
        for art in to_push:
            history.add(art)

    print(f"\n{'='*60}")
    print(f"✅ 完成: 推送 {len(to_push)} 条文章")
    print(f"{'='*60}\n")


def run_deep_dive(url: str, focus: str = ""):
    """对单篇文章进行深度爆破"""
    print(f"\n💥 开始深度爆破: {url}\n")

    content = fetch_article_content(url)
    if not content:
        print("[ERROR] 无法获取文章内容")
        return

    ai = AIProcessor()
    result = ai.deep_dive("用户指定文章", content, focus)

    print("\n" + "="*60)
    print(result)
    print("="*60 + "\n")

    # 推送到飞书
    bot = FeishuBot()
    bot.send_deep_dive("用户指定文章", result, url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="数字孪生行业资讯监控器")
    parser.add_argument("--dry-run", action="store_true", help="仅运行，不推送")
    parser.add_argument("--deep-dive", type=str, help="对指定URL进行深度爆破")
    parser.add_argument("--focus", type=str, default="", help="深度爆破时重点关注领域")
    args = parser.parse_args()

    if args.deep_dive:
        run_deep_dive(args.deep_dive, args.focus)
    else:
        run_monitor(dry_run=args.dry_run)
