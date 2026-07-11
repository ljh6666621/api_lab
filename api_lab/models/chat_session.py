from sqlalchemy import Column, Integer, String, DateTime, JSON, func

from core.database import Base


class ChatSession(Base):
    """聊天会话数据模型：存储多轮对话的会话元数据与消息历史。"""

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    """会话主键 ID，自增整数"""

    user_id = Column(Integer, nullable=False, index=True)
    """所属用户 ID，非空"""

    title = Column(String(200), nullable=True)
    """会话标题，最多 200 字符，可为空"""

    messages = Column(JSON, default=list)
    """消息列表 JSON，默认空数组，每条含 role 与 content"""

    created_at = Column(DateTime(timezone=True), default=func.now())
    """会话创建时间（带时区），默认当前数据库时间"""
