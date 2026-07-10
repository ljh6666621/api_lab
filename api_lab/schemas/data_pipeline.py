from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DataSourceCreate(BaseModel):
    """数据源创建请求体：定义新增数据源时必须传入的字段及约束。"""
    name: str = Field(..., min_length=1, max_length=100, description="数据源名称")
    type: Optional[str] = Field("http_api", description="数据源类型：http_api/crawler/upload")
    config: dict = Field(..., description="数据源配置字典，如 {url, headers, method, params, jq_path}")
    status: Optional[int] = Field(1, description="状态：1=启用，0=停用")


class DataSourceUpdate(BaseModel):
    """数据源更新请求体：所有字段均为可选，仅更新传入的非空字段。"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = None
    config: Optional[dict] = None
    status: Optional[int] = None


class DataSourceResponse(BaseModel):
    """数据源响应体：返回数据源详情的标准结构，支持直接从 ORM 实体转换。"""
    id: int
    name: str
    type: str
    config: Optional[dict] = None
    status: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DataPipelineCreate(BaseModel):
    """流水线创建请求体：定义新增采集流水线时必须传入的字段及约束。"""
    name: str = Field(..., min_length=1, max_length=200, description="流水线名称")
    source_id: int = Field(..., description="关联数据源 ID")
    schedule: Optional[str] = Field(None, description="cron 定时表达式，为空则不调度")
    extract_rules: Optional[dict] = Field(None, description="提取规则：{field_map, filter}")
    target_asset_id: Optional[int] = Field(None, description="目标资产 ID（预留）")
    status: Optional[int] = Field(1, description="状态：1=启用，0=停用")


class DataPipelineUpdate(BaseModel):
    """流水线更新请求体：所有字段均为可选，仅更新传入的非空字段。"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    source_id: Optional[int] = None
    schedule: Optional[str] = None
    extract_rules: Optional[dict] = None
    target_asset_id: Optional[int] = None
    status: Optional[int] = None


class DataPipelineResponse(BaseModel):
    """流水线响应体：返回采集流水线详情的标准结构，支持直接从 ORM 实体转换。"""
    id: int
    name: str
    source_id: int
    schedule: Optional[str] = None
    extract_rules: Optional[dict] = None
    target_asset_id: Optional[int] = None
    status: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PipelineRunResponse(BaseModel):
    """流水线运行记录响应体：返回单次执行的完整信息（包含数据和错误）。"""
    id: int
    pipeline_id: int
    triggered_by: str
    start_at: datetime
    end_at: Optional[datetime] = None
    status: str
    rows_count: int
    error_msg: Optional[str] = None
    data: Optional[list] = None

    model_config = {"from_attributes": True}


class ManualRunRequest(BaseModel):
    """手动触发执行请求体：force=True 时忽略正在运行的实例并强制执行。"""
    force: Optional[bool] = Field(False, description="是否忽略正在运行的记录强制执行")
