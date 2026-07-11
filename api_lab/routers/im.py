import re
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from core.database import get_db
from core.config import SECRET_KEY, ALGORITHM
from core.security import get_current_user
from models.user import User
from models.im import IMMessage
from schemas.im import (
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    MessageSendRequest,
    MessageResponse,
)
from services.im import (
    ConversationRepository,
    MessageRepository,
    parse_employee_id_from_name,
    build_sender_name_map,
    conv_last_message,
)

router = APIRouter(prefix="/im", tags=["即时通讯"])


def _to_conversation_response(db: Session, conv, include_members: bool = False):
    """将 ORM 会话对象转为 Pydantic 响应（含 members_count / last_message）。"""
    member_ids = ConversationRepository.get_members(db, conv.id)
    data = {
        "id": conv.id,
        "type": conv.type,
        "name": conv.name,
        "created_by": conv.created_by,
        "created_at": conv.created_at,
        "members_count": len(member_ids),
        "last_message": conv_last_message(db, conv.id),
    }
    if include_members:
        data["members"] = member_ids
        return ConversationDetailResponse(**data)
    return ConversationResponse(**data)


def _to_message_response(msg: IMMessage, sender_name_map: Dict[int, str]) -> MessageResponse:
    """将 ORM 消息对象转为 Pydantic 响应（含合成的 sender_name）。"""
    sid = msg.sender_id if msg.sender_id is not None else 0
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        sender_id=msg.sender_id,
        sender_name=sender_name_map.get(sid, "数字员工" if sid == 0 else f"用户{sid}"),
        content=msg.content,
        msg_type=msg.msg_type,
        created_at=msg.created_at,
    )


def _reply_employee(
    db: Session,
    conv_id: int,
    emp_id: int,
    user_message: str,
    sender_user_id: int,
) -> Optional[IMMessage]:
    """
    数字员工接入点：
    - 尝试调用 services.digital_employee.chat_with_employee
    - 失败则发送一条 "模块未启用" 的系统消息作为兜底
    """
    history = MessageRepository.query_history(db, conv_id, limit=20)
    assistant_text = None
    try:
        from services import digital_employee  # type: ignore

        if hasattr(digital_employee, "chat_with_employee"):
            assistant_text = digital_employee.chat_with_employee(
                db, emp_id, history
            )
    except ImportError:
        assistant_text = None
    except Exception:
        assistant_text = None

    if not assistant_text:
        assistant_text = "[数字员工模块未启用]"

    reply_msg = MessageRepository.send(
        db,
        conv_id=conv_id,
        sender_id=0,
        content=assistant_text,
        msg_type="text",
    )
    return reply_msg


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建会话（单聊/群聊/数字员工对话）。"""
    conv_type = payload.conv_type or "single"

    if conv_type == "employee":
        if payload.employee_id is None:
            raise HTTPException(status_code=400, detail="employee 类型必须提供 employee_id")
        conv = ConversationRepository.get_or_create_employee_conv(
            db,
            user_id=current_user.id,
            employee_id=payload.employee_id,
        )
        return _to_conversation_response(db, conv)

    member_ids = list(payload.members or [])
    if conv_type == "group":
        if current_user.id not in member_ids:
            member_ids.insert(0, current_user.id)

    conv = ConversationRepository.create(
        db,
        conv_type=conv_type,
        created_by=current_user.id,
        name=payload.name,
        member_ids=member_ids,
    )
    return _to_conversation_response(db, conv)


@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户的会话列表。"""
    convs = ConversationRepository.list_by_user(db, current_user.id)
    return [_to_conversation_response(db, c) for c in convs]


