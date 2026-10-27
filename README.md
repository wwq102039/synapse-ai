> **⚠️ 使用声明**
>
> 本项目中的安全测试模块（端口扫描、子域名枚举、Web 漏洞探测、WiFi 相关工具等）
> **仅限用于你拥有明确书面授权的目标，或你自己的本地实验环境**。
> 未经授权对他人网络、主机或应用进行扫描、爆破或攻击，在包括中国大陆在内的多数司法辖区构成违法行为。
> 作者不对任何滥用行为承担责任。

---

# Synapse AI - AI Brain Studio

> **模型即大脑，工具即感官。** 基于 DeepSeek API 的智能体工作台，AI 自主决策何时调用何种工具。

---

## 项目概述

Synapse AI 是一个**中小型 AI Agent 项目**，核心理念是将大语言模型视为"大脑"，将各类功能模块视为"感官器官"。大脑（DeepSeek）通过 Function Calling 自主判断：

- **是否需要工具** — 简单对话直接用模型知识回答
- **选择哪个工具** — 从 14 个工具中选出最合适的
- **何时结束任务** — 获取工具结果后判断是否需要继续调用

整个过程在 Web 界面上以**神经元动画 + 思维链**形式实时可视化。

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **AI 引擎** | DeepSeek API (`deepseek-chat`) | Function Calling 驱动工具调用决策 |
| **后端** | Python 3.11 + FastAPI | REST API + WebSocket 双通道 |
| **前端** | HTML5 + CSS3 + Vanilla JS | Canvas 神经元动画、暗色科幻主题 |
| **CLI** | Python 异步终端 | 彩色 ANSI 输出、完整对话功能 |
| **数据库** | SQLite | 记忆存储、对话持久化 |
| **环境管理** | Anaconda (`synapse-ai`) | 独立 Python 虚拟环境 |

---

## 项目结构

```
synapse-ai/
├── backend/
│   ├── main.py                    # FastAPI 服务入口 (REST + WebSocket)
│   ├── brain.py                   # AI Brain 核心 — 工具调用决策引擎
│   ├── config.py                  # 环境变量配置
│   └── tools/
│       ├── __init__.py            # 工具注册中心 + OpenAI Schema 转换
│       ├── filesystem.py          # 文件系统: 读/写/列目录/搜索
│       ├── web_search.py          # 网页搜索 + 内容抓取 (DuckDuckGo)
│       ├── code_executor.py       # Python 沙箱代码执行
│       ├── calculator.py          # 高级数学表达式求值
│       ├── system_info.py         # 系统信息: CPU/内存/磁盘/网络
│       ├── database_query.py      # SQLite 查询 + 键值记忆存储
│       ├── text_processor.py      # 文本分析 (统计/提取/哈希/正则)
│       └── weather.py             # 实时天气查询 (Open-Meteo API)
├── frontend/
│   ├── index.html                 # SPA 主页面 (三栏布局)
│   ├── css/style.css              # 暗色科幻主题样式
│   └── js/
│       ├── brain-viz.js           # Canvas 2D 神经元网络动画
│       ├── chat.js                # WebSocket 聊天 + Markdown 渲染
│       ├── tools-panel.js         # 工具列表管理
│       └── app.js                 # 应用主逻辑 + 配置 + 思维链
├── cli/
│   └── cli.py                     # 命令行交互界面
├── .env.example                   # 环境变量模板
├── requirements.txt               # Python 依赖清单
└── run.bat                        # Windows 一键启动脚本
```

---

## 工具列表 (14 个)

AI 大脑可以自主调用的全部工具：

| 工具 | 图标 | 功能描述 |
|------|------|----------|
| `file_read` | 📄 | 读取文件内容 |
| `file_list` | 📁 | 列出目录文件 |
| `file_write` | ✏ | 写入文件 |
| `file_search` | 🔍 | 按模式搜索文件 |
| `web_search` | 🌐 | DuckDuckGo 网页搜索 |
| `web_fetch` | 📡 | 抓取网页内容 |
| `code_execute` | 💻 | Python 沙箱代码执行 |
| `calculator` | 🔢 | 数学表达式求值 |
| `system_info` | 🖥 | 系统信息查询 |
| `weather` | ☁ | 实时天气查询 |
| `db_query` | 🗃 | SQLite 数据库查询 |
| `db_memory` | 🧠 | 键值记忆存取 |
| `text_process` | 📝 | 文本分析处理 |
| `text_transform` | 🔀 | 文本格式转换 |

---

## 快速开始

### 环境要求

