"""
数字孪生行业资讯监控器 - AI 处理模块
负责内容摘要生成和深度爆破解读
"""
import os
import re
from typing import List, Optional
from openai import OpenAI

from config import AI_API_KEY, AI_API_BASE, AI_MODEL, SUMMARY_MAX_LENGTH


class AIProcessor:
    """AI 内容处理器"""

    def __init__(self):
        self.client = OpenAI(
            api_key=AI_API_KEY,
            base_url=AI_API_BASE,
        )

    def _call(self, prompt: str, max_tokens: int = 500) -> str:
        """调用大模型"""
        try:
            resp = self.client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": "你是一位数字孪生行业技术专家，擅长从英文技术文章中提取核心干货。输出简洁、结构化、无废话。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[ERROR] AI调用失败: {e}")
            return ""

    def summarize(self, title: str, content: str) -> str:
        """
        生成一句话精简摘要
        输入: 文章标题 + 正文（或前几段）
        输出: 一句话中文摘要
        """
        # 如果内容太长，截断
        content = content[:3000] if content else ""
        prompt = f"""请对以下数字孪生行业技术文章生成一句精简的中文摘要（不超过{SUMMARY_MAX_LENGTH}字）。
要求：
- 只说核心技术点/更新内容，不要背景介绍
- 如果涉及具体技术（如Pixel Streaming、3D Tiles、OpenUSD等），点明名称
- 格式：【技术点】+ 【价值/影响】

标题：{title}
内容：{content}

摘要："""
        result = self._call(prompt, max_tokens=200)
        # 清理
        result = result.replace("摘要：", "").strip()
        return result if result else f"{title[:50]}..."

    def deep_dive(self, title: str, content: str, focus_area: str = "") -> str:
        """
        深度爆破解读 - 提取结构化干货
        输入: 完整文章内容
        输出: Markdown 格式的结构化要点
        """
        content = content[:8000]  # 限制长度
        focus_hint = f"重点关注：{focus_area}" if focus_area else ""
        prompt = f"""你是一位数字孪生领域的技术专家。请对以下技术文章进行"爆破式"解读，提取所有硬核干货，删除一切废话。

{focus_hint}

要求输出格式（严格按此格式）：
## 📌 核心结论
（一句话总结这篇文章最重要的1-3个结论）

## 🔧 技术干货
- 要点1：...
- 要点2：...
- 要点3：...
（列出所有具体的技术方案、参数、架构设计、性能数据）

## 💡 对你的价值
（结合GIS+Unreal背景，说明这篇文章对你实际工作的直接帮助）

## 🔗 关键术语/链接
（文章中提到的技术标准、工具、协议名称）

原文标题：{title}
原文内容：
{content}
"""
        return self._call(prompt, max_tokens=2000)

    def batch_summarize(self, articles: List[dict]) -> List[dict]:
        """
        批量生成摘要
        articles: [{"title": ..., "content": ..., "url": ...}]
        返回: 添加 summary 字段的文章列表
        """
        results = []
        for art in articles:
            summary = self.summarize(art["title"], art.get("content", ""))
            art["summary"] = summary
            results.append(art)
        return results


if __name__ == "__main__":
    # 测试
    processor = AIProcessor()
    test_title = "Unreal Engine 5.4 Pixel Streaming Updates"
    test_content = "The latest update to Pixel Streaming in UE 5.4 introduces significant improvements to WebRTC protocol handling, reducing latency by 30% for multi-user scenarios. New APIs allow direct integration with IoT data streams..."
    print("=== 摘要测试 ===")
    print(processor.summarize(test_title, test_content))
    print("\n=== 深度爆破测试 ===")
    print(processor.deep_dive(test_title, test_content, "渲染架构"))
