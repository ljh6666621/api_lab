# API Lab 项目 - 成员 e 代码汇总

**负责模块**：基础服务层  
**日期**：2026-07-10  

---

## services/user.py

```python
from typing import Optional

from sqlalchemy.orm import Session

from models.user import User
from core.security import hash_password, verify_password


class UserRepository:
    """用户仓储服务：封装所有与 User 模型相关的数据库操作与业务逻辑。"""

    def list_all(
        self,
        db: Session,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> list[User]:
        """
        查询用户列表，可选按账号状态过滤、按用户名模糊搜索。
        :param db: 数据库会话
        :param status: 可选，1=正常 2=禁用
        :param keyword: 可选，用户名关键字
        :return: 符合条件的用户实体列表
        """
        query = db.query(User)
        if status is not None:
            query = query.filter(User.status == status)
        if keyword:
            query = query.filter(User.username.contains(keyword.lower()))
        return query.all()

    def get(self, db: Session, user_id: int) -> Optional[User]:
        """
        按用户主键 ID 查询单个用户。
        :param db: 数据库会话
        :param user_id: 用户 ID
        :return: 找到返回 User，否则 None
        """
        return db.query(User).filter(User.id == user_id).first()

    def get_by_username_or_email(self, db: Session, identifier: str) -> Optional[User]:
        """
        按用户名 或 邮箱查找用户（登录时使用，支持两种登录名）。
        :param db: 数据库会话
        :param identifier: 用户名或邮箱
        :return: 匹配到的用户或 None
        """
        return db.query(User).filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

    def exists(self, db: Session, username: Optional[str] = None, email: Optional[str] = None) -> bool:
        """
        判断指定用户名/邮箱是否已存在，用于注册前的唯一性校验。
        :param db: 数据库会话
        :param username: 用户名
        :param email: 邮箱
        :return: 任意一项存在即返回 True
        """
        query = db.query(User)
        conditions = []
        if username:
            conditions.append(User.username == username)
        if email:
            conditions.append(User.email == email)
        if not conditions:
            return False
        return query.filter(*conditions).first() is not None

    def register(
        self,
        db: Session,
        *,
        username: str,
        email: str,
        password: str,
        mobile: str = "",
        dept_id: int = 0,
    ) -> Optional[User]:
        """
        注册新用户：先做唯一性校验，通过后哈希密码并写入数据库。
        :param db: 数据库会话
        :param username: 用户名（唯一）
        :param email: 邮箱（唯一）
        :param password: 明文密码，会被 bcrypt 哈希
        :param mobile: 手机号
        :param dept_id: 所属部门 ID
        :return: 创建成功返回新用户，用户名/邮箱冲突返回 None
        """
        if self.exists(db, username=username, email=email):
            return None
        user = User(
            username=username,
            email=email,
            mobile=mobile or "",
            dept_id=dept_id or 0,
            status=1,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate(self, db: Session, identifier: str, password: str) -> Optional[User]:
        """
        用户认证：按用户名/邮箱找到用户后校验密码。
        :param db: 数据库会话
        :param identifier: 用户名或邮箱
        :param password: 明文密码
        :return: 验证通过返回 User 对象，否则 None
        """
        user = self.get_by_username_or_email(db, identifier)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def count(self, db: Session) -> int:
        """统计 users 表总记录数，用于种子数据插入前判断是否为空库。"""
        return db.query(User).count()

    def bulk_create(self, db: Session, users: list[dict], default_password: str) -> int:
        """
        批量创建用户（用于种子数据初始化），跳过已存在用户名/邮箱。
        所有新用户使用同一个默认密码哈希，减少重复计算。
        :param db: 数据库会话
        :param users: 用户字典列表，可包含 id/username/email/mobile/dept_id/status
        :param default_password: 默认明文密码
        :return: 实际创建成功的用户数量
        """
        created = 0
        pwd_hash = hash_password(default_password)
        for u in users:
            if self.exists(db, username=u.get("username"), email=u.get("email")):
                continue
            db.add(User(
                id=u.get("id"),
                username=u.get("username"),
                email=u.get("email") or f"{u.get('username')}@example.com",
                mobile=u.get("mobile") or "",
                dept_id=u.get("dept_id") or 0,
                status=u.get("status") or 1,
                password_hash=pwd_hash,
            ))
            created += 1
        db.commit()
        return created


user_service = UserRepository()
```