- Anaconda 已安装
- DeepSeek API Key（[获取地址](https://platform.deepseek.com/api_keys)）
- Windows / Linux / macOS

### 安装与启动

```bash
# 1. 克隆项目
cd synapse-ai

# 2. 创建 conda 环境并安装依赖
conda create -n synapse-ai python=3.11 -y
conda activate synapse-ai
pip install -r requirements.txt

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env 文件，填入你的 DEEPSEEK_API_KEY

# 4. 启动服务
# 方式一: 双击 run.bat (Windows)
# 方式二: 命令行启动
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8765 --reload

# 5. 打开浏览器访问 http://localhost:8765
```

### CLI 模式

```bash
conda activate synapse-ai
cd cli
python cli.py
```

CLI 支持的命令：

| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助 |
| `/quit` | 退出程序 |
| `/clear` | 清空对话历史 |
| `/tools` | 列出可用工具 |
| `/model` | 显示当前模型 |
| `/history` | 查看对话历史 |
| `/save <文件>` | 保存对话到 JSON 文件 |

---

## API 接口

### REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |
| `GET` | `/api/tools` | 获取所有工具列表 |
| `POST` | `/api/chat` | 发送消息（标准 HTTP） |
| `POST` | `/api/config` | 运行时更新 API Key / Model |

#### POST /api/chat 示例

```json
// 请求
{
  "message": "北京现在天气怎么样？",
  "history": []
}

// 响应
{
  "response": "北京现在晴天，温度 28°C，湿度 45%...",
  "thoughts": [
    { "type": "thinking", "content": "用户问天气，需要调用 weather 工具" },
    { "type": "tool_call", "content": "Invoking: weather", "metadata": { "name": "weather", "args": { "city": "Beijing" } } },
    { "type": "tool_result", "content": "{...weather data...}" },
    { "type": "response", "content": "北京现在晴天..." }
  ],
  "tool_calls_count": 1,
  "timestamp": "2026-05-28T18:55:00"
}
```

### WebSocket

```
ws://localhost:8765/ws/chat
```

实时推送 AI 思维链中的每一步，前端用于驱动神经元动画。

---

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│                    用户界面层                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Web UI   │  │  CLI     │  │  REST API 调用方  │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
└───────┼──────────────┼────────────────┼────────────┘
        │              │                │
        ▼              ▼                ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI 服务层                       │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  REST Endpoints  │  │  WebSocket (实时思维流)    │ │
│  └────────┬─────────┘  └────────────┬─────────────┘ │
└───────────┼─────────────────────────┼───────────────┘
            │                         │
            ▼                         ▼
┌─────────────────────────────────────────────────────┐
│              Synapse Brain (AI 大脑)                  │
│  ┌────────────────────────────────────────────────┐ │
│  │  1. 构建 System Prompt + 工具 Schema             │ │
│  │  2. 调用 DeepSeek API (带 Function Calling)      │ │
│  │  3. 解析响应: stop → 返回 / tool_calls → 执行工具 │ │
│  │  4. 工具结果反馈回模型，循环直到任务完成          │ │
│  └────────────────────────────────────────────────┘ │
└───────────┬─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────┐
│               工具注册表 (14 Tools)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ 文件系统  │ │ 网络搜索  │ │ 代码执行  │  ...        │
│  └──────────┘ └──────────┘ └──────────┘             │
└─────────────────────────────────────────────────────┘
```

### 决策循环

1. **感知**: 用户消息 + 对话历史 → 构建 messages 数组
2. **决策**: DeepSeek 分析，返回 `finish_reason: "stop"` 或 `"tool_calls"`
3. **执行**: 如果选择工具调用，执行工具函数并获取结果
4. **反馈**: 工具结果以 `role: "tool"` 消息形式追加到 messages
5. **循环**: 最多 8 轮，直到模型认为任务完成

---

## 设计亮点

### 1. 实时神经元可视化
Canvas 2D 绘制的神经网络动画，AI 思考时神经元活跃度升高，工具调用时信号粒子沿突触传递。

### 2. 思维链透明化
每一次 AI 的决策（思考、调用工具、获取结果、生成回复）都在右侧面板实时展示，让用户"看到"AI 的思考过程。

### 3. 模型自主决策
不是硬编码的工具调用流程，而是让 DeepSeek 自己在 8 轮对话中决定需要哪些工具、按什么顺序调用。

### 4. 多端统一
Web UI / CLI / REST API 共享同一个 Brain 实例，换端不换体验。

### 5. 长期记忆
`db_memory` 工具让 AI 可以主动存取键值对记忆，跨对话保留上下文。

---

## 配置说明

`.env` 文件配置项：

```env
DEEPSEEK_API_KEY=sk-xxxxxxxx     # DeepSeek API 密钥（必填）
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1  # API 地址
DEEPSEEK_MODEL=deepseek-chat     # 模型: deepseek-chat / deepseek-reasoner
SERVER_HOST=0.0.0.0              # 服务监听地址
SERVER_PORT=8765                 # 服务端口
```

---

## License

MIT
