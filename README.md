# 龙蟾 GEO 品牌监测平台

GEO (Generative Engine Optimization) 品牌监测系统，通过多模型 AI 问答 + 浏览器自动化爬取，监测品牌在 AI 搜索引擎中的曝光情况，分析信息来源质量，辅助品牌 SEO/GEO 策略优化。

## 系统架构

```
┌─────────────┐     ┌──────────┐     ┌────────────────┐
│   Nginx     │────▶│ Frontend │     │   PostgreSQL   │
│   :2888     │     │ Next.js  │     │   :5433        │
│             │────▶│ :3000    │     └────────────────┘
│             │     └──────────┘              ▲
│             │                               │
│             │     ┌──────────┐     ┌────────┴───────┐
│             │────▶│ Backend  │────▶│   Redis        │
│             │     │ FastAPI  │     │   :6380        │
│             │     │ :8000    │     │  DB0: cache    │
│             │     └──────────┘     │  DB1: broker   │
│             │                      │  DB2: results  │
│             │     ┌──────────┐     │  DB3: auth     │
│             │     │ Celery   │────▶└────────────────┘
│             │     │ Workers  │
│             │     ├──────────┤
│             │     │ default  │ ← API 类型任务 (concurrency=2)
│             │     │ browser  │ ← 浏览器任务 (concurrency=1)
│             │     └──────────┘
│             │          │
│             │     ┌────▼─────┐
│             │     │Playwright│
│             │     │Chromium  │
│             │     └──────────┘
└─────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + ECharts |
| **后端** | FastAPI + SQLAlchemy ORM + Pydantic v2 |
| **任务队列** | Celery + Redis Broker |
| **浏览器自动化** | Playwright + Chromium (持久化会话) |
| **数据库** | PostgreSQL 16 |
| **缓存/状态** | Redis 7 (多 DB 隔离) |
| **部署** | Docker Compose + Nginx 反向代理 |

## 核心功能

### 1. 多模型 AI 问答监测
- **API 模型**: 通过 OpenAI 兼容接口调用 GPT、Claude、Gemini 等
- **浏览器模型**: 自动化操控豆包(doubao.com)、DeepSeek(chat.deepseek.com) 网页版
- 批量提问 → 提取 AI 回答 → 解析引用来源 → 爬取来源页面内容

### 2. 浏览器爬虫引擎
- **豆包 Provider**: `参考X篇资料` 面板滚动提取、3策略答案抽取、参考面板自动关闭
- **DeepSeek Provider**: `X个网页` 虚拟列表滚动、搜索结果面板完整收集、面板自动关闭
- **会话管理**: 持久化浏览器 Profile、Redis 认证状态机、手机验证码 OTP 流程
- **验证码自动解决**: 基于视觉模型的 CAPTCHA 识别（滑块、点选、旋转等）

### 3. 品牌分析
- 品牌提及率分析 (跨模型对比)
- 竞品分析与对比
- 来源质量评分
- ECharts 可视化图表
- CSV 数据导出

### 4. 前端页面
| 页面 | 功能 |
|------|------|
| `/dashboard` | 数据概览仪表盘 |
| `/brands` | 品牌管理 (CRUD) |
| `/questions` | 问题库管理 |
| `/tasks` | 任务创建与执行监控 |
| `/qa-detail` | 问答明细 (答案格式化、来源预览、爬取内容) |
| `/sessions` | 浏览器会话管理 (登录状态、健康检查) |
| `/analysis` | 分析报告 (品牌分析、竞品对比、可视化) |

## 项目结构

```
longchan-geo/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # API 路由
│   │   │   ├── analysis.py      # 品牌分析、竞品、导出
│   │   │   ├── brands.py        # 品牌 CRUD
│   │   │   ├── questions.py     # 问题 CRUD
│   │   │   ├── sessions.py      # 浏览器会话管理
│   │   │   ├── stats.py         # 统计数据
│   │   │   └── tasks.py         # 任务管理 + 结果查询
│   │   ├── core/
│   │   │   ├── config.py        # 配置 (Pydantic Settings)
│   │   │   ├── database.py      # SQLAlchemy 引擎
│   │   │   └── security.py      # JWT 认证
│   │   ├── models/              # SQLAlchemy ORM 模型
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── services/
│   │   │   ├── llm/
│   │   │   │   ├── base.py              # BaseLLMProvider ABC
│   │   │   │   ├── openai_provider.py   # OpenAI 兼容 API
│   │   │   │   ├── browser_base.py      # BaseBrowserProvider
│   │   │   │   ├── doubao_provider.py   # 豆包浏览器 Provider
│   │   │   │   ├── deepseek_provider.py # DeepSeek 浏览器 Provider
│   │   │   │   └── source_parser.py     # 信息源解析
│   │   │   ├── captcha/         # CAPTCHA 自动解决
│   │   │   ├── analysis/        # 品牌分析服务
│   │   │   ├── auth_flow.py     # Redis 认证状态机
│   │   │   └── session_manager.py # 浏览器会话管理
│   │   └── tasks/
│   │       ├── execute_task.py  # 多模型任务执行引擎
│   │       └── browser_tasks.py # 浏览器健康检查任务
│   ├── tests/                   # 单元测试 + 集成测试
│   ├── Dockerfile               # 后端 + Celery Worker
│   └── Dockerfile.browser       # 浏览器 Worker (含 Playwright)
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router 页面
│   │   ├── components/          # shadcn/ui 组件
│   │   ├── lib/api.ts           # API 客户端
│   │   └── types/index.ts       # TypeScript 类型定义
│   └── Dockerfile
├── nginx/
│   └── nginx.conf               # 反向代理配置
├── docker/                      # 辅助 Docker 配置
└── docker-compose.yml           # 完整服务编排
```

## 快速部署

### 环境要求
- Docker + Docker Compose
- 4GB+ 内存 (浏览器 Worker 需要 2GB+)

### 1. 克隆项目

```bash
git clone https://github.com/Estrella9527/longchan-geo-.git
cd longchan-geo-
```

### 2. 配置环境变量

```bash
# 创建后端环境变量文件
cat > backend/.env << 'EOF'
# LLM API (OpenAI 兼容接口)
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-api-key-here
LLM_DEFAULT_MODEL=gpt-4o-mini

