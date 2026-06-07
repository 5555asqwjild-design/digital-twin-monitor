"""
数字孪生行业资讯监控器 - 飞书机器人推送模块
支持 webhook 推送和加签验证
"""
import json
import time
import base64
import hmac
import hashlib
import requests
from typing import List, Dict

from config import FEISHU_WEBHOOK, FEISHU_SECRET


class FeishuBot:
    """飞书群机器人"""

    def __init__(self, webhook: str = None, secret: str = None):
        self.webhook = webhook or FEISHU_WEBHOOK
        self.secret = secret or FEISHU_SECRET

    def _gen_sign(self, timestamp: int) -> str:
        """生成加签（如果配置了secret）"""
        if not self.secret:
            return ""
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    def _send(self, payload: Dict) -> bool:
        """发送消息到飞书"""
        if not self.webhook:
            print("[WARN] 未配置飞书 webhook，跳过推送")
            return False

        timestamp = int(time.time())
        sign = self._gen_sign(timestamp)

        if sign:
            payload["timestamp"] = timestamp
            payload["sign"] = sign

        try:
            resp = requests.post(
                self.webhook,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            result = resp.json()
            if result.get("code") == 0:
                print("[INFO] 飞书推送成功")
                return True
            else:
                print(f"[ERROR] 飞书推送失败: {result}")
                return False
        except Exception as e:
            print(f"[ERROR] 飞书请求异常: {e}")
            return False

    def send_text(self, text: str) -> bool:
        """发送纯文本消息"""
        return self._send({
            "msg_type": "text",
            "content": {"text": text},
        })

    def send_rich_text(self, title: str, articles: List[Dict], category: str = "digital_twin", content_type: str = "") -> bool:
        """
        发送富文本卡片 - 资讯列表
        articles: [{"title": ..., "summary": ..., "url": ..., "source": ..., "scene_tags": [...]}]
        category: "digital_twin" 或 "global_affairs"，决定卡片颜色
        content_type: 数字孪生子分类（政策速递/行业案例/技术研报/产业动态）
        """
        # 卡片颜色和图标
        type_templates = {
            "政策速递": "red",
            "行业案例": "blue",
            "技术研报": "purple",
            "产业动态": "wathet",
        }
        
        if category == "global_affairs":
            template = "green"
        elif content_type and content_type in type_templates:
            template = type_templates[content_type]
        else:
            template = "blue"

        elements = []
        for art in articles:
            # 场景标签
            tags = art.get("scene_tags", [])
            tag_str = ""
            if tags:
                tag_str = " ".join([f"`{t}`" for t in tags]) + "\n"
            
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**[{art['source']}]** [{art['title']}]({art['url']})\n{tag_str}📝 {art.get('summary', '')}",
                }
            })
            elements.append({"tag": "hr"})

        if elements:
            elements.pop()

        card = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title,
                    },
                    "template": template,
                },
                "elements": elements,
            },
        }
        return self._send(card)

    def send_single_article(self, title: str, summary: str, url: str, source: str, scene_tags: List[str] = None) -> bool:
        """发送单条文章推送（实时触发用）"""
        return self.send_rich_text("数字孪生新资讯", [{
            "title": title,
            "summary": summary,
            "url": url,
            "source": source,
            "scene_tags": scene_tags or [],
        }])

    def send_deep_dive(self, original_title: str, deep_content: str, url: str) -> bool:
        """发送深度爆破解读结果"""
        card = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"💥 深度爆破: {original_title[:50]}...",
                    },
                    "template": "red",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": deep_content[:3000],  # 飞书卡片有长度限制
                        }
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "阅读原文"},
                                "url": url,
                                "type": "primary",
                            }
                        ]
                    }
                ],
            },
        }
        return self._send(card)


if __name__ == "__main__":
    bot = FeishuBot()
    # 测试推送 - 国内分类示例
    bot.send_rich_text("📋 政策速递 (06-07)", [
        {
            "title": "工信部发布《数字孪生工厂建设指南》",
            "summary": "到2027年打造100个数字孪生工厂标杆，优先采用国产GIS平台和渲染引擎",
            "url": "https://example.com",
            "source": "工信部",
            "scene_tags": ["工业互联网", "信创国产化"],
        },
    ], category="digital_twin", content_type="政策速递")
    
    bot.send_rich_text("🏗️ 行业案例 (06-07)", [
        {
            "title": "深圳市CIM平台二期建成，覆盖全市2000+建筑",
            "summary": "基于超图GIS引擎，实现城市级数字孪生底座，支撑智慧城管、应急指挥等场景",
            "url": "https://example.com",
            "source": "泰伯网",
            "scene_tags": ["智慧城市", "实景三维"],
        },
    ], category="digital_twin", content_type="行业案例")
