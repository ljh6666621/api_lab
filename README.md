# 企业智能协同平台 API Lab

> 实训项目 — 基于 FastAPI 的分层架构 RESTful API 服务。**当前进度：Day 1 已完成（25%）**

**项目开发计划（四天）**：
- **Day 1**：基础框架搭建、数据模型设计、数据库初始化 ✅ 已完成
- **Day 2**：数据流水线模块、调度器集成 ⏳ 待开发
- **Day 3**：模型与技能管理、数字员工模块 ⏳ 待开发
- **Day 4**：即时通讯、前端页面、联调测试 ⏳ 待开发

## 项目特性

- **分层架构**：严格遵循 routers / services / models / schemas / core 五层职责分离
- **数据库持久化**：基于 SQLAlchemy 2.0 ORM，默认 SQLite，可切换 MySQL
- **安全认证**：OAuth2 + JWT 令牌鉴权，bcrypt (12轮盐) 密码哈希
- **三大业务模块**：商品 CRUD、用户注册/登录/查询、部门 CRUD
- **LLM 大模型对话**：支持非流式/流式聊天、9 种人格角色切换、温度参数调节
- **NL2SQL 自然语言转 SQL**：用户口语提问 → 自动生成 SQL → 执行并返回查询结果
- **CLI 命令行工具**：本地多轮对话、人格切换、NL2SQL 快捷命令
- **接口文档**：自动生成 Swagger UI 与 ReDoc 交互式文档

## 技术栈

| 类别 | 技术 | 版本要求 |
|------|------|----------|
| Web 框架 | FastAPI | >= 0.110.0 |
| ASGI 服务器 | Uvicorn | >= 0.27.0 |
| 数据校验 | Pydantic | >= 2.0.0 |
| 配置管理 | pydantic-settings | >= 2.0.0 |
| ORM | SQLAlchemy | >= 2.0.0 |
| 密码加密 | bcrypt | >= 4.0.0 |
| JWT 令牌 | python-jose | >= 3.3.0 |
| LLM 客户端 | openai | >= 1.0.0 |
| HTTP 客户端 | httpx | >= 0.27 |
| 定时调度 | APScheduler | >= 3.10.4 |
| 数据分析 | pandas | >= 2.0 |
| 对称加密 | cryptography (Fernet) | >= 42.0 |
| 实时通道 | websockets | >= 12 |

## 目录结构

