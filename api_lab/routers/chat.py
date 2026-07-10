from typing import Generator, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from core.llm_config import llm_config
from models.user import User
from prompts.roles import ROLE_NAMES, get_role_system_prompt, list_roles
from schemas.chat import (
    ChatMessageAppendRequest,
    ChatRequest,
    ChatResponse,
    ChatSessionAskRequest,
    ChatSessionCreate,
    ChatSessionResponse,
    NL2SQLAnswerResponse,
    NL2SQLRequest,
    NL2SQLResponse,
)
from services.llm_service import (
    ChatSessionRepository,
    build_messages,
    chat_completion,
    generate_nl2sql,
    generate_nl2sql_with_answer,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    """非流式聊天接口"""
    if request.stream:
        raise HTTPException(status_code=400, detail="流式响应请使用 /chat/stream 接口")

    system_prompt = get_role_system_prompt(request.role)
    user_messages = [{"role": m.role, "content": m.content} for m in request.messages]
    messages = build_messages(system_prompt, user_messages)

    response = chat_completion(
        messages,
        temperature=request.temperature,
    )

    return ChatResponse(content=response.choices[0].message.content or "")


@router.post("/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    """流式聊天接口"""
    system_prompt = get_role_system_prompt(request.role)
    user_messages = [{"role": m.role, "content": m.content} for m in request.messages]
    messages = build_messages(system_prompt, user_messages)

    stream = chat_completion(
        messages,
        temperature=request.temperature,
        stream=True,
    )

    def generate() -> Generator[str, None, None]:
        for chunk in stream:
            if chunk.choices:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/roles")
def get_roles():
    """获取人格角色列表"""
    return {"roles": list_roles()}


@router.post("/nl2sql", response_model=NL2SQLResponse)
def nl2sql(
    request: NL2SQLRequest,
    db: Session = Depends(get_db),
):
    """自然语言转 SQL 接口（仅生成 SQL 和执行结果）"""
    result = generate_nl2sql(
        request.question,
        request.table_schemas,
        asset_ids=request.asset_ids,
        db=db,
    )
    return NL2SQLResponse(
        sql=result.get("sql"),
        explanation=result.get("explanation", ""),
        results=result.get("results"),
    )


@router.post("/nl2sql/answer", response_model=NL2SQLAnswerResponse)
def nl2sql_answer(
    request: NL2SQLRequest,
    db: Session = Depends(get_db),
):
    """
    智能问答接口：
    1. 根据自然语言生成 SQL
    2. 执行 SQL 查询数据库
    3. 大模型基于查询结果组织自然语言答案
    """
    result = generate_nl2sql_with_answer(
        request.question,
        request.table_schemas,
        asset_ids=request.asset_ids,
        db=db,
    )
    return NL2SQLAnswerResponse(
        sql=result.get("sql"),
        explanation=result.get("explanation", ""),
        results=result.get("results"),
        answer=result.get("answer"),
    )


def _session_to_response(session, include_messages: bool = False) -> ChatSessionResponse:
    msgs = session.messages if isinstance(session.messages, list) else []
    return ChatSessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        messages_count=len(msgs),
        messages=(session.messages if (include_messages and isinstance(session.messages, list)) else None),
        created_at=session.created_at,
    )


@router.post("/sessions", response_model=ChatSessionResponse)
def create_chat_session(
    request: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新的 NL2SQL 多轮会话"""
    session = ChatSessionRepository.create(db, user_id=current_user.id, title=request.title)
    return _session_to_response(session)


@router.get("/sessions", response_model=List[ChatSessionResponse])
def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出当前用户的全部会话（按创建时间倒序，最多 50 条）"""
    sessions = ChatSessionRepository.list_by_user(db, user_id=current_user.id, limit=50)
    return [_session_to_response(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个会话详情（仅允许本人访问）"""
    session = ChatSessionRepository.get(db, session_id=session_id, user_id=current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    return _session_to_response(session, include_messages=True)


@router.post("/sessions/{session_id}/messages")
def append_session_message(
    session_id: int,
    request: ChatMessageAppendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    向会话追加一条用户消息并触发 NL2SQL 多轮回答：
    1. append 用户消息
    2. 取最近 20 条消息为上下文，调用 generate_nl2sql_with_answer
    3. append assistant 回答，返回 {answer, sql, rows}
    """
    updated = ChatSessionRepository.append_message(
        db,
        session_id=session_id,
        user_id=current_user.id,
        role=request.role,
        content=request.content,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")

    history = updated.messages if isinstance(updated.messages, list) else []
    context_messages = history[-20:] if len(history) > 20 else history
    llm_messages = [
        {"role": m.get("role", "user"), "content": m.get("content", "")}
        for m in context_messages
        if isinstance(m, dict)
    ]

    if llm_messages and llm_messages[-1].get("role") == "user":
        question = llm_messages[-1]["content"]
    else:
        question = request.content

    result = generate_nl2sql_with_answer(
        question,
        None,
        asset_ids=None,
        db=db,
    )

    answer_text = result.get("answer") or ""
    ChatSessionRepository.append_message(
        db,
        session_id=session_id,
        user_id=current_user.id,
        role="assistant",
        content=answer_text,
    )

    return {
        "answer": answer_text,
        "sql": result.get("sql"),
        "rows": result.get("results") or [],
    }


@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ChatSessionRepository.get(db, session_id=session_id, user_id=current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    db.delete(session)
    db.commit()
    return {"deleted": True, "id": session_id}


@router.post("/sessions/{session_id}/ask", response_model=NL2SQLAnswerResponse)
def ask_session(
    session_id: int,
    request: ChatSessionAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ChatSessionRepository.get(db, session_id=session_id, user_id=current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    ChatSessionRepository.append_message(
        db, session_id=session_id, user_id=current_user.id,
        role="user", content=request.content,
    )
    import json
    result = generate_nl2sql_with_answer(
        request.content,
        request.table_schemas,
        asset_ids=request.asset_ids,
        db=db,
    )
    sql = result.get("sql")
    explanation = result.get("explanation", "")
    results = result.get("results")
    answer = result.get("answer")
    assistant_payload = {
        "answer": answer,
        "sql": sql,
        "explanation": explanation,
        "results": results,
    }
    ChatSessionRepository.append_message(
        db, session_id=session_id, user_id=current_user.id,
        role="assistant", content=json.dumps(assistant_payload, ensure_ascii=False),
    )
    return NL2SQLAnswerResponse(
        answer=answer, sql=sql, explanation=explanation, results=results,
    )
