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