---

## services/department.py

```python
from typing import Optional

from sqlalchemy.orm import Session

from models.department import Department


class DepartmentRepository:
    """部门仓储服务：封装部门 CRUD、唯一性校验与条件查询等操作。"""

    def list_all(
        self,
        db: Session,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> list[Department]:
        """
        查询部门列表，支持按状态过滤、按部门名称模糊搜索。
        :param db: 数据库会话
        :param status: 可选，1=正常 2=禁用
        :param keyword: 可选，部门名称关键字
        :return: 符合条件的部门列表
        """
        query = db.query(Department)
        if status is not None:
            query = query.filter(Department.status == status)
        if keyword:
            query = query.filter(Department.name.contains(keyword))
        return query.all()

    def get(self, db: Session, dept_id: int) -> Optional[Department]:
        """
        按部门 ID 查找单个部门。
        :param db: 数据库会话
        :param dept_id: 部门主键
        :return: 找到返回 Department，否则 None
        """
        return db.query(Department).filter(Department.id == dept_id).first()

    def get_by_name(self, db: Session, name: str) -> Optional[Department]:
        """
        按部门名称查找，用于创建/编辑前的唯一性校验。
        :param db: 数据库会话
        :param name: 部门名称
        :return: 已存在返回 Department，否则 None
        """
        return db.query(Department).filter(Department.name == name).first()

    def create(self, db: Session, data: dict) -> Optional[Department]:
        """
        新增部门：若同名部门已存在则返回 None，否则写入数据库。
        :param db: 数据库会话
        :param data: 部门字段字典
        :return: 新建后的部门实体；名称冲突为 None
        """
        if self.get_by_name(db, data.get("name", "")):
            return None
        item = Department(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update(self, db: Session, dept_id: int, data: dict) -> Optional[Department]:
        """
        按 ID 局部更新部门字段；部门不存在返回 None。
        :param db: 数据库会话
        :param dept_id: 目标部门 ID
        :param data: 待更新字段字典
        :return: 更新后的部门实体，或 None
        """
        item = self.get(db, dept_id)
        if not item:
            return None
        for key, value in data.items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return item

    def delete(self, db: Session, dept_id: int) -> bool:
        """
        按 ID 删除部门。
        :param db: 数据库会话
        :param dept_id: 目标部门 ID
        :return: 删除成功返回 True；部门不存在返回 False
        """
        item = self.get(db, dept_id)
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True


dept_service = DepartmentRepository()
```

---

## services/product.py

```python
from typing import Optional

from sqlalchemy.orm import Session

from models.product import Product


class ProductRepository:
    """商品仓储服务：封装商品 CRUD 及按条件查询的数据库操作。"""

    def list_all(
        self,
        db: Session,
        name: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> list[Product]:
        """
        查询商品列表，支持按名称模糊匹配、按价格区间过滤。
        :param db: 数据库会话
        :param name: 商品名称关键字（可选）
        :param min_price: 最低价格（可选，含等于）
        :param max_price: 最高价格（可选，含等于）
        :return: 满足条件的商品列表
        """
        query = db.query(Product)
        if name:
            query = query.filter(Product.name.contains(name))
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        return query.all()

    def get(self, db: Session, product_id: int) -> Optional[Product]:
        """
        按商品 ID 查找单个商品。
        :param db: 数据库会话
        :param product_id: 商品主键
        :return: 找到返回 Product，否则 None
        """
        return db.query(Product).filter(Product.id == product_id).first()

    def create(self, db: Session, data: dict) -> Product:
        """
        创建新商品，写入数据库并刷新获取自增 ID、创建/更新时间。
        :param db: 数据库会话
        :param data: 商品字段字典，对应 ProductCreate schema
        :return: 新建后的商品实体
        """
        item = Product(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update(self, db: Session, product_id: int, data: dict) -> Optional[Product]:
        """
        按 ID 局部更新商品字段；若商品不存在返回 None。
        :param db: 数据库会话
        :param product_id: 目标商品 ID
        :param data: 待更新字段字典（仅包含需要修改的键）
        :return: 更新后的商品实体，或 None
        """
        item = self.get(db, product_id)
        if not item:
            return None
        for key, value in data.items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return item

    def delete(self, db: Session, product_id: int) -> bool:
        """
        按 ID 删除商品。
        :param db: 数据库会话
        :param product_id: 目标商品 ID
        :return: 删除成功返回 True，商品不存在返回 False
        """
        item = self.get(db, product_id)
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True


product_service = ProductRepository()
```

