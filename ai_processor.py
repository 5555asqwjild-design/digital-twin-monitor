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
            system = "你是一位中国数字孪生产业分析师，熟悉国内政策、技术路线和行业落地。输出简洁、有洞察力。"
            prompt = f"""请对以下国内数字孪生相关内容生成一句精简的中文摘要（不超过{SUMMARY_MAX_LENGTH}字）。
要求：
- 点明政策/技术/案例的核心要点
- 说明对国内产业的影响或落地价值
- 如涉及具体企业（超图、51World、飞渡等）或政策文件，点明名称
- 格式：【要点】+ 【影响/价值】

标题：{title}
内容：{content}

摘要："""

        result = self._call(prompt, system_prompt=system, max_tokens=200)
        result = result.replace("摘要：", "").replace("格局解读：", "").strip()
        return result if result else f"{title[:50]}..."

    def classify(self, title: str, content: str) -> dict:
        """
        对数字孪生文章进行智能分类
        返回 {"content_type": "政策速递|行业案例|技术研报|产业动态", "scene_tags": ["智慧城市", "智慧水利", ...]}
        """
        content = content[:2000] if content else ""
        system = "你是一位中国数字孪生产业分类专家，熟悉国内政策、技术和应用场景。只输出JSON格式，不要任何解释。"
        prompt = f"""请对以下数字孪生相关文章进行分类，只输出JSON，不要任何其他文字。

分类规则：
1. content_type（内容类型，单选）：
   - "政策速递" — 政府发布的政策、规划、指导意见、通知、标准
   - "行业案例" — 具体项目的实施、落地、应用案例、试点经验
   - "技术研报" — 技术白皮书、研究报告、技术路线分析、测评
   - "产业动态" — 企业新闻、市场动态、投融资、行业活动

2. scene_tags（应用场景标签，可多选，最多3个）：
   ["智慧城市", "智慧水利", "智慧电力", "智慧交通", "智慧园区", "实景三维", "工业互联网", "信创国产化"]
   如果都不匹配则留空数组 []

标题：{title}
内容：{content}

请严格按以下JSON格式输出（不要markdown代码块）：
{{"content_type":"...","scene_tags":["..."]}}
"""
        result = self._call(prompt, system_prompt=system, max_tokens=150)
        try:
            import json
            # 清理可能的 markdown 代码块
            result = result.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[1]
            if result.endswith("```"):
                result = result.rsplit("\n", 1)[0]
            result = result.strip()
            data = json.loads(result)
            return {
                "content_type": data.get("content_type", "产业动态"),
                "scene_tags": data.get("scene_tags", [])
            }
        except Exception:
            # 回退：根据关键词简单分类
            text = (title + " " + content).lower()
            if any(k in text for k in ["政策", "通知", "意见", "规划", "标准", "指南", "印发", "发布"]):
                ctype = "政策速递"
            elif any(k in text for k in ["案例", "落地", "实施", "项目", "试点", "应用", "建设", "交付"]):
                ctype = "行业案例"
            elif any(k in text for k in ["白皮书", "报告", "研究", "测评", "分析", "技术路线"]):
                ctype = "技术研报"
            else:
                ctype = "产业动态"
            
            tags = []
            tag_keywords = {
                "智慧城市": ["城市", "cim", "市政"],
                "智慧水利": ["水利", "水务", "防洪", "流域"],
                "智慧电力": ["电力", "电网", "能源", "电厂"],
                "智慧交通": ["交通", "公路", "铁路", "地铁", "机场"],
                "智慧园区": ["园区", "开发区", "厂区"],
                "实景三维": ["实景三维", "测绘", "遥感", "地理信息"],
                "工业互联网": ["工业", "制造", "工厂", "车间"],
                "信创国产化": ["信创", "国产化", "国产", "自主可控"]
            }
            for tag, kws in tag_keywords.items():
                if any(k in text for k in kws):
                    tags.append(tag)
            return {"content_type": ctype, "scene_tags": tags[:3]}

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
            system = "你是一位中国数字孪生产业分析师，熟悉国内政策环境、国产化技术路线和行业落地案例。"
            prompt = f"""你是一位中国数字孪生产业分析师。请对以下内容进行深度解读，聚焦国内政策、国产化技术路线和行业落地价值。

{focus_hint}

要求输出格式（严格按此格式）：
## 📌 核心要点
（一句话总结政策/案例/技术的核心内容，如涉及具体文件请写明文件名）

## 🏛️ 政策/产业背景
- 相关政策：...
- 主管部门：...
- 产业阶段：...
（如涉及政策，说明发文单位、政策层级、与前期政策的衔接关系）

## 🔧 技术/国产化要点
- 技术方案：...
- 国产化元素：...
- 信创要求：...
（如涉及技术，说明国产GIS引擎/渲染引擎/数据库等，以及与国外技术的替代关系）

## 💼 落地价值
- 应用场景：...
- 受益方：...
- 商业模式：...
（说明智慧城市/智慧园区/水利/电力/交通等具体落地场景和可复制性）

## 📈 产业影响
（对国内数字孪生产业链的影响，对相关企业的机会或挑战）

原文标题：{title}
原文内容：
{content}
"""
        return self._call(prompt, system_prompt=system, max_tokens=2000)


if __name__ == "__main__":
    # 测试
    processor = AIProcessor()
    test_title = "工信部发布《数字孪生工厂建设指南》"
    test_content = "工信部近日印发《数字孪生工厂建设指南》，提出到2027年在航空航天、汽车制造、能源电力等重点行业打造100个数字孪生工厂标杆。指南明确要求优先采用国产工业软件、国产GIS平台和国产渲染引擎，符合信创要求。超图软件、51World、飞渡科技等企业已参与标准制定。"
    print("=== 摘要测试 ===")
    print(processor.summarize(test_title, test_content))
    print("\n=== 深度解读测试 ===")
    print(processor.deep_dive(test_title, test_content, "政策解读"))
