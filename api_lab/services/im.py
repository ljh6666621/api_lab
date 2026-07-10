import re
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session

from models.im import IMConversation, IMConversationMember, IMMessage
from models.user import User


class ConversationRepository:
    """会话仓储层：负责会话与成员的CRUD操作。"""

    @staticmethod
    def _exists_single_conv(db: Session, uid_a: int, uid_b: int) -> Optional[IMConversation]:
        """检查两个用户之间是否已存在单聊会话，有则返回之。"""
        subq1 = (
            db.query(IMConversationMember.conversation_id)
            .filter(IMConversationMember.user_id == uid_a)
            .subquery()
        )
        subq2 = (
            db.query(IMConversationMember.conversation_id)
            .filter(IMConversationMember.user_id == uid_b)
            .subquery()
        )
        conv_ids = (
            db.query(IMConversation.id)
            .filter(IMConversation.type == "single")
            .filter(IMConversation.id.in_(subq1))
            .filter(IMConversation.id.in_(subq2))
            .all()
        )
        if not conv_ids:
            return None
        return db.query(IMConversation).filter(IMConversation.id == conv_ids[0][0]).first()

    @staticmethod
    def create(
        db: Session,
        conv_type: str,
        created_by: int,
        name: Optional[str],
        member_ids: List[int],
    ) -> IMConversation:
        """
        创建会话：
        - single: 若已存在同成员的单聊则直接返回既有会话
        - group/employee: 直接新建
        """
        if conv_type == "single" and len(member_ids) == 2:
            existing = ConversationRepository._exists_single_conv(db, member_ids[0], member_ids[1])
            if existing:
                return existing

        conv = IMConversation(
            type=conv_type,
            name=name,
            created_by=created_by,
        )
        db.add(conv)
        db.flush()

        seen = set()
        for uid in member_ids:
            if uid in seen:
                continue
            seen.add(uid)
            db.add(IMConversationMember(conversation_id=conv.id, user_id=uid))

        db.commit()
        db.refresh(conv)
        return conv

    @staticmethod
    def list_by_user(db: Session, user_id: int) -> List[IMConversation]:
        """获取指定用户参与的所有会话，按最近活跃（消息时间或创建时间）倒序。"""
        subq = (
            db.query(
                IMMessage.conversation_id.label("cid"),
                func.max(IMMessage.created_at).label("last_time"),
            )
            .group_by(IMMessage.conversation_id)
            .subquery()
        )
        rows = (
            db.query(IMConversation, subq.c.last_time)
            .join(
                IMConversationMember,
                IMConversationMember.conversation_id == IMConversation.id,
            )
            .outerjoin(subq, subq.c.cid == IMConversation.id)
            .filter(IMConversationMember.user_id == user_id)
            .order_by(desc(subq.c.last_time), desc(IMConversation.created_at))
            .all()
        )
        return [r[0] for r in rows]

    @staticmethod
    def get(db: Session, conv_id: int, user_id: int) -> Optional[IMConversation]:
        """获取单个会话，同时校验当前用户是否为该会话成员（越权返回None）。"""
        conv = db.query(IMConversation).filter(IMConversation.id == conv_id).first()
        if not conv:
            return None
        is_member = (
            db.query(IMConversationMember)
            .filter(
                IMConversationMember.conversation_id == conv_id,
                IMConversationMember.user_id == user_id,
            )
            .first()
        )
        if not is_member:
            return None
        return conv

    @staticmethod
    def get_members(db: Session, conv_id: int) -> List[int]:
        """返回会话内所有成员的用户ID列表。"""
        rows = (
            db.query(IMConversationMember.user_id)
            .filter(IMConversationMember.conversation_id == conv_id)
            .all()
        )
        return [r[0] for r in rows]

    @staticmethod
    def get_or_create_employee_conv(
        db: Session,
        user_id: int,
        employee_id: int,
    ) -> IMConversation:
        """
        获取或创建"与数字员工对话"的专用会话。
        简化策略：
        - conversation.name = f"与员工#{employee_id}对话"
        - 成员列表仅包含 user_id（数字员工不占真实User表位，通过name解析识别）
        - 若当前用户已存在对应 employee_id 的 employee 类型会话，则直接返回
        """
        expected_name = f"与员工#{employee_id}对话"
        subq = (
            db.query(IMConversationMember.conversation_id)
            .filter(IMConversationMember.user_id == user_id)
            .subquery()
        )
        existing = (
            db.query(IMConversation)
            .filter(
                IMConversation.type == "employee",
                IMConversation.name == expected_name,
                IMConversation.id.in_(subq),
            )
            .first()
        )
        if existing:
            return existing
        return ConversationRepository.create(
            db,
            conv_type="employee",
            created_by=user_id,
            name=expected_name,
            member_ids=[user_id],
        )


