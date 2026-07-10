from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    """数字员工创建请求体：定义新增数字员工时的字段及约束。"""

    name: str = Field(..., min_length=1, max_length=100, description="员工名称")
    avatar: Optional[str] = Field(None, max_length=500, description="头像URL")
    description: Optional[str] = Field(None, description="员工职责描述")
    role_key: Optional[str] = Field("default", max_length=50, description="角色key，对应prompts.ROLES，默认default")
    default_model_id: Optional[int] = Field(None, description="默认LLM模型ID，None或0表示系统默认")
    status: Optional[int] = Field(1, description="状态：1=启用，0=禁用，默认1")


class EmployeeUpdate(BaseModel):
    """数字员工更新请求体：所有字段均为可选，仅更新传入的非空字段。"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    role_key: Optional[str] = Field(None, max_length=50)
    default_model_id: Optional[int] = None
    status: Optional[int] = None
    owner_id: Optional[int] = None


class EmployeeResponse(BaseModel):
    """数字员工响应体：返回员工详情的标准结构，支持直接从ORM实体转换。"""

    id: int
    name: str
    avatar: Optional[str] = None
    description: Optional[str] = None
    role_key: str
    default_model_id: Optional[int] = None
    owner_id: Optional[int] = None
    status: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeChatRequest(BaseModel):
    """数字员工聊天请求体：支持两种输入方式，二选一。
    - 直接传 content 字符串：视为单轮用户消息
    - 传 messages 列表：完整的多轮对话上下文
    """

    messages: Optional[List[Dict[str, Any]]] = Field(None, description="多轮对话消息列表，格式如[{role,content}]")
    content: Optional[str] = Field(None, description="单轮用户消息文本（与messages二选一）")


class EmployeeTaskRequest(BaseModel):
    """数字员工任务触发请求体：指定任务类型与参数。"""

    task_type: str = Field(..., description="任务类型：pipeline_run/asset_profile/nl2sql_report")
    params: Optional[Dict[str, Any]] = Field(None, description="任务参数字典")


class TaskRunResponse(BaseModel):
    """数字员工任务执行记录响应体：返回任务运行详情，支持直接从ORM实体转换。"""

    id: int
    employee_id: int
    user_id: int
    task_type: str
    params: Optional[Any] = None
    status: str
    result: Optional[Any] = None
    error_msg: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
