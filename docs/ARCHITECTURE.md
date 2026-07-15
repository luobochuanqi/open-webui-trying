# Open WebUI 仓库架构报告

> 基于 v0.10.2 代码分析，不依赖文档/README，纯代码推导。

---

## 一、项目全景

```
open-webui/
├── backend/              # Python 后端 (FastAPI + SQLAlchemy)
├── src/                  # 前端 (Svelte 5 + SvelteKit + Tailwind CSS 4)
├── static/               # 静态资源
├── test/                 # 测试 (仅有 1 个 fixture 文件)
├── scripts/              # 工具脚本
├── docs/                 # 文档
│
├── docker-compose*.yaml  # 9 个 Compose 文件 (分层 override)
├── Dockerfile            # 多阶段构建 (支持 CUDA/Ollama 内嵌/SLIM)
├── package.json          # Node 依赖
├── pyproject.toml        # Python 依赖 + 构建配置
├── svelte.config.js      # SvelteKit 配置
├── vite.config.ts        # Vite 构建
├── tailwind.config.js    # Tailwind CSS v4
├── tsconfig.json         # TypeScript
└── Makefile              # 构建自动化
```

---

## 二、后端架构 (`backend/open_webui/`)

### 2.1 入口与生命周期 (`main.py`)

FastAPI 应用启动流程：

```
lifespan()
├── reset/import 配置
├── 执行数据库迁移 (Alembic)
├── seed 默认配置
├── 创建管理员账号 (WEBUI_ADMIN_EMAIL/PASSWORD)
├── 安装函数/工具依赖
├── 连接 Redis
├── 初始化 embedding/reranking
├── 预拉取模型列表
├── 初始化工具服务器 (MCP/OpenAPI)
├── 启动后台任务 (会话清理/自动化调度)
└── 发布 SYSTEM_STARTUP_COMPLETED 事件
```

中间件链（注册顺序）：
```
RedirectMiddleware → SecurityHeadersMiddleware → CommitSessionMiddleware
→ AuthTokenMiddleware → WebsocketUpgradeGuardMiddleware → CORSMiddleware
→ [CompressMiddleware] → [AuditLoggingMiddleware]
```

WebSocket 挂载于 `/ws` (Socket.IO)，旁路 FastAPI 直接挂载。

### 2.2 API 路由 (`routers/`)

30 个路由模块，全部挂载在 `/api/v1/*` 下：

| 路由文件 | 前缀 | 核心功能 |
|---|---|---|
| `ollama.py` | `/ollama` | Ollama 模型管理 (拉取/删除/列表) 和代理 |
| `openai.py` | `/openai` | OpenAI API 兼容代理 |
| `pipelines.py` | `/api/v1/pipelines` | Pipeline 管理 (CRUD) |
| `tasks.py` | `/api/v1/tasks` | 后台任务 CRUD |
| `images.py` | `/api/v1/images` | 图像生成 (AUTOMATIC1111/ComfyUI) |
| `audio.py` | `/api/v1/audio` | TTS/STT 语音合成与识别 |
| `retrieval.py` | `/api/v1/retrieval` | RAG 检索查询 + 向量库/搜索配置 |
| `configs.py` | `/api/v1/configs` | 配置 CRUD (键值对) |
| `auths.py` | `/api/v1/auths` | 认证 (登录/注册/OAuth/Signout) |
| `users.py` | `/api/v1/users` | 用户 CRUD + 设置 |
| `channels.py` | `/api/v1/channels` | 频道 (CRUD/消息/成员) |
| `chats.py` | `/api/v1/chats` | 聊天 CRUD/导入导出/标签/克隆 |
| `notes.py` | `/api/v1/notes` | 笔记 CRUD |
| `models.py` | `/api/v1/models` | 自定义模型 CRUD |
| `knowledge.py` | `/api/v1/knowledge` | 知识库 CRUD |
| `prompts.py` | `/api/v1/prompts` | 提示词 CRUD |
| `tools.py` | `/api/v1/tools` | 工具 CRUD |
| `skills.py` | `/api/v1/skills` | 技能 CRUD |
| `memories.py` | `/api/v1/memories` | 用户记忆 CRUD |
| `folders.py` | `/api/v1/folders` | 文件夹 CRUD |
| `groups.py` | `/api/v1/groups` | 用户组 CRUD + 权限 |
| `files.py` | `/api/v1/files` | 文件上传/下载/内容获取 |
| `functions.py` | `/api/v1/functions` | 函数插件 CRUD + 导出 |
| `evaluations.py` | `/api/v1/evaluations` | A/B 模型评测 (反馈/排行榜) |
| `analytics.py` | `/api/v1/analytics` | 用户/模型使用统计 |
| `utils.py` | `/api/v1/utils` | 文档转换/代码执行/标题生成等 |
| `terminals.py` | `/api/v1/terminals` | 终端服务器连接管理 |
| `automations.py` | `/api/v1/automations` | 自动化 (CRUD/触发) |
| `calendar.py` | `/api/v1/calendars` | 日历事件 CRUD |
| `scim.py` | `/api/v1/scim/v2` | SCIM 2.0 身份管理 (条件挂载) |

