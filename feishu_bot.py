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

    def send_rich_text(self, title: str, articles: List[Dict]) -> bool:
        """
        发送富文本卡片 - 资讯列表
        articles: [{"title": ..., "summary": ..., "url": ..., "source": ...}]
        """
        elements = []
        for art in articles:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**[{art['source']}]** [{art['title']}]({art['url']})\n📝 {art.get('summary', '')}",
                }
            })
            elements.append({"tag": "hr"})

        # 移除最后一个分割线
        if elements:
            elements.pop()

        card = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"📡 {title}",
                    },
                    "template": "blue",
                },
                "elements": elements,
            },
        }
        return self._send(card)

    def send_single_article(self, title: str, summary: str, url: str, source: str) -> bool:
        """发送单条文章推送（实时触发用）"""
        return self.send_rich_text("数字孪生新资讯", [{
            "title": title,
            "summary": summary,
            "url": url,
            "source": source,
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
    # 测试推送
    bot.send_rich_text("数字孪生每日精选", [
        {
            "title": "Unreal Engine 5.4 Pixel Streaming重大更新",
            "summary": "WebRTC延迟降低30%，新增IoT数据流直接接入API",
            "url": "https://example.com",
            "source": "Unreal Engine Blog",
        },
        {
            "title": "OGC发布3D Tiles 1.1正式标准",
            "summary": "支持语义元数据和隐式瓦片，大幅提升城市场景加载效率",
            "url": "https://example.com",
            "source": "OGC",
        },
    ])
