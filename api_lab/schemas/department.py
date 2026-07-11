from typing import Optional
from pydantic import BaseModel, Field


class DepartmentBase(BaseModel):
    """部门通用字段基类：定义部门名称、上级、负责人等基础属性。"""
    name: str = Field(..., min_length=1, max_length=100, description="部门名称")
    parent_id: Optional[int] = Field(0, description="上级部门ID")
    leader: Optional[str] = Field("", max_length=50, description="负责人")
    phone: Optional[str] = Field("", max_length=20, description="联系电话")
    status: Optional[int] = Field(1, description="1正常 2禁用")


class DepartmentCreate(DepartmentBase):
    """部门创建请求体：直接继承基类所有字段用于新增部门。"""
    pass


class DepartmentUpdate(BaseModel):
    """部门更新请求体：所有字段均为可选，仅更新传入的非空字段。"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parent_id: Optional[int] = None
    leader: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[int] = None


class DepartmentResponse(DepartmentBase):
    """部门响应体：在通用字段基础上增加部门 ID，支持 ORM 实体直接转换。"""
    id: int

    model_config = {"from_attributes": True}
