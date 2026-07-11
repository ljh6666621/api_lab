from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class DataAssetCreate(BaseModel):
    """数据资产创建请求体：定义新增数据资产时的字段及约束。"""

    name: str = Field(..., min_length=1, max_length=200, description="资产名称")
    source_type: Optional[str] = Field("manual", description="来源类型：pipeline/table/manual，默认 manual")
    source_table: Optional[str] = Field(None, max_length=200, description="来源表名")
    pipeline_id: Optional[int] = Field(None, description="关联流水线 ID")
    description: Optional[str] = Field(None, description="资产描述")
    owner_id: Optional[int] = Field(None, description="负责人用户 ID")
    columns_info: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="字段信息 JSON")
    tags: Optional[str] = Field(None, max_length=500, description="标签，逗号分隔")


class DataAssetUpdate(BaseModel):
    """数据资产更新请求体：所有字段均为可选，仅更新传入的非空字段。"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    source_type: Optional[str] = None
    source_table: Optional[str] = Field(None, max_length=200)
    pipeline_id: Optional[int] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    columns_info: Optional[Union[Dict[str, Any], List[Any]]] = None
    row_count: Optional[int] = None
    last_sync_at: Optional[datetime] = None
    tags: Optional[str] = Field(None, max_length=500)


class DataAssetResponse(BaseModel):
    """数据资产响应体：返回资产详情的标准结构，支持直接从 ORM 实体转换。"""

    id: int
    name: str
    source_type: str
    source_table: Optional[str] = None
    pipeline_id: Optional[int] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    columns_info: Optional[Any] = None
    row_count: int = 0
    last_sync_at: Optional[datetime] = None
    tags: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetProfileResponse(BaseModel):
    """资产画像响应体：返回画像详情的标准结构，支持直接从 ORM 实体转换。"""

    id: int
    asset_id: int
    generated_at: datetime
    summary: Optional[Any] = None
    report_text: Optional[str] = None
    generated_by: Optional[int] = None

    model_config = {"from_attributes": True}


class ManualProfileRequest(BaseModel):
    """手动触发生成画像的请求体。"""

    force: bool = Field(False, description="是否强制重新生成（忽略 1 小时缓存）")


class OverviewResponse(BaseModel):
    """数据资产概览统计响应体。"""

    total_assets: int = Field(0, description="资产总数")
    total_rows: int = Field(0, description="所有资产总行数")
    by_source_type: Dict[str, int] = Field(default_factory=dict, description="按来源类型分组的资产数量")
    today_profiles: int = Field(0, description="今日生成的画像数量")
