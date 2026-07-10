from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class ConversationCreate(BaseModel):
    """创建会话请求体。"""
    conv_type: str = Field(default="single", description="会话类型：single单聊/group群聊/employee数字员工")
    name: Optional[str] = Field(default=None, description="会话名称（群聊或数字员工对话名）")
    members: List[int] = Field(description="参与用户ID列表：single必须正好2人，group至少1人（+创建者）")
    employee_id: Optional[int] = Field(default=None, description="数字员工ID，当conv_type=employee时必填")

    @field_validator("members")
    @classmethod
    def check_members(cls, v, info):
        conv_type = info.data.get("conv_type", "single")
        if conv_type == "single":
            if len(v) != 2:
                raise ValueError("单聊会话 members 必须包含正好 2 个用户ID")
        elif conv_type == "group":
            if len(v) < 1:
                raise ValueError("群聊会话 members 至少需要 1 个用户ID")
        elif conv_type == "employee":
            if len(v) < 1:
                raise ValueError("数字员工对话 members 至少包含当前用户ID")
        return v


class ConversationResponse(BaseModel):
    """会话列表响应项（简要信息）。"""
    id: int
    type: str
    name: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    members_count: int = Field(description="会话成员数量")
    last_message: Optional[str] = Field(default=None, description="最新一条消息的内容预览")


class ConversationDetailResponse(ConversationResponse):
    """会话详情响应（含成员ID列表）。"""
    members: List[int] = Field(description="会话内所有成员的用户ID列表")


class MessageSendRequest(BaseModel):
    """发送消息请求体。"""
    content: str = Field(description="消息内容")
    msg_type: str = Field(default="text", description="消息类型：text/image/file等")


class MessageResponse(BaseModel):
    """消息响应项。"""
    id: int
    conversation_id: int
    sender_id: Optional[int]
    sender_name: Optional[str] = Field(default=None, description="发送者显示名称（用户姓名或'数字员工/系统'）")
    content: str
    msg_type: str
    created_at: datetime