---

## services/llm_service.py

```python
import json
import re
from pathlib import Path
from typing import List, Optional

from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.llm_config import llm_config

DEFAULT_TABLE_SCHEMAS = """CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    parent_id INTEGER,
    leader VARCHAR(50),
    phone VARCHAR(20),
    status INTEGER,
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255),
    category VARCHAR(100),
    price FLOAT,
    stock INTEGER,
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(255),
    mobile VARCHAR(20),
    password_hash VARCHAR(255),
    dept_id INTEGER,
    status INTEGER,
    created_at DATETIME,
    updated_at DATETIME
);"""


def _sql_safety_check(sql: str) -> None:
    """SQL 白名单安全检查：仅允许以 SELECT 开头的只读查询，防止写库操作。

    :param sql: 待执行的 SQL 字符串
    :raises ValueError: 当 SQL 不以 SELECT 开头时抛出
    """
    if not re.match(r"^\s*SELECT\s", sql, re.I):
        raise ValueError("只允许 SELECT 查询，防止写库操作")


def get_client() -> OpenAI:
    return OpenAI(
        api_key=llm_config.LLM_API_KEY,
        base_url=llm_config.LLM_BASE_URL,
    )


def chat_completion(
    messages: List[dict],
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    stream: bool = False,
):
    client = get_client()
    return client.chat.completions.create(
        model=model or llm_config.LLM_MODEL_ID,
        messages=messages,
        max_tokens=max_tokens or llm_config.LLM_MAX_TOKENS,
        temperature=temperature or llm_config.LLM_TEMPERATURE,
        stream=stream,
    )


def build_messages(system_prompt: str, user_messages: List[dict]) -> List[dict]:
    VALID_ROLES = {"user", "assistant", "system", "tool", "function"}
    messages = [{"role": "system", "content": system_prompt}]
    for msg in user_messages:
        role = msg.get("role", "user")
        if role not in VALID_ROLES:
            role = "user"
        messages.append({"role": role, "content": msg.get("content", "")})
    return messages


def load_nl2sql_template() -> str:
    template_path = Path(__file__).resolve().parent.parent / "prompts" / "nl2sql_template.txt"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return """你是一位专业的数据库 SQL 专家。请根据用户的自然语言问题和提供的表结构，生成准确、高效的 SQL 查询语句。

## 表结构信息
{table_schemas}

## 用户问题
{question}

## 要求
1. 严格按照提供的表结构生成 SQL，不要使用不存在的表或字段
2. SQL 语句必须是有效的，可直接在数据库中执行
3. 优先考虑查询性能，合理使用索引字段
4. 只返回 SQL 语句和简要解释，不要包含其他内容
5. 如果无法生成有效 SQL，请说明原因

请以 JSON 格式返回：
{{
  "sql": "生成的 SQL 语句",
  "explanation": "对 SQL 的简要解释"
}}"""


def generate_nl2sql(
    question: str,
    table_schemas: Optional[str] = None,
    *,
    asset_ids: Optional[List[int]] = None,
    db: Optional[Session] = None,
) -> dict:
    table_schema_str = table_schemas

    if db is not None and asset_ids:
        try:
            from models.data_asset import DataAsset

            try:
                assets = db.query(DataAsset).filter(DataAsset.id.in_(asset_ids)).all()
                if assets and (table_schema_str is None or table_schema_str.strip() == ""):
                    lines = []
                    for asset in assets:
                        table_name = getattr(asset, "table_name", None) or getattr(asset, "name", None)
                        columns_info = getattr(asset, "columns_info", None)
                        if table_name and isinstance(columns_info, list) and columns_info:
                            for col in columns_info:
                                if isinstance(col, dict):
                                    cname = col.get("name") or col.get("column_name") or ""
                                    ctype = col.get("type") or col.get("data_type") or ""
                                    if cname:
                                        lines.append(f"{table_name}|{cname}|{ctype}")
                    if lines:
                        table_schema_str = "表名|字段名|类型\n" + "\n".join(lines)
            except Exception:
                pass
        except ImportError:
            pass

    template = load_nl2sql_template()
    if not table_schema_str or table_schema_str.strip() == "string" or table_schema_str.strip() == "":
        schemas = DEFAULT_TABLE_SCHEMAS
    else:
        schemas = table_schema_str
    system_prompt = template.format(table_schemas=schemas, question=question)

    messages = [{"role": "system", "content": system_prompt}]

    try:
        response = chat_completion(messages, temperature=0.2)
        content = response.choices[0].message.content or ""

        try:
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
            if json_match:
                content = json_match.group(1)
            result = json.loads(content)
            sql = result.get("sql")
            explanation = result.get("explanation", "")

            if sql:
                try:
                    _sql_safety_check(sql)
                    from core.database import engine
                    with engine.connect() as conn:
                        cursor_result = conn.execute(text(sql))
                        columns = [col for col in cursor_result.keys()]
                        results = [dict(zip(columns, row)) for row in cursor_result.fetchall()]
                        return {"sql": sql, "explanation": explanation, "results": results}
                except ValueError as safety_e:
                    return {"sql": sql, "explanation": f"{explanation}（安全拦截: {str(safety_e)}）", "results": None}
                except Exception as exec_e:
                    return {"sql": sql, "explanation": f"{explanation}（执行失败: {str(exec_e)}）", "results": None}
            return {"sql": sql, "explanation": explanation, "results": None}
        except json.JSONDecodeError:
            return {"sql": None, "explanation": f"无法解析模型返回的 JSON: {content}", "results": None}
    except Exception as e:
        return {"sql": None, "explanation": f"调用大模型失败: {str(e)}", "results": None}


def summarize_nl2sql_results(question: str, sql: str, results: Optional[List[dict]]) -> Optional[str]:
    if not results:
        return "没有查询到相关数据。"

    results_json = json.dumps(results, ensure_ascii=False, indent=2)
    system_prompt = (
        "你是一位专业的数据分析师。请根据用户的问题、SQL语句和数据库查询结果，"
        "用简洁、自然的中文语言回答用户的问题。如果数据中有数字，请清晰列出；"
        "如果可以做总结或对比，请提供洞察。不要复述 SQL，直接给出结论。"
    )
    user_content = (
        f"用户问题：{question}\n"
        f"SQL语句：{sql}\n"
        f"查询结果：{results_json}\n"
        f"请用自然语言给出详细回答。"
    )

    try:
        response = chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception:
        return None


def generate_nl2sql_with_answer(
    question: str,
    table_schemas: Optional[str] = None,
    *,
    asset_ids: Optional[List[int]] = None,
    db: Optional[Session] = None,
) -> dict:
    nl2sql_result = generate_nl2sql(question, table_schemas, asset_ids=asset_ids, db=db)
    if nl2sql_result.get("results"):
        answer = summarize_nl2sql_results(
            question,
            nl2sql_result.get("sql", ""),
            nl2sql_result.get("results"),
        )
        nl2sql_result["answer"] = answer
    else:
        nl2sql_result["answer"] = None
    return nl2sql_result


class ChatSessionRepository:
    """聊天会话仓储：封装 ChatSession 模型的 CRUD 静态方法。"""

    @staticmethod
    def create(db: Session, user_id: int, title: Optional[str] = None):
        """创建新的聊天会话。

        :param db: 数据库会话
        :param user_id: 所属用户 ID
        :param title: 可选标题
        :return: 新建的 ChatSession 实体
        """
        from models.chat_session import ChatSession

        session = ChatSession(user_id=user_id, title=title, messages=[])
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get(db: Session, session_id: int, user_id: int):
        """按 ID 获取单个会话（必须匹配 user_id，防越权）。

        :param db: 数据库会话
        :param session_id: 会话 ID
        :param user_id: 当前用户 ID
        :return: 匹配的 ChatSession 或 None
        """
        from models.chat_session import ChatSession

        return (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )

    @staticmethod
    def list_by_user(db: Session, user_id: int, limit: int = 50):
        """列出当前用户的会话（按创建时间倒序）。

        :param db: 数据库会话
        :param user_id: 当前用户 ID
        :param limit: 最大返回条数，默认 50
        :return: ChatSession 列表
        """
        from models.chat_session import ChatSession
        from sqlalchemy import desc

        return (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.created_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def append_message(db: Session, session_id: int, user_id: int, role: str, content: str):
        """向指定会话追加一条消息，成功返回刷新后的会话，失败返回 None。

        :param db: 数据库会话
        :param session_id: 会话 ID
        :param user_id: 当前用户 ID（越权校验）
        :param role: 消息角色 user/assistant
        :param content: 消息内容
        :return: 更新后的 ChatSession，或 None（会话不存在/异常）
        """
        session = ChatSessionRepository.get(db, session_id, user_id)
        if session is None:
            return None
        try:
            if not isinstance(session.messages, list):
                session.messages = []
            session.messages.append({"role": role, "content": content})
            db.commit()
            db.refresh(session)
            return session
        except Exception:
            db.rollback()
            return None
```

