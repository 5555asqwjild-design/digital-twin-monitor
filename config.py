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


# === 数字孪生数据源 ===
DIGITAL_TWIN_SOURCES = [
    Source(
        name="Digital Twin Consortium",
        url="https://www.digitaltwinconsortium.org/blog/",
        type="html",
        priority=5,
        keywords=["digital twin", "interoperability", "white paper", "lifecycle"],
        category="digital_twin",
    ),
    Source(
        name="OGC Standards",
        url="https://www.ogc.org/blog",
        type="html",
        priority=5,
        keywords=["3D Tiles", "CityGML", "geospatial", "standard"],
        category="digital_twin",
    ),
    Source(
        name="Unreal Engine Blog",
        url="https://www.unrealengine.com/en-US/blog",
        type="html",
        priority=4,
        keywords=["Pixel Streaming", "WebRTC", "large world coordinates", "rendering", "spatial computing", "nDisplay", "virtual production", "simulation", "digital twin", "Unreal Engine 5", "Unreal Engine 6", "UE5", "UE6", "AI", "machine learning", "neural", "performance", "optimization", "world partition", "Nanite", "Lumen", "MetaHuman", "RealityScan", "Twinmotion", "Datasmith", "USD", "OpenUSD"],
        category="digital_twin",
    ),
    Source(
        name="NVIDIA Developer Blog",
        url="https://developer.nvidia.com/blog",
        type="html",
        priority=4,
        keywords=["digital twin", "Omniverse", "OpenUSD", "IoT", "WebSocket", "simulation", "physics", "USD"],
        category="digital_twin",
    ),
    Source(
        name="Cesium Blog",
        url="https://cesium.com/blog/",
        type="html",
        priority=4,
        keywords=["Cesium for Unreal", "3D Tiles", "streaming", "terrain"],
        category="digital_twin",
    ),
    Source(
        name="Hacker News",
        url="https://hn.algolia.com/?q=digital+twin",
        type="api",
        priority=3,
        keywords=["digital twin", "3D Tiles", "WebRTC", "signaling server"],
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
