from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, UniqueConstraint, JSON, func
from sqlalchemy.orm import relationship

from core.database import Base


class IMConversation(Base):
    """即时通讯会话表：支持单聊(single)、群聊(group)、数字员工对话(employee)三种类型。"""
    __tablename__ = "im_conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    type = Column(String(20), nullable=False, default="single", comment="会话类型：single单聊/group群聊/employee数字员工")
    name = Column(String(200), nullable=True, comment="会话名称（群聊名或数字员工对话名）")
    created_by = Column(Integer, nullable=True, comment="创建者用户ID")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    members = relationship("IMConversationMember", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("IMMessage", back_populates="conversation", cascade="all, delete-orphan")


class IMConversationMember(Base):
    """会话成员表：记录每个会话包含哪些用户成员。"""
    __tablename__ = "im_conversation_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("im_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID（数字员工以employee_id作为伪用户ID存入）")
    joined_at = Column(DateTime, default=func.now(), comment="加入时间")

    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conv_user"),
    )

    conversation = relationship("IMConversation", back_populates="members")


class IMMessage(Base):
    """即时通讯消息表：存储会话内的所有聊天消息。"""
    __tablename__ = "im_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("im_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, nullable=True, default=0, comment="发送者用户ID，0表示系统/数字员工")
    content = Column(Text, nullable=False, comment="消息内容文本")
    msg_type = Column(String(20), nullable=False, default="text", comment="消息类型：text文本/image图片/file文件等")
    created_at = Column(DateTime, default=func.now(), index=True, comment="发送时间")
    read_at = Column(JSON, nullable=True, comment="已读状态字典：{用户ID: ISO时间戳字符串}")

    conversation = relationship("IMConversation", back_populates="messages")
