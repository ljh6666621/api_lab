# LLM Chat API Lab

> 基于 FastAPI 的 LLM 聊天服务，支持 CLI、流式响应和人格切换。

## 项目特性

- **CLI 聊天工具**：命令行交互式聊天，支持流式输出
- **FastAPI API**：提供 `/chat`、`/chat/stream`、`/chat/roles` 接口
- **流式响应**：实时输出 LLM 回复，无需等待完整响应
- **人格切换**：5 种预设角色（默认助手、专业顾问、创意写作者、幽默大师、冷静分析者）
- **温度参数**：支持自定义 temperature，控制回答的稳定性与多样性

## 技术栈

| 类别 | 技术 | 版本要求 |
|------|------|----------|
| Web 框架 | FastAPI | >= 0.110.0 |
| ASGI 服务器 | Uvicorn | >= 0.27.0 |
| 配置管理 | pydantic-settings | >= 2.0.0 |
| LLM SDK | openai | >= 1.0.0 |

## 目录结构

```
llm_chat/
├── app/
│   ├── core/
│   │   └── config.py          # 配置管理（pydantic-settings + .env）
│   ├── prompts/
│   │   └── roles.py           # 人格角色系统
│   ├── routers/
│   │   └── chat.py            # 聊天 API 路由
│   ├── schemas/
│   │   └── chat.py            # 请求/响应数据模型
│   └── main.py                # FastAPI 应用入口
├── prompts/
│   └── nl2sql_template.txt    # NL2SQL 模板（预留）
├── .env                       # 环境变量配置
├── cli_chat.py                # CLI 命令行聊天工具
├── requirements.txt           # 依赖清单
└── README.md                  # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

修改 `.env` 文件：

```ini
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_ID=qwen-plus
```

### 3. CLI 聊天

```bash
python cli_chat.py
```

CLI 命令：
- 直接输入消息进行聊天
- `/role` — 查看可用人格角色
- `/role <角色名>` — 切换人格
- `/clear` — 清空对话历史
- `/exit` 或 `/quit` — 退出

### 4. 启动 API 服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 Swagger 文档。

## API 接口

### 聊天接口（非流式）

```bash
POST /chat
```

请求体：
```json
{
  "messages": [
    {"role": "user", "content": "讲一个笑话"}
  ],
  "role": "humorous",
  "stream": false,
  "temperature": 0.7
}
```

响应：
```json
{
  "content": "笑话内容..."
}
```

### 流式聊天接口

```bash
POST /chat/stream
```

响应类型：`text/plain`，流式输出

### 获取角色列表

```bash
GET /chat/roles
```

响应：
```json
{
  "roles": [
    {"name": "default", "description": "默认助手"},
    {"name": "professional", "description": "专业顾问"},
    {"name": "creative", "description": "创意写作者"},
    {"name": "humorous", "description": "幽默大师"},
    {"name": "calm", "description": "冷静分析者"}
  ]
}
```

## 人格角色

| 角色名 | 描述 | System Prompt |
|--------|------|---------------|
| `default` | 默认助手 | 友好的 AI 助手 |
| `professional` | 专业顾问 | 逻辑清晰、严谨专业 |
| `creative` | 创意写作者 | 生动语言、丰富想象 |
| `humorous` | 幽默大师 | 轻松搞笑、充满乐趣 |
| `calm` | 冷静分析者 | 客观中立、理性分析 |

## 切换模型

修改 `.env` 文件中的 `LLM_MODEL_ID`：

```ini
LLM_MODEL_ID=qwen-turbo      # 高速低延迟
LLM_MODEL_ID=qwen-plus       # 效果均衡（推荐）
LLM_MODEL_ID=qwen-max        # 最强效果
```

支持的模型：qwen-turbo、qwen-plus、qwen-max、qwen3.5-plus、qwen3.5-flash 等。

## 温度对比实验

相同问题在不同温度下的表现：

### 场景 A：结构化任务（期望温度 0.2 稳定）

问题：「统计各区域销售额」

| 维度 | temperature=0.2 | temperature=1.0 |
|------|-----------------|-----------------|
| 格式稳定性 | 3/3 一致 | 3/3 不一致 |
| 数字一致性 | 3/3 数字相同 | 3/3 数字波动 |
| 表达多样性 | 措辞相近 | 措辞多变 |

### 场景 B：生成任务（期望温度 1.0 多样）

问题：「写一段给老板的本周销售小结」

| 维度 | temperature=0.2 | temperature=1.0 |
|------|-----------------|-----------------|
| 格式稳定性 | 3/3 一致 | 3/3 不一致 |
| 数字一致性 | 3/3 数字相同 | 3/3 数字波动 |
| 表达多样性 | 措辞相近 | 措辞多变 |

**提示**：DeepSeek-Chat 与 Qwen3-Max 对 temperature 敏感度不同，建议至少试 2 个模型对比。

## 许可证

实训项目内部使用。