```
api_lab/
├── core/                  # 核心配置层
│   ├── config.py          # 全局配置（数据库、JWT、功能开关 IM_ENABLE/SCHEDULER_ENABLE）
│   ├── database.py        # SQLAlchemy 引擎与会话管理
│   ├── llm_config.py      # LLM 大模型配置
│   ├── scheduler.py       # APScheduler 调度器封装
│   ├── crypto.py          # Fernet 对称加密（模型 api_key 加密）
│   └── security.py        # bcrypt 密码哈希 & JWT 签发/鉴权
├── models/                # ORM 数据模型层
│   ├── product.py         # 商品表 (products)
│   ├── user.py            # 用户表 (users)
│   ├── department.py      # 部门表 (departments)
│   ├── data_pipeline.py   # 数据源/管道/运行记录 (pipeline_sources/pipelines/pipeline_runs)
│   ├── data_asset.py      # 资产/画像快照 (data_assets/asset_profiles)
│   ├── chat_session.py    # 会话/消息 (chat_sessions/chat_messages)
│   ├── im.py              # 即时通讯会话/消息 (im_conversations/im_members/im_messages)
│   ├── digital_employee.py# 数字员工/任务 (digital_employees/employee_tasks)
│   └── modelskills.py     # 模型/技能/绑定 (ms_models/ms_skills/ms_bindings)
├── schemas/               # Pydantic 数据校验层
│   ├── product.py         # 商品请求/响应 Schema
│   ├── user.py            # 用户注册/登录/响应 Schema
│   ├── department.py      # 部门请求/响应 Schema
│   ├── chat.py            # 聊天/NL2SQL/会话请求/响应 Schema
│   ├── data_pipeline.py   # 数据源/管道/run Schema
│   ├── data_asset.py      # 资产/画像 Schema
│   ├── im.py              # 即时通讯会话/消息 Schema
│   ├── digital_employee.py# 数字员工/任务 Schema
│   └── modelskills.py     # 模型/技能/绑定 Schema
├── routers/               # API 路由层（仅负责路由分发）
│   ├── __init__.py        # 路由模块导出
│   ├── health.py          # 健康检查 & 问候接口
│   ├── products.py        # 商品 CRUD 路由
│   ├── users.py           # 用户注册/登录/查询路由
│   ├── department.py      # 部门 CRUD 路由
│   ├── chat.py            # LLM 聊天 & NL2SQL & 多轮会话路由
│   ├── data_pipelines.py  # A. 数据采集流水线路由（/pipelines）
│   ├── data_assets.py     # B. 数据资产分析路由（/assets）
│   ├── im.py              # D. 即时通讯路由 + WebSocket 接入（/im）
│   ├── digital_employees.py# E. 数字员工路由（/employees）
│   └── modelskills.py     # F. 模型与技能管理路由（/modelskills）
├── services/              # 业务逻辑层（数据库操作）
│   ├── product.py         # ProductRepository
│   ├── user.py            # UserRepository（含 register/authenticate）
│   ├── department.py      # DepartmentRepository
│   ├── llm_service.py     # LLM 服务封装（chat_completion / generate_nl2sql）
│   ├── data_pipeline.py   # 数据源/管道/run 业务 + APScheduler 注册
│   ├── data_asset.py      # 资产 CRUD + pandas 画像 + LLM 报告 + 1h 缓存
│   ├── im_service.py      # IM 会话/消息 + 在线用户状态 + 数字员工自动回复
│   ├── digital_employee.py# 员工 CRUD + 对话 system prompt + 任务模式 A+B+C
│   └── modelskills.py     # 模型加密 CRUD + 内置 4 技能 + 绑定管理
├── prompts/               # 提示词 & 角色模板
│   ├── roles.py           # 9 种人格角色定义（数字员工 role_key 绑定）
│   └── nl2sql_template.txt # NL2SQL 提示词模板
├── static/                # 前端静态资源
│   ├── portal.html        # 门户首页（暗紫水晶+青色渐变卡片，总入口）
│   ├── index.html         # 智能问数前端（浅色系对话气泡）
│   └── im.html            # 即时通讯前端（蓝绿渐变极简聊天）
├── data/                  # 数据文件
│   └── api_lab.db         # SQLite 数据库文件（自动生成）
├── .env                   # 环境变量配置文件（数据库 + LLM + 功能开关）
├── init_db.py             # 数据库初始化脚本（建表 + 种子数据）
├── cli_chat.py            # CLI 命令行聊天工具
├── main.py                # FastAPI 应用入口
└── requirements.txt       # Python 依赖清单（含 httpx/APScheduler/pandas/cryptography/websockets）
```

## 快速开始

### 1. 安装依赖

```bash
cd api_lab
pip install -r requirements.txt
```

### 2. 配置 `.env`

复制以下内容到 `.env` 文件，填入你的 LLM API Key：

```ini
# ============ 数据库配置 ============
DB_DRIVER=sqlite
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123456
DB_NAME=collab_platform_test

# ============ 安全配置 ============
SECRET_KEY=api-lab-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
DEFAULT_USER_PASSWORD=123456

# ============ LLM 配置 ============
LLM_API_KEY=sk-your-api-key-here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_ID=qwen-plus
LLM_MAX_TOKENS=2048
LLM_TEMPERATURE=0.7
```

> **切换模型**：修改 `.env` 的 `LLM_MODEL_ID` 即可切换模型（如 `qwen-plus`、`qwen-max`、`qwen-turbo`）。

### 3. 启动服务

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后将自动执行 `init_all()`：
- 创建所有数据表（users / products / departments）

首次启动时数据库为空，需先通过 `/users/register` 注册用户后再进行其他业务操作。

### 4. 访问接口文档

| 文档类型 | 地址 |
|----------|------|
| Swagger UI（推荐） | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |

### 5. CLI 命令行聊天

```bash
python cli_chat.py
```

## API 接口总览