# JWT 密钥 (生产环境请修改)
JWT_SECRET=your-secret-key-here
EOF
```

### 3. 构建并启动

```bash
# 构建所有服务
docker compose build

# 启动
docker compose up -d

# 查看日志
docker compose logs -f
```

### 4. 访问系统

| 服务 | 地址 |
|------|------|
| **系统首页** | http://localhost:2888 |
| **前端直连** | http://localhost:3000 |
| **API 文档** | http://localhost:2888/docs |
| **PostgreSQL** | localhost:5433 |
| **Redis** | localhost:6380 |

## 服务说明

### Docker 容器

| 服务 | 说明 |
|------|------|
| `db` | PostgreSQL 16 数据库 |
| `redis` | Redis 7 (缓存 + Celery Broker + 认证状态) |
| `backend` | FastAPI 后端 API |
| `celery-worker` | Celery 默认队列 Worker (API 任务) |
| `celery-browser-worker` | Celery 浏览器队列 Worker (Playwright, concurrency=1) |
| `frontend` | Next.js 14 前端 (standalone 模式) |
| `nginx` | Nginx 反向代理 |

### Redis DB 分配

| DB | 用途 |
|----|------|
| DB 0 | 通用缓存 |
| DB 1 | Celery Broker |
| DB 2 | Celery Result Backend |
| DB 3 | 浏览器认证状态机 (OTP 流程) |

### Celery 队列

| 队列 | Worker | 并发 | 用途 |
|------|--------|------|------|
| `default` | celery-worker | 2 | API 类型 LLM 调用 |
| `browser` | celery-browser-worker | 1 | 浏览器自动化 (串行避免冲突) |

## LLM Provider 架构

```
BaseLLMProvider (ABC)
├── OpenAIProvider          — sync httpx, OpenAI 兼容 API
└── BaseBrowserProvider     — Playwright 浏览器自动化基类
      ├── DoubaoProvider    — doubao.com 网页版
      └── DeepSeekProvider  — chat.deepseek.com 网页版
```

- **API Provider**: 标准 OpenAI 兼容接口，支持任意兼容端点
- **Browser Provider**: 自动操控浏览器访问 AI 平台，提取真实的网页搜索源
  - 持久化浏览器 Profile (免重复登录)
  - 自动检测回答完成 (参考按钮 / 停止按钮 / 文本稳定)
  - 面板滚动 + 虚拟列表处理，完整收集引用来源
  - 爬取引用的原始网页内容

## 常用命令

```bash
# 重建并重启
docker compose build backend celery-browser-worker frontend
docker compose up -d

# 仅重启后端
docker compose restart backend celery-worker celery-browser-worker

# 查看浏览器 Worker 日志
docker compose logs -f celery-browser-worker

# 进入后端容器
docker compose exec backend bash

# 数据库连接
docker compose exec db psql -U postgres longchan_geo
```

## 开发说明

- 数据库使用 SQLAlchemy ORM，启动时 `create_all` 自动建表，无需手动迁移
- 前端 ESLint 严格模式，未使用的 import 会导致构建失败
- 浏览器 Worker 限制 `concurrency=1`，避免多个 Playwright 实例冲突
- 浏览器会话数据持久化在 Docker Volume `browser_sessions` 中

## License

Private Project - All Rights Reserved
