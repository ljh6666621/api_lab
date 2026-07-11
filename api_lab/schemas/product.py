from typing import Optional

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """商品创建请求体：定义新增商品时必须传入的字段及约束。"""
    name: str = Field(..., min_length=1, description="商品名称")
    category: str = Field(..., description="品类")
    price: float = Field(..., gt=0, description="单价")
    stock: int = Field(default=0, ge=0, description="库存")


class ProductUpdate(BaseModel):
    """商品更新请求体：所有字段均为可选，仅更新传入的非空字段。"""
    name: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)


class ProductResponse(BaseModel):
    """商品响应体：返回商品详情的标准结构，支持直接从 ORM 实体转换。"""
    id: int
    name: str
    category: str
    price: float
    stock: int

    model_config = {"from_attributes": True}


class DeleteResponse(BaseModel):
    """通用删除操作响应体：告知前端删除是否成功并附带提示消息。"""
    success: bool
    message: str
