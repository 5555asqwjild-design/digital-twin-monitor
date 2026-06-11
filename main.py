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
    print(f"🚀 资讯监控启动 @ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    # 1. 加载历史
    history = HistoryManager()
    print(f"[INFO] 历史记录: {len(history.history)} 条已推送")

    # 2. 抓取所有源
    articles = scrape_all()
    if not articles:
        print("[WARN] 未抓取到任何文章")
        return

    # 3. 过滤新文章 + 时间过滤（只取最近3天）+ 标题去重
    cutoff = datetime.now() - timedelta(days=3)
    new_articles = []
    seen_titles = set()
    for art in articles:
        # 标题去重（即使URL不同，标题相同也跳过）
        title_key = art.title.strip()[:50]
        if title_key in seen_titles:
            print(f"[INFO] 标题重复跳过: {art.title[:50]}")
            continue
        seen_titles.add(title_key)
        
        if not history.is_new(art.id):
            print(f"[INFO] 已推送跳过: {art.title[:50]}")
            continue
        if art.published and art.published < cutoff:
            continue
        new_articles.append(art)

    if not new_articles:
        print("[INFO] 没有新文章需要推送")
        return

    print(f"[INFO] 发现 {len(new_articles)} 条新文章")

    # 4. AI 生成摘要 + 智能分类
    ai = AIProcessor()
    to_push = {"digital_twin": [], "global_affairs": []}
    for art in new_articles[:MAX_ARTICLES_PER_BATCH]:
        print(f"[INFO] 正在处理: {art.title[:60]}...")
        content = fetch_article_content(art.url)
        category = getattr(art, 'category', 'digital_twin')
        
        # AI 摘要
        summary = ai.summarize(art.title, content, category=category)
        art.summary = summary
        
        # AI 智能分类（仅数字孪生类）
        if category == "digital_twin":
            classify_result = ai.classify(art.title, content)
            art.content_type = classify_result.get("content_type", "产业动态")
            art.scene_tags = classify_result.get("scene_tags", [])
            print(f"[INFO] 分类结果: {art.content_type} | 标签: {', '.join(art.scene_tags) if art.scene_tags else '无'}")
        
        to_push.setdefault(category, []).append(art)

    # 5. 推送到飞书（按分类分别推送不同颜色的卡片）
    if not dry_run:
        bot = FeishuBot()
        date_str = datetime.now().strftime('%m-%d')

        for category, arts in to_push.items():
            if not arts:
                continue
            
            if category == "digital_twin":
                # 数字孪生：按 content_type 分组推送
                type_groups = {}
                for a in arts:
                    ctype = getattr(a, 'content_type', '产业动态')
                    type_groups.setdefault(ctype, []).append(a)
                
                for ctype, type_arts in type_groups.items():
                    push_data = [{
                        "title": a.title,
                        "summary": a.summary,
                        "url": a.url,
                        "source": a.source,
                        "scene_tags": getattr(a, 'scene_tags', []),
                    } for a in type_arts]
                    
                    type_icons = {
                        "政策速递": "📋",
                        "行业案例": "🏗️",
                        "技术研报": "🔬",
                        "产业动态": "📰",
                    }
                    icon = type_icons.get(ctype, "📰")
                    title = f"{icon} {ctype} ({date_str})"
                    
                    if len(push_data) == 1:
                        bot.send_single_article(
                            push_data[0]["title"],
                            push_data[0]["summary"],
                            push_data[0]["url"],
                            push_data[0]["source"],
                            scene_tags=push_data[0].get("scene_tags", []),
                        )
                    else:
                        bot.send_rich_text(title, push_data, category=category, content_type=ctype)
            else:
                # 全球局势：保持原有逻辑
                push_data = [{
                    "title": a.title,
                    "summary": a.summary,
                    "url": a.url,
                    "source": a.source,
                } for a in arts]
                title = f"🌍 全球格局速报 ({date_str})"
                
                if len(push_data) == 1:
                    bot.send_single_article(
                        push_data[0]["title"],
                        push_data[0]["summary"],
                        push_data[0]["url"],
                        push_data[0]["source"],
                    )
                else:
                    bot.send_rich_text(title, push_data, category=category)

        # 6. 记录历史
        for arts in to_push.values():
            for art in arts:
                history.add(art)

    total = sum(len(v) for v in to_push.values())
    print(f"\n{'='*60}")
    print(f"✅ 完成: 推送 {total} 条文章")
    for cat, arts in to_push.items():
        if cat == "digital_twin":
            # 按子分类统计
            type_counts = {}
            for a in arts:
                ctype = getattr(a, 'content_type', '产业动态')
                type_counts[ctype] = type_counts.get(ctype, 0) + 1
            print(f"  🏗️ 数字孪生: {len(arts)} 条")
            for ctype, count in type_counts.items():
                print(f"      • {ctype}: {count} 条")
        else:
            print(f"  🌍 {cat}: {len(arts)} 条")
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
