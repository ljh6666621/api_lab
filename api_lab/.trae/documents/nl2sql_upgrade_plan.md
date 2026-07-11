# C-智能问数NL2SQL 模块升级实施计划

## 项目概况
- 项目路径：`e:\实训\api_lab`
- 技术栈：FastAPI + SQLAlchemy + Pydantic + SQLite
- 现有模型风格：每个类/函数都有中文注释，使用 `core.database.Base` 作为 ORM 基类

---

## 修改文件清单及具体内容

### 1. 新建 `models/chat_session.py`
**目的**：新增 ChatSession 数据模型，存储用户的聊天会话及历史消息

**具体内容**：
- 导入：`datetime`, `sqlalchemy` 的 `Column, Integer, String, DateTime, JSON`, `core.database.Base`
- 类 `ChatSession(Base)`：
  - `__tablename__ = "chat_sessions"`
  - `id`: Integer, PK, autoincrement
  - `user_id`: Integer, nullable=False, index=True
  - `title`: String(255), nullable=True, default=None
  - `messages`: JSON 列，存储 `list[dict]`，格式为 `[{"role":"user","content":"..."}]`，默认空列表 `[]`
  - `created_at`: DateTime, default=datetime.utcnow
- 整个类添加中文 docstring 注释

---

### 2. 修改 `models/__init__.py`
**目的**：导出 ChatSession 模型

**具体内容**：
- 第3行后增加：`from models.chat_session import ChatSession`
- `__all__` 列表追加 `"ChatSession"`

---

### 3. 修改 `schemas/chat.py`
**目的**：追加新的 Pydantic schema，保持原有 schema 不变

**具体内容**（追加在文件末尾）：
- `ChatSessionCreate(BaseModel)`：
  - `title: Optional[str] = Field(None, description="会话标题，可选")`
- `ChatSessionResponse(BaseModel)`：
  - `id: int = Field(..., description="会话ID")`
  - `user_id: int = Field(..., description="所属用户ID")`
  - `title: Optional[str] = Field(None, description="会话标题")`
  - `messages_count: int = Field(..., description="消息总数")`
  - `created_at: datetime = Field(..., description="创建时间")`
  - Config: `from_attributes = True`
- `ChatMessageAppendRequest(BaseModel)`：
  - `content: str = Field(..., description="消息内容")`
  - `role: str = Field("user", description="消息角色，默认 user")`
- `NL2SQLWithSessionRequest(BaseModel)`：
  - `session_id: Optional[int] = Field(None, description="会话ID，可选；不传则使用临时上下文")`
  - `content: str = Field(..., description="用户提问内容")`
  - `asset_ids: Optional[List[int]] = Field(default=[], description="关联数据资产ID列表")`
- 顶部 import 补充：`from datetime import datetime`

---

### 4. 修改 `services/llm_service.py`
**目的**：增强 NL2SQL 能力 + 新增会话仓储 + 安全检查

**4(a) 修改 `generate_nl2sql` 函数签名**
```python
def generate_nl2sql(
    question: str,
    table_schemas: Optional[str] = None,
    asset_ids: Optional[List[int]] = None,
    db: Optional[Session] = None,
) -> dict
```
- 在开头增加逻辑：如果 `asset_ids` 非空且 `db` 存在：
  - 尝试从 `data_assets` 表查询 `columns_info` 字段（使用 try-except，如果表不存在则降级使用 DEFAULT_TABLE_SCHEMAS）
  - 如果查询到 columns_info，则拼接成 `table_schema_str`（格式为多个 CREATE TABLE 块）
  - 如果传入的 `table_schemas` 为空，则使用该拼接结果覆盖 `table_schemas`
- 其他逻辑保持不变

**4(b) 修改 `generate_nl2sql_with_answer` 函数签名**
```python
def generate_nl2sql_with_answer(
    question: str,
    table_schemas: Optional[str] = None,
    asset_ids: Optional[List[int]] = None,
    db: Optional[Session] = None,
) -> dict
```
- 调用 `generate_nl2sql` 时传入 `asset_ids` 和 `db` 参数

**4(c) SQL 安全白名单检查**
- 在 `generate_nl2sql` 函数内部，`from sqlalchemy import text` 之后、`conn.execute(text(sql))` 之前增加：
```python
import re as _re
if not _re.match(r'^\s*SELECT\s', sql, _re.I):
    raise ValueError('仅允许 SELECT 查询')
```
- 该异常会被已有的 `except Exception as exec_e` 捕获

**4(d) 新增 `ChatSessionRepository` 类**
追加在文件末尾：
```python
class ChatSessionRepository:
    """聊天会话仓储类：封装 ChatSession 数据模型的增删改查操作。"""

    @staticmethod
    def create(db: Session, user_id: int, title: Optional[str] = None) -> ChatSession:
        """
        创建新的聊天会话。
        :param db: 数据库会话
        :param user_id: 所属用户 ID
        :param title: 会话标题（可选）
        :return: 创建后的 ChatSession 实体
        """
        session = ChatSession(user_id=user_id, title=title, messages=[])
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def append_message(
        db: Session,
        session_id: int,
        user_id: int,
        role: str,
        content: str,
    ) -> ChatSession:
        """
        向指定会话追加一条消息，并验证会话归属。
        :param db: 数据库会话
        :param session_id: 目标会话 ID
        :param user_id: 当前用户 ID（用于验证归属）
        :param role: 消息角色（user / assistant）
        :param content: 消息内容
        :return: 更新后的 ChatSession 实体
        :raises HTTPException: 会话不存在或归属不匹配时抛出 404
        """
        chat_session = ChatSessionRepository.get(db, session_id, user_id)
        current_messages = list(chat_session.messages) if chat_session.messages else []
        current_messages.append({"role": role, "content": content})
        chat_session.messages = current_messages
        db.commit()
        db.refresh(chat_session)
        return chat_session

    @staticmethod
    def get(db: Session, session_id: int, user_id: int) -> ChatSession:
        """
        获取指定会话并验证归属。
        :param db: 数据库会话
        :param session_id: 会话 ID
        :param user_id: 当前用户 ID
        :return: ChatSession 实体
        :raises HTTPException: 会话不存在或归属不匹配
        """
        from fastapi import HTTPException, status
        chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not chat_session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
        if chat_session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该会话")
        return chat_session

    @staticmethod
    def list_by_user(db: Session, user_id: int) -> List[ChatSession]:
        """
        获取指定用户的所有会话（按创建时间倒序）。
        :param db: 数据库会话
        :param user_id: 用户 ID
        :return: ChatSession 列表
        """
        from sqlalchemy import desc
        return db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(desc(ChatSession.created_at)).all()
```
- 顶部 import 补充：`from sqlalchemy.orm import Session`（如果没有），`from models.chat_session import ChatSession`