---

## prompts/roles.py

```python
from typing import Optional

ROLES = {
    "default": {
        "name": "default",
        "description": "默认助手",
        "system_prompt": "你是一个友好的AI助手，擅长回答各种问题。",
    },
    "professional": {
        "name": "professional",
        "description": "专业顾问",
        "system_prompt": "你是一位资深的专业顾问，回答问题时逻辑清晰、严谨专业，提供详细的分析和建议。",
    },
    "creative": {
        "name": "creative",
        "description": "创意写作者",
        "system_prompt": "你是一位富有创意的写作者，擅长用生动的语言和丰富的想象力来表达想法。",
    },
    "humorous": {
        "name": "humorous",
        "description": "幽默大师",
        "system_prompt": "你是一位幽默风趣的聊天伙伴，擅长用轻松搞笑的方式回答问题，让对话充满乐趣。",
    },
    "calm": {
        "name": "calm",
        "description": "冷静分析者",
        "system_prompt": "你是一位冷静理性的分析者，面对任何问题都能保持客观中立，提供冷静的分析和建议。",
    },
    "sql_expert": {
        "name": "sql_expert",
        "description": "SQL 专家",
        "system_prompt": "你是一位专业的数据库 SQL 专家。请根据用户的自然语言问题和提供的表结构，生成准确、高效的 SQL 查询语句。只生成 SQL 语句，并遵循表结构，优先考虑查询性能。",
    },
    "data_analyst": {
        "name": "data_analyst",
        "description": "数据分析师",
        "system_prompt": "你是一位资深的数据分析师，擅长从数据中发现趋势和洞察，提供专业的数据分析报告和建议。",
    },
    "crawler_admin": {
        "name": "crawler_admin",
        "description": "爬虫运维",
        "system_prompt": "你是一位爬虫运维专家，擅长处理网页爬虫的部署、监控和维护工作。",
    },
    "compliance_auditor": {
        "name": "compliance_auditor",
        "description": "合规审计员",
        "system_prompt": "你是一位合规审计员，擅长审查业务流程是否符合法规要求和内部政策，提供合规建议和改进方案。",
    },
}


ROLE_NAMES = {
    "default": "默认助手",
    "professional": "专业顾问",
    "creative": "创意写作者",
    "humorous": "幽默大师",
    "calm": "冷静分析者",
    "sql_expert": "SQL 专家",
    "data_analyst": "数据分析师",
    "crawler_admin": "爬虫运维",
    "compliance_auditor": "合规审计员",
}


def get_role_system_prompt(role_name: Optional[str]) -> str:
    if role_name and role_name in ROLES:
        return ROLES[role_name]["system_prompt"]
    return ROLES["default"]["system_prompt"]


def list_roles() -> list[dict]:
    return [
        {"name": role["name"], "description": role["description"]}
        for role in ROLES.values()
    ]
```

---

**完成文件数**：5 个  
**代码行数**：约 400 行
