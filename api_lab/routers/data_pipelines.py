import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.user import User
from schemas.data_pipeline import (
    DataPipelineCreate,
    DataPipelineResponse,
    DataPipelineUpdate,
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    ManualRunRequest,
    PipelineRunResponse,
)
from services.data_pipeline import (
    data_source_service,
    execute_pipeline,
    pipeline_service,
)

router = APIRouter(prefix="/pipelines", tags=["数据采集流水线"])


@router.post("/sources", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
def create_data_source(
    body: DataSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建数据源接口（需登录）：持久化数据源配置，返回创建后的数据源详情。"""
    data = body.model_dump()
    data["created_by"] = current_user.id
    return data_source_service.create(db, data)


@router.get("/sources", response_model=list[DataSourceResponse])
def list_data_sources(
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(100, ge=1, le=500, description="每页条数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """数据源列表接口（需登录）：分页返回所有数据源。"""
    return data_source_service.list(db, skip=skip, limit=limit)


@router.get("/sources/{source_id}", response_model=DataSourceResponse)
def get_data_source(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """根据 ID 获取单个数据源详情（需登录）；不存在返回 HTTP 404。"""
    source = data_source_service.get(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return source


@router.put("/sources/{source_id}", response_model=DataSourceResponse)
def update_data_source(
    source_id: int,
    body: DataSourceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新数据源接口（需登录）：按 ID 局部更新字段；无有效字段或不存在时报错。"""
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")
    updated = data_source_service.update(db, source_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return updated


@router.delete("/sources/{source_id}")
def delete_data_source(
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除数据源接口（需登录）：按 ID 删除数据源。"""
    if not data_source_service.delete(db, source_id):
        raise HTTPException(status_code=404, detail="数据源不存在")
    return {"success": True, "message": "删除成功"}


@router.post("", response_model=DataPipelineResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    body: DataPipelineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建流水线接口（需登录）：保存流水线配置，若设置了 schedule 则自动注册 cron 任务。"""
    source = data_source_service.get(db, body.source_id)
    if not source:
        raise HTTPException(status_code=400, detail="关联的数据源不存在")
    data = body.model_dump()
    data["created_by"] = current_user.id
    return pipeline_service.create(db, data)


@router.get("", response_model=list[DataPipelineResponse])
def list_pipelines(
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(100, ge=1, le=500, description="每页条数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """流水线列表接口（需登录）：分页返回所有采集流水线。"""
    return pipeline_service.list(db, skip=skip, limit=limit)


@router.get("/{pipeline_id}", response_model=DataPipelineResponse)
def get_pipeline(
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """根据 ID 获取单个流水线详情（需登录）；不存在返回 HTTP 404。"""
    pipeline = pipeline_service.get(db, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="流水线不存在")
    return pipeline


@router.put("/{pipeline_id}", response_model=DataPipelineResponse)
def update_pipeline(
    pipeline_id: int,
    body: DataPipelineUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新流水线接口（需登录）：局部更新字段，schedule 变化时同步注册/移除 cron 任务。"""
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")
    if "source_id" in data:
        source = data_source_service.get(db, data["source_id"])
        if not source:
            raise HTTPException(status_code=400, detail="关联的数据源不存在")
    updated = pipeline_service.update(db, pipeline_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="流水线不存在")
    return updated


@router.delete("/{pipeline_id}")
def delete_pipeline(
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除流水线接口（需登录）：按 ID 删除，同步移除已注册的定时任务。"""
    if not pipeline_service.delete(db, pipeline_id):
        raise HTTPException(status_code=404, detail="流水线不存在")
    return {"success": True, "message": "删除成功"}


@router.post("/{pipeline_id}/run", response_model=PipelineRunResponse)
def run_pipeline(
    pipeline_id: int,
    body: ManualRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    手动触发流水线执行（需登录）：
    - 若当前已存在 running 状态的记录且 force=False 则拒绝（400）
    - force=True 时忽略并发限制强制执行
    """
    pipeline = pipeline_service.get(db, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="流水线不存在")
    if not body.force and pipeline_service.has_running(db, pipeline_id):
        raise HTTPException(status_code=400, detail="流水线当前正在运行中，如需强制请设置 force=true")
    return execute_pipeline(db, pipeline_id, triggered_by=f"user_{current_user.id}")


@router.get("/{pipeline_id}/runs", response_model=list[PipelineRunResponse])
def list_pipeline_runs(
    pipeline_id: int,
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(100, ge=1, le=500, description="每页条数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询流水线历史运行记录（需登录）：按开始时间倒序排列。"""
    pipeline = pipeline_service.get(db, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="流水线不存在")
    return pipeline_service.list_runs(db, pipeline_id, skip=skip, limit=limit)


@router.post("/{pipeline_id}/upload", response_model=PipelineRunResponse)
def upload_and_run_pipeline(
    pipeline_id: int,
    file: UploadFile = File(..., description="CSV 文件（UTF-8 编码）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    上传 CSV 文件并触发流水线执行（需登录）：
    - 解析 CSV 为字典列表作为 uploaded_rows 传入执行器
    - 支持 UTF-8 BOM（utf-8-sig）
    """
    pipeline = pipeline_service.get(db, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="流水线不存在")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持 CSV 文件上传")
    try:
        content = file.file.read()
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        uploaded_rows = [dict(row) for row in reader]
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码错误，请使用 UTF-8 编码的 CSV")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV 解析失败: {str(e)}")
    return execute_pipeline(db, pipeline_id, triggered_by="upload", uploaded_rows=uploaded_rows)
