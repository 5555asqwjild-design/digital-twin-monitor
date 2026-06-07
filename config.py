"""
资讯监控器 - 配置文件（数字孪生 + 全球局势）
"""
import os
from dataclasses import dataclass
from typing import List


@dataclass
class Source:
    name: str
    url: str
    type: str  # "rss", "api", "html"
    priority: int  # 1-5, 越高越重要
    keywords: List[str]  # 用于过滤相关内容
    category: str = "digital_twin"  # "digital_twin" 或 "global_affairs"


# === 数字孪生数据源（国内导向）===
DIGITAL_TWIN_SOURCES = [
    Source(
        name="泰伯网",
        url="https://www.taibo.cn/",
        type="html",
        priority=5,
        keywords=["数字孪生", "实景三维", "CIM", "城市信息模型", "GIS", "三维GIS", "空间智能", "智慧城市", "智慧园区", "智慧水利", "智慧交通", "智慧电力", "低空经济", "遥感", "测绘", "超图", "51World", "飞渡", "优锘", "信创", "国产化"],
        category="digital_twin",
    ),
    Source(
        name="工信部",
        url="https://www.miit.gov.cn/jgsj/xxjsfzs/wjfb/index.html",
        type="html",
        priority=5,
        keywords=["数字孪生", "工业互联网", "智能制造", "数字化转型", "实景三维", "CIM", "智慧城市", "信创", "国产化", "工业软件"],
        category="digital_twin",
    ),
    Source(
        name="住建部",
        url="https://www.mohurd.gov.cn/gongkai/zc/wjk/index.html",
        type="html",
        priority=5,
        keywords=["数字孪生", "CIM", "城市信息模型", "智慧城市", "数字住建", "实景三维", "市政基础设施", "城市运行管理"],
        category="digital_twin",
    ),
    Source(
        name="自然资源部",
        url="https://gi.mnr.gov.cn/",
        type="html",
        priority=4,
        keywords=["实景三维", "数字孪生", "三维GIS", "测绘", "遥感", "国土空间", "地理信息", "基础测绘", "时空大数据"],
        category="digital_twin",
    ),
    Source(
        name="中国信通院",
        url="http://www.caict.ac.cn/kxyj/qwfb/ztbg/",
        type="html",
        priority=4,
        keywords=["数字孪生", "数字孪生城市", "智慧城市", "CIM", "实景三维", "数字化转型", "工业互联网", "产业图谱"],
        category="digital_twin",
    ),
]

# === 全球局势数据源 ===
GLOBAL_AFFAIRS_SOURCES = [
    Source(
        name="The Economist",
        url="https://www.economist.com/rss/print-edition.xml",
        type="rss",
        priority=5,
        keywords=["geopolitics", "trade", "war", "election", "economy", "China", "US", "Russia", "Europe", "Asia", "Middle East", "Africa", "Latin America", "technology", "AI", "climate", "energy", "migration", "democracy", "authoritarianism", "sanctions", "tariff", "supply chain", "semiconductor", "nuclear", "diplomacy", "summit", "treaty", "alliance", "NATO", "G7", "BRICS", "UN", "central bank", "inflation", "recession", "GDP", "pandemic", "cybersecurity", "space", "Arctic", "Ukraine", "Taiwan", "Israel", "Gaza", "Korea", "Myanmar", "Sudan"],
        category="global_affairs",
    ),
    Source(
        name="Wikipedia Current Events",
        url="https://en.wikipedia.org/w/api.php",
        type="api",
        priority=4,
        keywords=["war", "conflict", "election", "summit", "treaty", "sanctions", "trade", "pandemic", "climate", "disaster", "terrorism", "nuclear", "diplomacy", "geopolitics", "coup", "revolution", "protest", "ceasefire", "alliance"],
        category="global_affairs",
    ),
    Source(
        name="Al Jazeera",
        url="https://www.aljazeera.com/xml/rss/all.xml",
        type="rss",
        priority=4,
        keywords=["war", "conflict", "Palestine", "Israel", "Gaza", "Ukraine", "Russia", "Syria", "Yemen", "Iran", "Iraq", "Afghanistan", "Sudan", "Libya", "Ethiopia", "Myanmar", "China", "US", "Turkey", "Saudi", "Egypt", "Africa", "Middle East", "Asia", "Latin America", "migration", "refugee", "human rights", "UN", "ceasefire", "peace", "diplomacy", "sanctions", "nuclear", "climate", "coup", "revolution", "protest", "election", "genocide", "massacre", "offensive", "attack"],
        category="global_affairs",
    ),
    Source(
        name="Rest of World",
        url="https://restofworld.org/feed/",
        type="rss",
        priority=3,
        keywords=["technology", "internet", "censorship", "surveillance", "AI", "platform", "social media", "digital rights", "startup", "ecommerce", "fintech", "China", "India", "Africa", "Southeast Asia", "Latin America", "Middle East", "Russia", "Brazil", "Indonesia", "Nigeria", "global south", "digital divide", "misinformation", "deepfake", "regulation", "ban", "protest", "migration", "culture", "society"],
        category="global_affairs",
    ),
    Source(
        name="Foreign Affairs",
        url="https://www.foreignaffairs.com/rss",
        type="rss",
        priority=5,
        keywords=["geopolitics", "strategy", "diplomacy", "war", "nuclear", "China", "US", "Russia", "Europe", "Asia", "Middle East", "India", "Africa", "Latin America", "trade", "sanctions", "alliance", "NATO", "democracy", "authoritarianism", "climate", "energy", "technology", "AI", "cyber", "space", "migration", "terrorism", "proliferation", "deterrence", "hegemony", "multipolar", "bipolar", "unipolar", "Cold War", "world order", "global governance", "international law", "sovereignty", "intervention", "regime change", "soft power", "hard power", "grand strategy", "foreign policy"],
        category="global_affairs",
    ),
]

# 合并所有数据源
SOURCES = DIGITAL_TWIN_SOURCES + GLOBAL_AFFAIRS_SOURCES

# === 推送配置 ===
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK", "")
FEISHU_SECRET = os.getenv("FEISHU_SECRET", "")  # 可选：加签密钥

# === AI配置 ===
# 使用 OpenAI 兼容接口，可替换为任意大模型 API
# DeepSeek: https://api.deepseek.com/v1, model: deepseek-chat
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_API_BASE = os.getenv("AI_API_BASE", "https://api.deepseek.com/v1")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")

# === 运行配置 ===
CHECK_INTERVAL_HOURS = 6  # 检查间隔
MAX_ARTICLES_PER_BATCH = 10  # 每次最多推送条数
SUMMARY_MAX_LENGTH = 150  # 摘要最大字数
HISTORY_FILE = "history.json"  # 已推送记录