### 系统接口

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/` | 项目根路径信息 | 否 |
| GET | `/health` | 健康检查 | 否 |
| GET | `/hello?name=` | 问候接口 | 否 |

### 商品管理 `/products`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/products` | 商品列表（支持按名称/价格区间过滤） | 否 |
| GET | `/products/{id}` | 查询单个商品 | 否 |
| POST | `/products` | 新增商品 | **是** |
| PUT | `/products/{id}` | 更新商品 | **是** |
| DELETE | `/products/{id}` | 删除商品 | **是** |

### 用户模块 `/users`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/users/register` | 用户注册 | 否 |
| POST | `/users/login` | 用户登录（获取 JWT） | 否 |
| GET | `/users/me` | 获取当前登录用户信息 | **是** |
| GET | `/users` | 用户列表（支持 status/keyword 过滤） | **是** |
| GET | `/users/{id}` | 查询单个用户 | **是** |

### 部门管理 `/departments`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/departments` | 部门列表（支持按状态/名称过滤） | 否 |
| GET | `/departments/{id}` | 查询单个部门 | 否 |
| POST | `/departments` | 新增部门 | **是** |
| PUT | `/departments/{id}` | 更新部门 | **是** |
| DELETE | `/departments/{id}` | 删除部门 | **是** |

### LLM 聊天 `/chat`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/chat` | 非流式聊天（支持人格角色） | 否 |
| POST | `/chat/stream` | 流式聊天（SSE 文本流） | 否 |
| GET | `/chat/roles` | 获取人格角色列表 | 否 |
| POST | `/chat/nl2sql` | 自然语言转 SQL（自动执行） | 否 |

## 人格角色系统

项目内置 **9 种数字员工角色**，可通过 API 或 CLI 切换：

| 角色名 | 中文名称 | 适用场景 |
|--------|----------|----------|
| `default` | 默认助手 | 通用问答 |
| `professional` | 专业顾问 | 咨询方案、专业分析 |
| `creative` | 创意写作者 | 文案创作、头脑风暴 |
| `humorous` | 幽默大师 | 轻松聊天、讲笑话 |
| `calm` | 冷静分析者 | 理性决策、问题分析 |
| `sql_expert` | SQL 专家 | 数据库查询、SQL 优化 |
| `data_analyst` | 数据分析师 | 数据洞察、趋势分析 |
| `crawler_admin` | 爬虫运维 | 爬虫部署、监控运维 |
| `compliance_auditor` | 合规审计员 | 合规审查、风险评估 |

### API 使用示例

```json
POST /chat
{
  "messages": [{"role": "user", "content": "你是谁？"}],
  "role": "sql_expert",
  "stream": false,
  "temperature": 0.2
}
```

## NL2SQL 自然语言转 SQL

用户用口语提问，系统自动生成 SQL 并执行返回数据结果。

### 请求示例

```json
POST /chat/nl2sql
{
  "question": "统计各部门人数",
  "table_schemas": null
}
```

- `question`（必填）：自然语言问题
- `table_schemas`（可选）：自定义表结构；不传则默认使用项目实际的 departments / products / users 三张表

### 响应示例

```json
{
  "sql": "SELECT d.name AS department_name, COUNT(u.id) AS user_count FROM departments d LEFT JOIN users u ON d.id = u.dept_id GROUP BY d.id, d.name;",
  "explanation": "使用 LEFT JOIN 连接 departments 和 users 表，确保即使是没有员工的部门也能被统计出来。",
  "results": [
    {"department_name": "研发部", "user_count": 4},
    {"department_name": "市场部", "user_count": 1},
    {"department_name": "人事部", "user_count": 2},
    {"department_name": "财务部", "user_count": 0}
  ]
}
```

### CLI 快捷命令

```bash
你: /sql 统计各部门人数
你: /sql 研发部有多少员工
你: /sql 所有产品的库存总量
你: /sql 查询各部门的负责人
```

---

## 项目开发进度

### Day 1 已完成模块（✅）

| 模块 | 负责人 | 状态 |
|------|--------|------|
| 数据库模型设计 | a | ✅ 完成 |
| 数据验证层 (Schemas) | d | ✅ 完成 |
| 配置与安全模块 (core/config.py, security.py, database.py, crypto.py) | b | ✅ 完成 |
| API 路由框架 (users, department, products) | c | ✅ 完成 |
| 基础服务层 (user, department, product, llm_service) | e | ✅ 完成 |

