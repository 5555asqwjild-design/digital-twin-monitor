# 数字孪生行业资讯监控器

自动从6个顶级信源抓取数字孪生行业最新动态，经AI脱水处理后实时推送到飞书。

## 数据源覆盖

| 类别 | 来源 | 重点监控 |
|---|---|---|
| 行业标准 | Digital Twin Consortium | 白皮书、互操作性标准 |
| 地学标准 | OGC | 3D Tiles、CityGML |
| 渲染引擎 | Unreal Engine Blog | Pixel Streaming、大世界坐标 |
| GPU/仿真 | NVIDIA Developer Blog | Omniverse、OpenUSD、IoT同步 |
| 三维地理 | Cesium Blog | Cesium for Unreal、流式加载 |
| 开源社区 | Hacker News | 新工具、踩坑经验 |

## 快速开始

### 1. 部署到 GitHub Actions（推荐，零成本）

1. Fork 本仓库到你的 GitHub
2. 设置 Secrets（Settings -> Secrets and variables -> Actions）：
   - `FEISHU_WEBHOOK`：飞书群机器人 webhook 地址
   - `FEISHU_SECRET`：飞书机器人加签密钥（可选）
   - `AI_API_KEY`：大模型 API Key（OpenAI 兼容）
   - `AI_API_BASE`：API 基础地址（默认 OpenAI 官方）
   - `AI_MODEL`：模型名称（默认 gpt-4o-mini）
3. 在 Actions 页面手动触发一次测试

### 2. 本地运行

```bash
pip install -r requirements.txt

# 设置环境变量
export FEISHU_WEBHOOK="https://open.feishu.cn/..."
export AI_API_KEY="sk-..."

# 运行监控
python main.py

# 仅测试不推送
python main.py --dry-run

# 深度爆破单篇文章
python main.py --deep-dive "https://..." --focus "渲染架构"
```

## 使用方式

### 日常推送
每6小时自动检查，发现新文章时推送到飞书：
- 标题 + 一句话AI摘要 + 原文链接
- 按来源分组，卡片式展示

### 深度爆破
随时对单篇文章做深度解读：
```bash
python main.py --deep-dive "文章URL" --focus "数据联动"
```
AI 会输出结构化干货：核心结论、技术要点、对你的价值、关键术语。

## 项目结构

```
.
├── config.py          # 数据源和配置
├── scraper.py         # 网页抓取模块
├── ai_processor.py    # AI摘要/爆破模块
├── feishu_bot.py      # 飞书推送模块
├── main.py            # 主控流程
├── requirements.txt   # 依赖
└── .github/workflows/ # GitHub Actions 定时任务
```

## 自定义扩展

- **添加新数据源**：在 `config.py` 的 `SOURCES` 中添加，在 `scraper.py` 中实现对应解析器
- **修改推送频率**：编辑 `.github/workflows/monitor.yml` 中的 `cron` 表达式
- **切换推送方式**：修改 `feishu_bot.py` 为钉钉/企业微信格式
