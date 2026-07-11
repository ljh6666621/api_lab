from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色：system/user/assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="对话历史消息列表")
    role: Optional[str] = Field(None, description="人格角色名称")
    stream: bool = Field(False, description="是否使用流式响应")
    temperature: Optional[float] = Field(None, description="温度参数，0-1")


class ChatResponse(BaseModel):
    content: str = Field(..., description="AI 回复内容")


class StreamResponse(BaseModel):
    chunk: str = Field(..., description="流式输出的内容片段")