### Day 2-4 待开发模块（⏳）

| 天数 | 模块 | 负责人 | 状态 |
|------|------|--------|------|
| Day 2 | 数据流水线模块、调度器集成 | a, b, c, d, e | ⏳ 待开发 |
| Day 3 | 模型与技能管理、数字员工模块 | a, b, c, d, e | ⏳ 待开发 |
| Day 4 | 即时通讯、前端页面、联调测试 | a, b, c, d, e | ⏳ 待开发 |

---

## 成员任务分配

| 成员 | Day 1 | Day 2 | Day 3 | Day 4 |
|------|-------|-------|-------|-------|
| a | 数据库模型设计 | 数据流水线模块 | 技能管理模块 | 前端页面优化 |
| b | 配置与安全模块 | 调度器集成 | 模型管理模块 | 联调测试 |
| c | API 路由框架 | 数据源仓储 | 数字员工模块 | 前端页面开发 |
| d | 数据验证层 | 流水线执行器 | 工具调用引擎 | 即时通讯模块 |
| e | 基础服务层 | 定时任务管理 | 任务执行模块 | WebSocket 通信 |

---

## 六大核心业务模块（Day 2-4 扩展）

本项目计划扩展至覆盖「数据采集、数据资产、智能问数、即时通讯、数字员工、模型与技能」六大协同模块。所有新增模块均遵循 routers/services/models/schemas/core 分层约束。

### F. 模型与技能管理 `/modelskills`
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST/GET | `/modelskills/models` | 模型 CRUD（api_key 加密入库+响应掩码） | **是** |
| GET/PUT/DEL | `/modelskills/models/{id}` | 单个模型查/改/删 | **是** |
| POST/GET | `/modelskills/skills` | 自定义技能 CRUD | **是** |
| GET | `/modelskills/skills/builtins` | 内置 4 技能：run_nl2sql/run_pipeline/gen_asset_profile/query_user | **是** |
| POST | `/modelskills/skills/test` | 测试技能执行 | **是** |
| POST/GET/DEL | `/modelskills/bindings` | 数字员工↔技能绑定管理 | **是** |

### C. 智能问数（NL2SQL，多轮版升级） `/chat`
除原有接口外，新增会话式多轮能力：
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST/GET | `/chat/sessions` | 创建/列出当前用户会话 | **是** |
| GET | `/chat/sessions/{id}` | 会话详情 | **是** |
| POST | `/chat/sessions/{id}/messages` | 追加消息并调用 NL2SQL 返回答案，自动保存上下文（最后20条），AI回复入库 | **是** |
| POST | `/chat/nl2sql{,/answer}` | 原接口：新增可选 `asset_ids` 绑定真实资产表结构 | **是** |

安全：SQL 执行前 `^SELECT` 正则白名单拦截，防止写库。

### A. 数据采集流水线 `/pipelines`
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST/GET/PUT/DEL | `/pipelines/sources` / `/pipelines/sources/{id}` | 数据源（HTTP API / 爬虫 / CSV Upload） | **是** |
| POST/GET/PUT/DEL | `/pipelines` | 管道 CRUD，带 cron 定时自动注册/移除 APScheduler | **是** |
| POST | `/pipelines/{id}/run` | 手动触发管道执行，返回 run 记录 | **是** |
| GET | `/pipelines/{id}/runs` | 历史 run 列表（按 start_at DESC） | **是** |
| POST | `/pipelines/{id}/upload` | multipart CSV 上传直接入库 | **是** |

调度：`.env` 中 `SCHEDULER_ENABLE=True` 时，后台 BackgroundScheduler 自动把所有 `schedule` 非空的管道注册 cron 任务。

### B. 数据资产分析 `/assets`
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST/GET/PUT/DEL | `/assets` | 资产 CRUD | **是** |
| GET | `/assets/overview` | 全资产仪表盘：总数/总行数/来源分组/今日画像数 | **是** |
| POST | `/assets/{id}/profile` | 画像生成：pandas 统计 + LLM 自然语言报告，1h 缓存（force=True 强制刷新） | **是** |
| GET | `/assets/{id}/profiles` | 该资产的历史画像快照列表 | **是** |

