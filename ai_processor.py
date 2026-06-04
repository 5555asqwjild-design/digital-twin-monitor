"""
资讯监控器 - AI 处理模块
支持数字孪生 + 全球局势 两个方向的摘要生成
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

    def _call(self, prompt: str, system_prompt: str = "", max_tokens: int = 500) -> str:
        """调用大模型"""
        if not system_prompt:
            system_prompt = "你是一位资讯分析专家，擅长从英文文章中提取核心信息。输出简洁、结构化、无废话。"
        try:
            resp = self.client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[ERROR] AI调用失败: {e}")
            return ""

    def summarize(self, title: str, content: str, category: str = "digital_twin") -> str:
        """
        生成一句话精简摘要
        根据 category 自动切换 prompt 方向
        """
        content = content[:3000] if content else ""

        if category == "global_affairs":
            system = "你是一位地缘政治分析专家，擅长透过新闻表象看清背后的格局与博弈。你的视角是'为什么'而非'发生了什么'。"
            prompt = f"""请对以下全球局势文章生成一句精简的中文格局解读（不超过{SUMMARY_MAX_LENGTH}字）。
要求：
- 不要复述新闻事实，而是点明背后的格局与博弈
- 说明涉及的大国/阵营利益、深层动机、可能走向
- 格式：【格局定位】+ 【背后博弈】+ 【可能走向】

标题：{title}
内容：{content}

格局解读："""
        else:
            system = "你是一位数字孪生行业技术专家，擅长从英文技术文章中提取核心干货。输出简洁、结构化、无废话。"
            prompt = f"""请对以下数字孪生行业技术文章生成一句精简的中文摘要（不超过{SUMMARY_MAX_LENGTH}字）。
要求：
- 只说核心技术点/更新内容，不要背景介绍
- 如果涉及具体技术（如Pixel Streaming、3D Tiles、OpenUSD等），点明名称
- 格式：【技术点】+ 【价值/影响】

标题：{title}
内容：{content}

摘要："""

        result = self._call(prompt, system_prompt=system, max_tokens=200)
        result = result.replace("摘要：", "").strip()
        return result if result else f"{title[:50]}..."

    def deep_dive(self, title: str, content: str, focus_area: str = "", category: str = "digital_twin") -> str:
        """
        深度爆破解读 - 提取结构化干货
        """
        content = content[:8000]
        focus_hint = f"重点关注：{focus_area}" if focus_area else ""

        if category == "global_affairs":
            system = "你是一位地缘政治分析专家，擅长透过新闻表象看清背后的格局与博弈。"
            prompt = f"""你是一位地缘政治分析专家。请对以下文章进行深度格局解读，透过表象看清背后的博弈与趋势。

{focus_hint}

要求输出格式（严格按此格式）：
## 📌 格局定位
（这件事在全球棋盘上的位置：属于大国博弈/区域冲突/经济战/技术竞争/价值观冲突中的哪一层）

## 🎯 利益博弈
- 利益方A：...（诉求、动机、手段）
- 利益方B：...（诉求、动机、手段）
- 潜在第三方：...
（列出所有关键利益方及其深层动机）

## 📈 趋势预判
（基于历史规律和当前态势，预判可能的走向、关键节点、转折信号）

## 🧠 历史参照
（类似的历史事件及其走向，可供参考的经验教训）

原文标题：{title}
原文内容：
{content}
"""
        else:
            system = "你是一位数字孪生领域的技术专家。"
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
        return self._call(prompt, system_prompt=system, max_tokens=2000)


if __name__ == "__main__":
    # 测试
    processor = AIProcessor()
    test_title = "Unreal Engine 5.4 Pixel Streaming Updates"
    test_content = "The latest update to Pixel Streaming in UE 5.4 introduces significant improvements to WebRTC protocol handling, reducing latency by 30% for multi-user scenarios. New APIs allow direct integration with IoT data streams..."
    print("=== 摘要测试 ===")
    print(processor.summarize(test_title, test_content))
    print("\n=== 深度爆破测试 ===")
    print(processor.deep_dive(test_title, test_content, "渲染架构"))