class MessageRepository:
    """消息仓储层：负责消息发送、历史查询、已读标记。"""

    @staticmethod
    def send(
        db: Session,
        conv_id: int,
        sender_id: Optional[int],
        content: str,
        msg_type: str = "text",
    ) -> IMMessage:
        """写入一条消息，commit+refresh后返回。"""
        msg = IMMessage(
            conversation_id=conv_id,
            sender_id=sender_id if sender_id is not None else 0,
            content=content,
            msg_type=msg_type,
            read_at={},
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def query_history(
        db: Session,
        conv_id: int,
        limit: int = 100,
        before_id: Optional[int] = None,
    ) -> List[IMMessage]:
        """
        查询会话历史消息：
        - 按 created_at desc + id desc 倒序取 N 条
        - 反转成"正序（时间升序）"返回
        """
        q = db.query(IMMessage).filter(IMMessage.conversation_id == conv_id)
        if before_id is not None:
            q = q.filter(IMMessage.id < before_id)
        rows = (
            q.order_by(desc(IMMessage.created_at), desc(IMMessage.id))
            .limit(limit)
            .all()
        )
        rows.reverse()
        return rows

    @staticmethod
    def mark_read(
        db: Session,
        conv_id: int,
        user_id: int,
        msg_id: int,
    ) -> None:
        """将指定消息标记为指定用户已读：read_at[user_id] = 当前UTC ISO字符串。"""
        msg = (
            db.query(IMMessage)
            .filter(
                IMMessage.id == msg_id,
                IMMessage.conversation_id == conv_id,
            )
            .first()
        )
        if not msg:
            return
        state = msg.read_at or {}
        if isinstance(state, dict):
            state[str(user_id)] = datetime.utcnow().isoformat()
        else:
            state = {str(user_id): datetime.utcnow().isoformat()}
        msg.read_at = state
        db.commit()


def parse_employee_id_from_name(name: Optional[str]) -> Optional[int]:
    """从对话名称 f"与员工#{employee_id}对话" 中解析出数字员工ID。"""
    if not name:
        return None
    m = re.search(r"与员工#(\d+)对话", name)
    if not m:
        return None
    try:
        return int(m.group(1))
    except (ValueError, TypeError):
        return None


def build_sender_name_map(db: Session, messages: List[IMMessage]) -> dict:
    """根据消息列表提取涉及的sender_id，批量查User姓名，返回 {sender_id: 显示名} 映射。"""
    sender_ids = set()
    for m in messages:
        if m.sender_id and m.sender_id > 0:
            sender_ids.add(m.sender_id)
    name_map: dict = {0: "数字员工"}
    if sender_ids:
        rows = db.query(User.id, User.username).filter(User.id.in_(sender_ids)).all()
        for uid, uname in rows:
            name_map[uid] = uname or f"用户{uid}"
    return name_map


def conv_last_message(db: Session, conv_id: int) -> Optional[str]:
    """获取会话最近一条消息的内容预览（前80字）。"""
    last = (
        db.query(IMMessage)
        .filter(IMMessage.conversation_id == conv_id)
        .order_by(desc(IMMessage.created_at), desc(IMMessage.id))
        .first()
    )
    if not last:
        return None
    txt = (last.content or "").strip()
    if len(txt) > 80:
        txt = txt[:80] + "..."
    return txt