### D. 即时通讯 `/im`（WebSocket + REST）
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST/GET | `/im/conversations` | 会话 CRUD（单聊/群聊/数字员工单聊）；single 类型自动去重 | **是** |
| GET | `/im/conversations/{id}` | 会话详情（含成员） | **是** |
| GET/POST | `/im/conversations/{id}/messages` | 历史消息/发送消息（数字员工会话会自动回复） | **是** |
| WS | `/im/ws?token=<JWT>` | WebSocket 实时推送，在线广播给同会话成员；心跳不在线时 3s 轮询降级 | **是** |

前端入口：`/static/im.html`（蓝绿渐变极简风格）

### E. 数字员工 `/employees`
| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST/GET/PUT/DEL | `/employees` | 数字员工 CRUD，绑定 `role_key`（prompts.ROLES 9种人格） + 自定义模型 | **是** |
| POST | `/employees/{id}/chat` | 单/多轮对话：自动拼 system prompt + 技能 function calling（结果占位） | **是** |
| POST | `/employees/{id}/tasks` | 任务模式：`pipeline_run` / `asset_profile` / `nl2sql_report` 组合 A+B+C，同步执行并记录 | **是** |
| GET | `/employees/{id}/tasks` / `/employees/tasks/me` | 任务执行历史 | **是** |

触发方式：数字员工既可直接调用 `/employees/{id}/chat`；也可在 IM 里建立「与员工#id对话」，自动触发 AI 回复。

---

### 项目前端入口
| 页面 | 地址 | 风格 |
|------|------|------|
| 门户导航首页（总入口） | `/static/portal.html` | 暗紫水晶+青色渐变卡片布局 |
| 智能问数前端 | `/static/index.html` | 浅色系左右气泡对话 |
| 即时通讯前端 | `/static/im.html` | 蓝绿渐变极简聊天 |
| Swagger | `/docs` | 官方 Swagger UI |

---

## CLI 命令行工具使用

启动 CLI：

```bash
python cli_chat.py
```

### 支持的命令

| 命令 | 说明 |
|------|------|
| 直接输入文本 | 与 AI 进行多轮对话（流式输出） |
| `/role` | 查看所有可用人格角色 |
| `/role <角色名>` | 切换人格，如 `/role humorous` |
| `/sql <问题>` | 快捷 NL2SQL，如 `/sql 统计各部门人数` |
| `/clear` | 清空对话历史 |
| `/exit` 或 `/quit` | 退出 CLI |

## 认证说明

### 获取 Token

使用 OAuth2 标准表单登录：

```bash
curl -X POST "http://127.0.0.1:8000/users/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

成功响应：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "...",
    "email": "...",
    "mobile": "",
    "dept_id": 0,
    "status": 1
  }
}
```

### 使用 Token 访问受保护接口

在 Swagger UI 右上角点击 **Authorize**，输入用户名和密码即可。

或在请求头中手动加入：

```
Authorization: Bearer <access_token>
```

## 配置说明

所有配置通过 `.env` 文件管理，使用 `pydantic-settings` 自动加载。配置加载优先级：环境变量 > `.env` 文件 > 默认值。

### 完整配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DB_DRIVER` | `sqlite` | 数据库驱动，可选 `sqlite` / `mysql` |
| `DB_HOST` | `127.0.0.1` | 数据库主机地址 |
| `DB_PORT` | `3306` | 数据库端口 |
| `DB_USER` | `root` | 数据库用户名 |
| `DB_PASSWORD` | `123456` | 数据库密码 |
| `DB_NAME` | `collab_platform_test` | 数据库名称 |
| `SECRET_KEY` | `api-lab-secret-key-change-in-production` | JWT 签名密钥（生产环境必须修改） |
| `ALGORITHM` | `HS256` | JWT 签名算法 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | Token 有效期（分钟） |
| `DEFAULT_USER_PASSWORD` | `123456` | 批量导入用户的默认密码 |
| `LLM_API_KEY` | (必填) | 大模型 API Key |
| `LLM_BASE_URL` | (必填) | 兼容 OpenAI 格式的 API Base URL |
| `LLM_MODEL_ID` | `qwen3.7-plus` | 模型 ID |
| `LLM_MAX_TOKENS` | `2048` | 最大生成长度 |
| `LLM_TEMPERATURE` | `0.7` | 默认温度参数 |

