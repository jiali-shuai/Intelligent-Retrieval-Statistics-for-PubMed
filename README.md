# PubMed 文献计量与综述分析系统

基于 **FastAPI + LangGraph 多智能体 + Vue3** 的一站式 PubMed 文献分析工具。输入一个研究关键词，系统自动扩展检索式、抓取文献、生成计量统计与可视化、提取研究热点词云、筛选高影响力文献，并撰写一篇中文综述报告。

---

## 功能特性

- **智能检索**：将中文/英文关键词翻译扩展为 PubMed 检索式，按发表年份限定「近 N 年」范围
- **计量统计**：文献年份分布、JCR 分区（Q1-Q4）、中科院分区（1-4 区）、影响因子分布、高产期刊 Top15
- **研究热点**：基于标题 / 作者关键词 / MeSH 主题词生成词云与研究方向归纳
- **高影响力文献**：按影响因子降序筛选近 N 年 Top 文献
- **智能综述**：综述环节启用大模型深度思考（thinking mode），生成结构化中文综述
- **历史记录**：所有检索与分析结果持久化到 MySQL，支持完整复现任意一次历史分析页面

---

## 界面展示

### 分析页（检索入口）

输入关键词并可按需设置「近 N 年 / 解析篇数 / Top 篇数」，一键启动多智能体分析。

![分析页](<picture/屏幕截图 2026-10-04 143128.png>)

### 历史记录

所有分析结果按时间倒序展示，支持回看任意一次分析的完整结果。

![历史记录](<picture/屏幕截图 2026-10-04 143142.png>)

### 计量指标与年份分布

展示命中总数、解析文献数、高影响力文献数、平均 / 最高影响因子与覆盖率，以及文献年份分布趋势。

![计量指标与年份分布](<picture/屏幕截图 2026-10-04 143203.png>)

### 分区分布（JCR / 中科院）

JCR 分区（Q1-Q4）与中科院分区（1-4 区）各自独立统计、分别展示。

![分区分布](<picture/屏幕截图 2026-10-04 143210.png>)

### 影响力 Top 文献

按影响因子降序筛选近 N 年高影响力文献，附分区、年份与 PubMed 链接。

![影响力 Top 文献](<picture/屏幕截图 2026-10-04 143157.png>)

---

## 技术架构

### 多智能体编排（LangGraph Supervisor 模式）

```
                     ┌─────────────┐
                     │  Supervisor │  ← 总管：唯一决策中枢
                     │   总管       │
                     └──────┬──────┘
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
      ┌──────────────┐ ┌──────────┐ ┌──────────────┐
      │ search_agent │ │stats_agent│ │ review_agent │
      │  检索策略员   │ │  统计员   │ │  综述撰写员   │
      └──────────────┘ └──────────┘ └──────────────┘
```

- **总管**：判断样本是否充分，决定分发给哪个成员或结束；样本不足时指挥检索策略员放宽检索式重试（最多 `MAX_ROUNDS` 轮）
- **检索策略员**：构建检索式并调用 PubMed 工具抓取文献
- **统计员**：完成计量统计并生成词云与研究方向
- **综述撰写员**：筛选 Top 文献并撰写中文综述（唯一启用深度思考的环节）

成员之间不直接通信，全部经由总管调度（Supervisor 模式）。

### 目录结构