核心端点（直接在 `main.py` 中定义）：

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/models` | GET | 获取所有模型 (权限过滤 + 排序) |
| `/api/models/base` | GET | 获取基础模型 (管理员) |
| `/api/models/unload` | POST | 卸载模型 (Ollama/llama.cpp) |
| `/api/chat/completions` | POST | 聊天补全 (兼容 OpenAI API) |
| `/api/embeddings` | POST | 嵌入向量生成 |
| `/api/v1/*` | 各种 | 兼容性别名 |

### 2.3 ORM 模型 (`models/`)

25 个 SQLAlchemy 异步模型，核心表：

| 表 | 关键字段 | 用途 |
|---|---|---|
| `chat` | id, user_id, title, chat(JSON), share_id, archived, pinned, folder_id | 聊天会话 |
| `chat_message` | id, chat_id, parent_id, role, content, model, files(JSON) | 聊天消息 (树形结构) |
| `message` | id, channel_id, user_id, content, data(JSON) | 频道消息 |
| `user` | id, name, email, role, password, api_key, oauth_sub | 用户 |
| `channel` | id, name, type(dm/group/public), description | 频道 |
| `config` | id(key), value(JSON) | 全局配置 (键值对) |
| `knowledge` | id, name, description, data(JSON) | 知识库 |
| `file` | id, user_id, filename, path, meta(JSON) | 文件 |
| `function` | id, user_id, name, content(Python), meta(JSON) | 函数插件 |
| `tool` | id, user_id, name, content, meta(JSON) | 工具 |
| `skill` | id, user_id, name, content, meta(JSON) | 技能 |
| `prompt` | id, user_id, name, content | 提示词 |
| `folder` | id, name, items(JSON), is_expanded | 文件夹 |
| `tag` | id, name, type, chat_id, user_id | 标签 |
| `feedback` | id, message_id, user_id, rating, comment | 反馈/评测 |
| `note` | id, user_id, title, content, is_pinned | 笔记 |
| `memory` | id, user_id, content, path, meta | 用户记忆 |
| `automation` | id, name, trigger, schedule, actions(JSON) | 自动化 |
| `calendar_event` | id, user_id, title, start, end, recurrence | 日历事件 |
| `group` | id, name, description, permissions(JSON) | 用户组 |
| `access_grant` | id, user_id, resource_type, resource_id, permission | 访问授权 |
| `shared_chat` | id, chat_id, hash, user_id | 共享聊天 |

### 2.4 RAG 子系统 (`retrieval/`)

三层架构：

```
                   ┌──────────────┐
                   │   retrieval  │  ← 统一检索接口
                   │   router     │
                   └──────┬───────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
    ┌─────▼─────┐   ┌────▼────┐   ┌──────▼───┐
    │  Vector   │   │   Web   │   │ Loaders  │
    │   DBs     │   │  Search │   │(文档解析) │
    └─────┬─────┘   └────┬────┘   └──────┬───┘
          │              │               │
          │     ┌────────┼────────┐      │
          │     │ DuckDuckGo      │      │
          │     │ Google PSE      │      ├── Marker
          │     │ Bing            │      ├── Tavily
          │     │ Brave           │      ├── YouTube
          │     │ SearXNG         │      ├── Mistral OCR
          │     │ Jina            │      ├── PaddleOCR
          │     │ Firecrawl       │      ├── MineRu
          │     │ Tavily          │      └── Microsoft Web IQ
          │     │ Perplexity      │
          │     │ SerpAPI/Serper  │
          │     │ Exa/Linkup/Kagi │
          │     │ + 更多 (共28种) │
          │     └────────────────┘
          │
    ┌─────┴─────────────────────┐
    │ ChromaDB (默认)            │
    │ pgvector / Qdrant / Milvus│
    │ Pinecone / Weaviate       │
    │ Elasticsearch / OpenSearch│
    │ MariaDB Vector / Oracle   │
    │ OpenGauss / Valkey / S3   │
    │ (共15种向量数据库)          │
    └───────────────────────────┘
```

加载引擎选择逻辑 (`retrieval/web/utils.py:857-923`)：
- `WEB_LOADER_ENGINE=''` 或 `'safe_web'` — 简单 HTTP 请求 (默认，无需额外服务)
- `'playwright'` — Chromium 渲染 JS 页面 (需 Playwright 服务)
- `'firecrawl'` / `'tavily'` / `'microsoft_web_iq'` / `'external'` — 第三方抓取服务

### 2.5 事件系统 (`events.py`)

约 50 个预定义事件，涵盖系统生命周期、配置变更、聊天/消息/文件的 CRUD。支持多 webhook 注册。

事件类别示例：
- 系统：`system.startup.started/completed`, `system.shutdown.*`
- 配置：`config.updated`, `config.connections.updated`, `config.tool_servers.updated`
- 聊天：`chat.created`, `chat.updated`, `chat.deleted`, `chat.title.generated`
- 消息：`message.created`, `message.rated`
- 文件：`file.uploaded`, `file.deleted`
- 用户：`user.created`, `user.deleted`, `user.logged_in`

### 2.6 工具系统

三层工具体系：

1. **内置工具** (`tools/builtin.py`, `tools/knowledge_fs.py`)
2. **用户自定义工具** — 在 Workspace 中编写的 Python 脚本，通过 `RestrictedPython` 沙箱执行
3. **工具服务器** — MCP (Model Context Protocol) 或 OpenAPI 服务器，通过 `utils/mcp/client.py` 连接

### 2.7 代码执行沙箱

支持两种代码执行方式：
- **后端** — Python 沙箱 (RestrictedPython)，通过 `utils/code_interpreter.py` 管理
- **前端浏览器** — Pyodide (WebAssembly Python)，通过 Web Worker 持久化

### 2.8 基础设施

- **数据库**：SQLAlchemy 异步 (SQLite 默认 / PostgreSQL 可选)
- **缓存**：Redis (会话存储、任务队列、速率限制)
- **可观测性**：OpenTelemetry (需启用 `ENABLE_OTEL`)，含 metrics/logs/tracing
- **审计日志**：可配置 path/level/method 过滤
- **存储**：本地文件系统，抽象层 `storage/provider.py`

---

## 三、前端架构 (`src/`)

### 3.1 路由 (`routes/`)

```
+layout.svelte          # 根布局: Socket.IO 连接, Pyodide 初始化, i18n, 主题
├── +layout.js          # 布局数据加载
├── +error.svelte       # 全局错误页
│
├── (app)/              # 主应用组 (需要认证)
│   ├── +layout.svelte  # 应用布局: 侧边栏 + 导航
│   ├── +page.svelte    # 根重定向
│   │
│   ├── admin/          # 管理面板
│   │   ├── +page.svelte
│   │   ├── analytics/   ─── Dashboard, ModelUsage, UserUsage
│   │   ├── evaluations/ ─── Feedbacks, Leaderboard, ModelActivity
│   │   ├── functions/   ─── FunctionEditor, FunctionMenu
│   │   ├── settings/    ─── 16个设置选项卡
│   │   └── users/       ─── UserList, Groups, Add/Edit User
│   │
│   ├── c/[id]/         # 聊天会话页面
│   ├── channels/[id]/  # 频道聊天页面
│   ├── home/           # 首页
│   ├── notes/          # 笔记 CRUD
│   ├── calendar/       # 日历视图
│   ├── automations/    # 自动化列表/编辑器
│   ├── playground/     # 模型测试场 (chat/completions/images)
│   └── workspace/      # 工作台
│       ├── knowledge/  ─── 知识库 CRUD
│       ├── models/     ─── 模型编辑器
│       ├── prompts/    ─── 提示词 CRUD
│       ├── skills/     ─── 技能编辑器
│       ├── tools/      ─── 工具编辑器
│       └── functions/  ─── 函数编辑器
│
├── auth/               # 登录页
├── error/              # 错误页
├── s/[id]/             # 共享聊天查看
└── watch/              # 监视页
```

### 3.2 API 封装 (`lib/apis/`)

29 个模块，每个对应一个后端 API，使用 `fetch` + Bearer token 认证。核心模式：

```typescript
export const getXxx = async (token, ...params) => {
  const res = await fetch(`${WEBUI_BASE_URL}/api/v1/xxx`, {
    headers: { authorization: `Bearer ${token}` }
  })
  return res.json()
}
```

### 3.3 状态管理 (`lib/stores/index.ts`)

100+ 个 Svelte writable stores，核心分类：

| 类别 | Stores |
|---|---|
| 应用状态 | `config`, `user`, `settings`, `theme`, `mobile` |
| 数据模型 | `chats`, `models`, `channels`, `knowledge`, `tools`, `skills` |
| 通信 | `socket`, `socketConnected`, `activeUserIds` |
| UI 状态 | `showSidebar`, `showSettings`, `showControls`, `showArtifacts` |
| 聊天 | `chatId`, `chatTitle`, `temporaryChatEnabled`, `chatRequestQueues` |
| 桌面集成 | `isApp`, `appInfo`, `desktopEvent` |

### 3.4 关键组件

```
chat/Messages/              # 消息渲染核心
├── Message.svelte          # 单条消息容器
├── UserMessage.svelte      # 用户消息
├── ResponseMessage.svelte  # AI 回复 (含状态/跟进/Web搜索结果)
├── ContentRenderer.svelte  # 内容渲染分发
├── Markdown.svelte         # Markdown 转 Svelte 组件
│   ├── MarkdownTokens.svelte       # 块级 token
│   ├── MarkdownInlineTokens.svelte # 行内 token
│   ├── KatexRenderer.svelte        # 数学公式
│   ├── Source.svelte               # 源引用
│   └── AlertRenderer.svelte        # 警告块
├── CodeBlock.svelte        # 代码高亮 + 执行/复制按钮
├── StructuredOutputRenderer.svelte # 结构化输出渲染
└── Citations.svelte        # 引用显示

chat/MessageInput/          # 输入系统
├── InputMenu.svelte        # 菜单按钮
├── FilesOverlay.svelte     # 文件选择
├── CallOverlay.svelte      # 语音/视频通话
├── VoiceRecording.svelte   # 录音
├── CommandSuggestionList.svelte # / 命令补全
└── Commands/               # / 子命令
    ├── Emojis.svelte
    ├── Knowledge.svelte
    ├── Models.svelte
    ├── Prompts.svelte
    └── Skills.svelte
```

### 3.5 Markdown 渲染管线

自定义 `marked` 扩展链：
```
citation-extension → colon-fence-extension → footnote-extension
→ katex-extension → mention-extension → strikethrough-extension
```

支持格式：标准 Markdown、KaTeX (数学)、Mermaid (图表)、代码高亮 (Shiki)、警告块、折叠块、HTML token 渲染。

### 3.6 前端特有功能

- **Pyodide 浏览器 Python**：`lib/pyodide/` 通过 Web Worker 实现浏览器内 Python 执行，`workers/pyodide.worker.ts` 管理持久化文件系统
- **TTS 语音合成**：`workers/kokoro.worker.ts` 使用 Kokoro.js 在浏览器端本地 TTS
- **富文本编辑器**：基于 TipTap (ProseMirror)，支持协作编辑 (Yjs)
- **图标系统**：178 个内联 SVG Svelte 组件

### 3.7 国际化

61 个语言包，通过 i18next 管理，支持浏览器自动检测语言。

---

## 四、Docker 部署

### Docker Compose 分层 override

```
docker-compose.yaml          # 基础: ollama + open-webui
├── docker-compose.gpu.yaml  # NVIDIA GPU 直通
├── docker-compose.amdgpu.yaml # AMD GPU 直通
├── docker-compose.api.yaml  # 暴露 Ollama API 端口
├── docker-compose.data.yaml # 本地目录持久化
├── docker-compose.otel.yaml # OpenTelemetry 可观测性
├── docker-compose.playwright.yaml # Playwright 网页渲染
└── docker-compose.a1111-test.yaml # A1111 图像生成测试
```

组合方式：
```bash
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml -f docker-compose.data.yaml up -d
```

`docker-compose-launcher.sh` 是交互式启动器，自动检测 GPU 并组装 `-f` 参数链。

### Dockerfile

多阶段构建，支持 build args：
| Arg | 默认值 | 作用 |
|---|---|---|
| `USE_CUDA` | `false` | CUDA 支持 |
| `USE_OLLAMA` | `false` | 同容器内嵌 Ollama |
| `USE_SLIM` | `false` | 跳过预下载 AI 模型 |
| `USE_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding 模型 |
| `USE_PERMISSION_HARDENING` | `false` | OpenShift 兼容 |

---

## 五、数据流

```
用户输入
  │
  ▼
SvelteKit 路由 → /c/[id]
  │
  ▼
lib/apis/chats → fetch POST /api/chat/completions
  │
  ▼
FastAPI main.py:chat_completion()
  ├── 验证用户 (JWT/OAuth)
  ├── 检查模型权限 (access_grants / user.role)
  ├── 参数合并 (用户参数 → 模型默认参数 → 请求参数)
  ├── 新建/更新聊天记录 (SQLAlchemy)
  ├── 发布事件 (message.created / chat.created)
  │
  ├── utils/chat.py:generate_chat_completion()
  │   ├── 模型路由:
  │   │   ├── Ollama → HTTP POST /api/generate (流式)
  │   │   ├── OpenAI → HTTP POST /v1/chat/completions
  │   │   ├── Anthropic → Anthropic SDK
  │   │   ├── Google → Google GenAI SDK
  │   │   ├── Pipeline → 自定义 pipeline 处理
  │   │   └── Arena → 同时调用多模型对比
  │   │
  │   ├── 工具调用:
  │   │   ├── 内置工具 (knowledge_fs, code_interpreter)
  │   │   ├── MCP 工具服务器 (utils/mcp/client.py)
  │   │   ├── OpenAPI 工具服务器
  │   │   └── 用户自定义工具
  │   │
  │   ├── 过滤管道:
  │   │   ├── 输入过滤 (用户函数)
  │   │   ├── RAG 检索注入 (向量库 + Web 搜索)
  │   │   └── 输出过滤 (用户函数)
  │   │
  │   └── 后台任务:
  │       ├── 标题自动生成 (TASKS.TITLE_GENERATION)
  │       ├── 标签自动生成
  │       ├── 记忆提取
  │       └── 上下文压缩 (compact_chat_branch)
  │
  ├── 实时推送 (Socket.IO)
  └── 发布事件 (chat.completed / message.completed)

返回 StreamingResponse (SSE) → 前端逐块渲染
  ├── Markdown → 自定义 marked 扩展 → Svelte 组件
  ├── 代码块 → Shiki 高亮 + 复制按钮
  ├── 结构化输出 → structuredOutputRenderer
  ├── 引用/来源 → Citations 组件
  └── 工具调用结果 → ToolCallDisplay 组件
```

---

## 六、核心依赖

### 后端 Python

| 类别 | 依赖 |
|---|---|
| Web 框架 | FastAPI 0.136, Uvicorn, Starlette, Pydantic 2 |
| 数据库 | SQLAlchemy 2.0 (async), Alembic, aiosqlite, psycopg |
| AI SDK | openai, anthropic, google-genai, langchain, sentence-transformers |
| 向量库 | chromadb (默认), qdrant-client, pymilvus, pinecone, weaviate-client, elasticsearch |
| 搜索 | duckduckgo, ddgs, tavily, firecrawl, jina, bing, brave, serpapi 等 |
| 文档解析 | pypdf, python-pptx, docx2txt, pandoc, markdown, beautifulsoup4 |
| 认证 | PyJWT, bcrypt, argon2, authlib, itsdangerous |
| 通信 | python-socketio, redis, mcp |
| 基础设施 | uv, hatchling, APScheduler, loguru, tiktoken |

### 前端 TypeScript/Svelte

| 类别 | 依赖 |
|---|---|
| 框架 | Svelte 5, SvelteKit 2, Vite 5 |
| 样式 | Tailwind CSS 4, PostCSS |
| 编辑器 | TipTap (ProseMirror), Codemirror 6 |
| 渲染 | marked, KaTeX, Mermaid, Shiki/highlight.js |
| 实时 | socket.io-client |
| 图表 | Chart.js, XYFlow (流程图) |
| 国际化 | i18next |
| 浏览器 Python | Pyodide |
| 终端 | xterm |
| 富文本协作 | Yjs, y-prosemirror |

---

## 七、测试状态

- 仅有 1 个测试 fixture：`test/test_files/image_gen/sd-empty.pt`
- 无正式的测试框架配置或测试脚本
- 无 CI/CD (无 `.github/`)
- Docker Compose 里有 `docker-compose.a1111-test.yaml` 用于图像生成的集成测试