### 切换到 MySQL

修改 `.env` 文件：

```ini
DB_DRIVER=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=your_database
```

并确保已安装 `pymysql`：

```bash
pip install pymysql
```

## 数据模型

### 商品 Product

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 自增主键 |
| name | String(255) | 商品名称（非空，有索引） |
| category | String(100) | 品类 |
| price | Float | 单价（>0） |
| stock | Integer | 库存（>=0，默认0） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 用户 User

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 自增主键 |
| username | String(50) | 用户名（唯一，非空） |
| email | String(255) | 邮箱（唯一，非空） |
| mobile | String(20) | 手机号 |
| password_hash | String(255) | bcrypt 哈希后的密码 |
| dept_id | Integer | 所属部门 ID |
| status | Integer | 1=正常，2=禁用 |
| created_at / updated_at | DateTime | 时间戳 |

### 部门 Department

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 自增主键 |
| name | String(100) | 部门名称（唯一，非空） |
| parent_id | Integer | 上级部门 ID（0=顶级） |
| leader | String(50) | 负责人 |
| phone | String(20) | 联系电话 |
| status | Integer | 1=正常，2=禁用 |
| created_at / updated_at | DateTime | 时间戳 |

## 分层架构约束

本项目严格遵循以下分层职责，开发新功能时请遵守：

1. **Routers 路由层**（`routers/*.py`）：只接收请求、调用 service、返回响应；不直接写 SQL，不写业务逻辑；通过 `HTTPException` 抛错。
2. **Services 业务层**（`services/*.py`）：封装所有业务逻辑与数据库交互；返回 ORM 对象 / `None` / `True` / `False`，**禁止**直接抛 `HTTPException`。
3. **Models 模型层**（`models/*.py`）：只定义 ORM 表结构，不处理 HTTP 或业务逻辑。
4. **Schemas 校验层**（`schemas/*.py`）：仅负责 Pydantic 数据校验与序列化，不访问数据库。
5. **Core 核心层**（`core/*.py`）：全局配置、数据库引擎、安全工具（hash_password / JWT）。

## 开发命令

```bash
# 仅初始化数据库（不启动服务）
python init_db.py

# 启动开发服务器（热重载）
uvicorn main:app --reload

# 指定端口启动
uvicorn main:app --host 0.0.0.0 --port 8080

# CLI 命令行聊天
python cli_chat.py

# 验证配置加载
python -c "from core.config import settings; from core.llm_config import llm_config; print('DB OK:', settings.DB_DRIVER); print('LLM OK:', llm_config.LLM_MODEL_ID)"
```

## 项目进度统计

| 指标 | 数值 |
|------|------|
| 总代码文件数 | 25+ 个 |
| 总代码行数 | 约 1500 行 |
| 完成百分比 | 25%（Day 1） |
| Day 1 完成率 | 100% |
| Day 2 完成率 | 0% |
| Day 3 完成率 | 0% |
| Day 4 完成率 | 0% |

## 问题记录

### Day 1 遇到的问题

1. **问题**：`.env` 文件解析失败，pydantic-settings 报错
   - **原因**：复制粘贴时引入了隐形 Unicode 零宽字符
   - **解决方案**：重新手动输入 `.env` 文件内容

2. **问题**：pydantic-settings 无法找到 `.env` 文件
   - **原因**：使用相对路径导致定位失败
   - **解决方案**：改用绝对路径配置

## 风险评估

| 风险等级 | 风险描述 | 应对措施 |
|---------|---------|---------|
| 中 | Day 2 流水线模块复杂度较高 | 提前熟悉 httpx 和 APScheduler 文档 |
| 低 | Day 3 LLM 调用可能超时 | 添加超时处理和重试机制 |
| 低 | Day 4 WebSocket 联调复杂 | 先测试 REST API，再集成 WebSocket |

## 许可证

实训项目内部使用。