```
yanchang/
├── backend/
│   ├── agent/                  # 多智能体
│   │   ├── agent.py            # 总管 + LangGraph 编排器
│   │   ├── search_agent.py     # 检索策略员
│   │   ├── stats_agent.py      # 统计员
│   │   ├── review_agent.py     # 综述撰写员
│   │   ├── tools.py            # 成员可调用的工具
│   │   ├── llm.py              # 大模型配置与输出解析
│   │   ├── prompt_loader.py    # prompt 加载
│   │   └── prompts/            # 各 agent 的 prompt 模板
│   ├── api/                    # 接口层
│   │   ├── analysis.py         # 一站式分析接口
│   │   ├── history.py          # 历史记录接口
│   │   └── router.py           # 路由注册 + 应用启动
│   ├── pubmed/                 # PubMed 检索
│   │   ├── eutils.py           # NCBI E-utilities 封装（重试 / 分批容错）
│   │   ├── analyzer.py         # 计量统计（纯函数）
│   │   └── client.py           # 检索门面
│   ├── metrics/                # 期刊指标
│   │   ├── impact.py           # JCR 影响因子 / 分区匹配
│   │   ├── jcr.json            # JCR 数据（影响因子 + JCR 分区）
│   │   └── sci.json            # 中科院分区数据
│   ├── db/                     # 持久化
│   │   ├── engine.py           # Tortoise 初始化 + 同步桥接
│   │   ├── models.py           # 数据模型
│   │   └── repository.py       # 仓储层
│   ├── config.py               # 配置
│   ├── main.py                 # 启动入口
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── src/
        ├── views/              # 页面：分析页 / 历史页
        ├── components/         # 共享组件
        ├── api/                # 接口封装
        └── router/             # 路由
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0

### 1. 后端

```bash
cd backend
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，至少填写 NCBI_API_KEY 与 DEEPSEEK_API_KEY
```

启动服务：

```bash
python main.py
# 服务运行在 http://localhost:8000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

前端开发服务器已配置代理，`/api` 请求自动转发到 `http://localhost:8000`。

---

## 环境变量说明

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `NCBI_API_KEY` | 是 | - | NCBI API Key，配置后请求频率上限由 3 次/秒 提升至 10 次/秒 |
| `NCBI_EMAIL` | 否 | `pubmed-analysis@example.com` | NCBI 要求提供的联系邮箱 |
| `DEEPSEEK_API_KEY` | 是 | - | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | 否 | `https://api.deepseek.com/v1` | API 地址 |
| `DEEPSEEK_MODEL` | 否 | `deepseek-flash` | 模型名称 |
| `DEEPSEEK_THINKING_EFFORT` | 否 | `high` | 深度思考强度：`low` / `high` / `max`，仅综述环节启用 |
| `DB_HOST` | 否 | - | MySQL 主机，留空则**跳过入库** |
| `DB_PORT` | 否 | `3306` | MySQL 端口 |
| `DB_USER` | 否 | - | MySQL 用户 |
| `DB_PASSWORD` | 否 | - | MySQL 密码 |
| `DB_NAME` | 否 | - | 数据库名 |

> MySQL 为可选依赖：`DB_HOST` 或 `DB_NAME` 为空时，系统正常运行但跳过历史记录入库，`/api/history/*` 接口返回 503。

---

## API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/analysis/run` | 一站式文献计量分析（多智能体编排） |
| `GET` | `/api/history/runs` | 历史询问列表（分页，按时间倒序） |
| `GET` | `/api/history/runs/{query_id}` | 单次询问详情（含 AI 生成结果） |

### 请求示例

```bash
curl -X POST http://localhost:8000/api/analysis/run \
  -H "Content-Type: application/json" \
  -d '{"keyword": "癌症免疫治疗", "recent_years": 5, "max_fetch": 300}'
```

| 字段 | 类型 | 范围 | 说明 |
| --- | --- | --- | --- |
| `keyword` | string | 非空 | 检索关键词，支持中文/英文 |
| `recent_years` | int | 1-10 | 「近 N 年」口径 |
| `max_fetch` | int | 1-500 | 最多解析文献数 |


---


## 关键设计说明

- **影响因子与分区**：PubMed 不提供 IF 与分区，系统使用本地 JCR / 中科院分区数据，按期刊全称与缩写归一化匹配。两类分区各自独立统计、分别展示。
- **命中数 vs 解析数**：`total_hits` 为 PubMed 检索式命中的全量文献数，`fetched` 为本次实际解析入库的抽样量（受 `max_fetch` 限制）。
- **健壮性**：PubMed 请求对超时 / 限流(429) / 服务端错误(5xx) 做指数退避重试；efetch 按 200 篇分批，单批失败自动跳过，避免个别批次拖垮整体。
- **深度思考**：仅综述撰写环节开启，其余结构化环节关闭思考以提升速度。

---

## 技术栈

**后端**：FastAPI · LangGraph · LangChain · DeepSeek · Tortoise ORM · MySQL · requests

**前端**：Vue 3 · Vite · Vue Router · ECharts · echarts-wordcloud · axios

---

## 说明

本项目用于文献计量与综述分析的演示，**AI 生成的统计口径、词云权重与综述内容仅供参考**，请以原文为准。