---

### 5. 修改 `routers/chat.py`
**目的**：新增会话路由组，旧接口兼容新增可选 asset_ids 字段

**顶部 import 补充**：
- `from fastapi import Depends, status`
- `from sqlalchemy.orm import Session`
- `from core.database import get_db`
- `from core.security import get_current_user`
- `from models.user import User`
- `from models.chat_session import ChatSession`
- `from services.llm_service import ChatSessionRepository`
- 从 `schemas.chat` 追加导入：`ChatSessionCreate, ChatSessionResponse, ChatMessageAppendRequest, NL2SQLWithSessionRequest`

**5(a) 修改现有两个接口增加可选 asset_ids 字段**

方案：扩展 `NL2SQLRequest` schema（在 schemas/chat.py 中追加一个可选字段），或者在路由函数中接收额外参数。

更优方案：在 `schemas/chat.py` 中修改 `NL2SQLRequest`，追加可选字段：
```python
asset_ids: Optional[List[int]] = Field(default=[], description="关联数据资产ID列表，可选")
```
然后在 `routers/chat.py` 中：
- `nl2sql` 路由：调用 `generate_nl2sql(request.question, request.table_schemas, request.asset_ids, db)`（需要注入 `db: Session = Depends(get_db)`）
- `nl2sql_answer` 路由：调用 `generate_nl2sql_with_answer(request.question, request.table_schemas, request.asset_ids, db)`（同样注入 db）

> 注意：因为 asset_ids 是可选（默认 []），所以旧调用完全兼容，不需要传这个字段。

**5(b) 新增会话路由组**（追加在文件末尾）

注意：现有 `router = APIRouter(prefix="/chat", tags=["chat"])`，所以新路由的路径为：
- `POST /chat/sessions` → 实际路由定义为 `@router.post("/sessions", ...)`
- 依此类推

```python
@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    body: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的聊天会话（需登录）"""
    chat_session = ChatSessionRepository.create(db, current_user.id, body.title)
    return ChatSessionResponse(
        id=chat_session.id,
        user_id=chat_session.user_id,
        title=chat_session.title,
        messages_count=len(chat_session.messages or []),
        created_at=chat_session.created_at,
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的所有会话列表（需登录）"""
    sessions = ChatSessionRepository.list_by_user(db, current_user.id)
    return [
        ChatSessionResponse(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            messages_count=len(s.messages or []),
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{sid}", response_model=ChatSessionResponse)
def get_session(
    sid: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取会话详情（需登录，验证归属）"""
    chat_session = ChatSessionRepository.get(db, sid, current_user.id)
    return ChatSessionResponse(
        id=chat_session.id,
        user_id=chat_session.user_id,
        title=chat_session.title,
        messages_count=len(chat_session.messages or []),
        created_at=chat_session.created_at,
    )


@router.post("/sessions/{sid}/messages")
def append_message_and_query(
    sid: int,
    body: ChatMessageAppendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    向会话追加用户消息，然后调用 NL2SQL 返回答案（需登录）：
    1. 追加用户消息到会话
    2. 取会话最后20条消息作为上下文
    3. 调用 generate_nl2sql_with_answer 生成 SQL、执行并总结答案
    4. 把 AI 回答追加为 assistant 消息
    5. 返回 {answer, sql, rows}
    """
    chat_session = ChatSessionRepository.append_message(
        db, sid, current_user.id, body.role, body.content
    )

    history_messages = chat_session.messages or []
    if len(history_messages) > 20:
        history_messages = history_messages[-20:]

    last_user_content = body.content
    result = generate_nl2sql_with_answer(last_user_content, None, [], db)

    assistant_content = result.get("answer") or result.get("explanation", "")
    ChatSessionRepository.append_message(
        db, sid, current_user.id, "assistant", assistant_content
    )

    return {
        "answer": result.get("answer"),
        "sql": result.get("sql"),
        "rows": result.get("results") or [],
    }
```

---

## 兼容性说明
1. 所有新增字段均为 `Optional`，旧的接口调用方式（不传 asset_ids、不传 session_id）完全兼容
2. 原有的 `NL2SQLRequest`、`NL2SQLResponse`、`NL2SQLAnswerResponse` schema 结构不变，仅追加字段
3. 原有路由函数的签名不变（除了内部注入 db，对外接口无影响）

---

## 风险点说明
1. `data_assets` 表可能不存在 → 已用 try-except 降级到 DEFAULT_TABLE_SCHEMAS
2. SQL 注入风险 → 新增 SELECT 白名单正则检查
3. Token 超限 → 取最近 20 条消息作为上下文
