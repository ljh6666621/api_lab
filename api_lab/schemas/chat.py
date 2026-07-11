from datetime import datetime
from typing import List, Optional, Dict

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色：user 或 assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="消息列表")
    role: Optional[str] = Field("default", description="人格角色名称")
    stream: bool = Field(False, description="是否流式响应")
    temperature: Optional[float] = Field(None, description="温度参数，控制回答多样性")


class ChatResponse(BaseModel):
    content: str = Field(..., description="AI 回复内容")


class NL2SQLRequest(BaseModel):
    question: str = Field(..., description="用户的自然语言问题")
    table_schemas: Optional[str] = Field(
        None,
        description="表结构描述，如 CREATE TABLE 语句；若未提供则使用默认示例表",
    )
    asset_ids: Optional[List[int]] = Field(
        None,
        description="关联的数据资产 ID 列表；若提供则从资产自动拼表结构",
    )


class NL2SQLResponse(BaseModel):
    sql: Optional[str] = Field(None, description="生成的 SQL 语句；若无法生成则为 null")
    explanation: str = Field(..., description="对 SQL 的解释或无法生成的原因")
    results: Optional[List[dict]] = Field(None, description="SQL 执行结果；若未执行或执行失败则为 null")


class NL2SQLAnswerResponse(BaseModel):
    sql: Optional[str] = Field(None, description="生成的 SQL 语句；若无法生成则为 null")
    explanation: str = Field(..., description="对 SQL 的解释或无法生成的原因")
    results: Optional[List[dict]] = Field(None, description="SQL 执行结果；若未执行或执行失败则为 null")
    answer: Optional[str] = Field(None, description="大模型基于查询结果生成的自然语言回答")


class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(None, description="会话标题，可省略由系统自动生成")


class ChatSessionResponse(BaseModel):
    id: int = Field(..., description="会话 ID")
    user_id: int = Field(..., description="所属用户 ID")
    title: Optional[str] = Field(None, description="会话标题")
    messages_count: int = Field(..., description="会话中的消息数量")
    messages: Optional[List[dict]] = Field(None, description="会话消息列表，仅在 GET /sessions/{id} 详情接口返回")
    created_at: datetime = Field(..., description="会话创建时间")

    model_config = ConfigDict(from_attributes=True)


class ChatMessageAppendRequest(BaseModel):
    content: str = Field(..., description="消息内容")
    role: str = Field("user", description="消息角色：默认 user")


class ChatSessionAskRequest(BaseModel):
    content: str = Field(..., description="用户的自然语言问题")
    role: str = Field("user", description="消息角色：默认 user")
    asset_ids: Optional[List[int]] = Field(None, description="绑定的数据资产 ID 列表")
    table_schemas: Optional[str] = Field(None, description="可选的自定义表结构描述字符串")
