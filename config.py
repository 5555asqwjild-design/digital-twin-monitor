"""
数字孪生行业资讯监控器 - 配置文件
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


# === 数据源配置 ===
SOURCES = [
    Source(
        name="Digital Twin Consortium",
        url="https://www.digitaltwinconsortium.org/blog/",
        type="html",
        priority=5,
        keywords=["digital twin", "interoperability", "white paper", "lifecycle"]
    ),
    Source(
        name="OGC Standards",
        url="https://www.ogc.org/blog",
        type="html",
        priority=5,
        keywords=["3D Tiles", "CityGML", "geospatial", "standard"]
    ),
    Source(
        name="Unreal Engine Blog",
        url="https://www.unrealengine.com/en-US/blog",
        type="html",
        priority=4,
        keywords=["Pixel Streaming", "WebRTC", "large world coordinates", "rendering"]
    ),
    Source(
        name="NVIDIA Developer Blog",
        url="https://developer.nvidia.com/blog",
        type="html",
        priority=4,
        keywords=["digital twin", "Omniverse", "OpenUSD", "IoT", "WebSocket", "simulation", "physics", "USD"]
    ),
    Source(
        name="Cesium Blog",
        url="https://cesium.com/blog/",
        type="html",
        priority=4,
        keywords=["Cesium for Unreal", "3D Tiles", "streaming", "terrain"]
    ),
    Source(
        name="Hacker News",
        url="https://hn.algolia.com/?q=digital+twin",
        type="api",
        priority=3,
        keywords=["digital twin", "3D Tiles", "WebRTC", "signaling server"]
    ),
]

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