@router.get("/conversations/{conv_id}", response_model=ConversationDetailResponse)
def get_conversation_detail(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话详情（含成员ID列表），会校验成员权限。"""
    conv = ConversationRepository.get(db, conv_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在或无权限")
    return _to_conversation_response(db, conv, include_members=True)


@router.get("/conversations/{conv_id}/messages", response_model=List[MessageResponse])
def list_messages(
    conv_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    before_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话的历史消息（正序时间线）。"""
    conv = ConversationRepository.get(db, conv_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在或无权限")
    msgs = MessageRepository.query_history(db, conv_id, limit=limit, before_id=before_id)
    name_map = build_sender_name_map(db, msgs)
    return [_to_message_response(m, name_map) for m in msgs]


@router.post("/conversations/{conv_id}/messages")
def send_message(
    conv_id: int,
    payload: MessageSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    发送消息：
    - 若会话为 employee 类型，会触发数字员工自动回复（异步/同步均直接返回 reply）
    - 返回 {"user": 用户消息, "reply": AI回复或null}
    """
    conv = ConversationRepository.get(db, conv_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在或无权限")

    if not payload.content or not payload.content.strip():
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    user_msg = MessageRepository.send(
        db,
        conv_id=conv_id,
        sender_id=current_user.id,
        content=payload.content.strip(),
        msg_type=payload.msg_type or "text",
    )

    reply_msg: Optional[IMMessage] = None
    if conv.type == "employee":
        emp_id = parse_employee_id_from_name(conv.name)
        if emp_id is not None:
            reply_msg = _reply_employee(
                db,
                conv_id=conv_id,
                emp_id=emp_id,
                user_message=user_msg.content,
                sender_user_id=current_user.id,
            )

    name_map = build_sender_name_map(db, [m for m in [user_msg, reply_msg] if m])
    user_resp = _to_message_response(user_msg, name_map)
    reply_resp = _to_message_response(reply_msg, name_map) if reply_msg else None

    return {"user": user_resp, "reply": reply_resp}


# ========== WebSocket 部分 ==========


class ConnectionManager:
    """WebSocket 连接管理器：按 user_id 维护在线连接，支持私聊与会话广播。"""

    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int) -> None:
        if user_id in self.active_connections:
            self.active_connections.pop(user_id, None)

    async def send_personal(self, user_id: int, message_json: Dict[str, Any]) -> None:
        ws = self.active_connections.get(user_id)
        if ws is not None:
            try:
                await ws.send_json(message_json)
            except Exception:
                self.disconnect(user_id)

    async def send_to_conversation(
        self,
        db: Session,
        conv_id: int,
        payload: Dict[str, Any],
        exclude_user_id: Optional[int] = None,
    ) -> None:
        """向会话内除 exclude_user_id 外的所有在线成员广播 payload。"""
        member_ids = ConversationRepository.get_members(db, conv_id)
        for uid in member_ids:
            if exclude_user_id is not None and uid == exclude_user_id:
                continue
            await self.send_personal(uid, payload)


_manager: Optional[ConnectionManager] = None


def _get_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


def setup_im_websocket(app) -> None:
    """
    在 main.py 中调用以注册全局 WebSocket 路由：
    - GET /im/ws?token=<JWT>
    - 消息协议：{"type":"message","conv_id":int,"content":str,"msg_type":"text"}
    """
    manager = _get_manager()

    @app.websocket("/im/ws")
    async def im_ws(
        websocket: WebSocket,
        token: Optional[str] = Query(default=None),
    ):
        user_id: Optional[int] = None
        if token:
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                sub = payload.get("sub")
                if sub is not None:
                    user_id = int(sub)
            except (JWTError, ValueError, TypeError):
                user_id = None

        if user_id is None:
            await websocket.accept()
            try:
                await websocket.send_json({"type": "error", "message": "无效的 token"})
            except Exception:
                pass
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await manager.connect(user_id, websocket)

        from core.database import SessionLocal

        db = SessionLocal()
        try:
            await manager.send_personal(
                user_id,
                {"type": "system", "message": "已连接", "user_id": user_id},
            )
            while True:
                try:
                    data = await websocket.receive_json()
                except WebSocketDisconnect:
                    break

                if not isinstance(data, dict):
                    continue
                msg_type = data.get("type")
                if msg_type != "message":
                    continue

                conv_id = data.get("conv_id")
                content = data.get("content") or ""
                msg_type_val = data.get("msg_type") or "text"

                if not isinstance(conv_id, int) or not content.strip():
                    continue

                conv = ConversationRepository.get(db, conv_id, user_id)
                if not conv:
                    continue

                saved = MessageRepository.send(
                    db,
                    conv_id=conv_id,
                    sender_id=user_id,
                    content=content.strip(),
                    msg_type=msg_type_val,
                )

                name_map = build_sender_name_map(db, [saved])
                response_payload = {
                    "type": "message",
                    "conv_id": conv_id,
                    "message": {
                        "id": saved.id,
                        "conversation_id": saved.conversation_id,
                        "sender_id": saved.sender_id,
                        "sender_name": name_map.get(
                            saved.sender_id or 0,
                            "数字员工" if (saved.sender_id or 0) == 0 else f"用户{saved.sender_id}",
                        ),
                        "content": saved.content,
                        "msg_type": saved.msg_type,
                        "created_at": saved.created_at.isoformat() if saved.created_at else None,
                    },
                }
                await manager.send_to_conversation(
                    db, conv_id, response_payload, exclude_user_id=user_id
                )
                await manager.send_personal(user_id, response_payload)

                if conv.type == "employee":
                    emp_id = parse_employee_id_from_name(conv.name)
                    if emp_id is not None:
                        reply_msg = _reply_employee(
                            db,
                            conv_id=conv_id,
                            emp_id=emp_id,
                            user_message=saved.content,
                            sender_user_id=user_id,
                        )
                        if reply_msg:
                            reply_name_map = build_sender_name_map(db, [reply_msg])
                            reply_payload = {
                                "type": "message",
                                "conv_id": conv_id,
                                "message": {
                                    "id": reply_msg.id,
                                    "conversation_id": reply_msg.conversation_id,
                                    "sender_id": reply_msg.sender_id,
                                    "sender_name": reply_name_map.get(0, "数字员工"),
                                    "content": reply_msg.content,
                                    "msg_type": reply_msg.msg_type,
                                    "created_at": reply_msg.created_at.isoformat() if reply_msg.created_at else None,
                                },
                            }
                            await manager.send_to_conversation(
                                db, conv_id, reply_payload, exclude_user_id=None
                            )
        except Exception:
            pass
        finally:
            try:
                db.close()
            except Exception:
                pass
            manager.disconnect(user_id)
