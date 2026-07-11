from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.user import User
from schemas.data_asset import (
    AssetProfileResponse,
    DataAssetCreate,
    DataAssetResponse,
    DataAssetUpdate,
    ManualProfileRequest,
    OverviewResponse,
)
from schemas.product import DeleteResponse
from services.data_asset import (
    AssetProfileRepository,
    DataAssetRepository,
    generate_profile,
)

router = APIRouter(prefix="/assets", tags=["数据资产分析"])


@router.post("", response_model=DataAssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    body: DataAssetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建数据资产接口（需登录）：接收资产信息并持久化，返回创建后的资产。"""
    data = body.model_dump(exclude_unset=True)
    asset = DataAssetRepository.create(db, data)
    return asset


@router.get("", response_model=list[DataAssetResponse])
def list_assets(
    skip: int = Query(0, ge=0, description="跳过条数，用于分页"),
    limit: int = Query(100, ge=1, le=500, description="返回最大条数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """数据资产列表接口（需登录）：分页获取资产列表，按创建时间倒序。"""
    return DataAssetRepository.list(db, skip=skip, limit=limit)


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """数据资产概览接口（需登录）：返回资产总数、总行数、来源分布与今日画像数。"""
    return DataAssetRepository.overview(db)


@router.get("/{asset_id}", response_model=DataAssetResponse)
def get_asset(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """根据资产 ID 获取单个资产详情（需登录）；不存在时返回 HTTP 404。"""
    asset = DataAssetRepository.get(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="数据资产不存在")
    return asset


@router.put("/{asset_id}", response_model=DataAssetResponse)
def update_asset(
    asset_id: int,
    body: DataAssetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新数据资产接口（需登录）：按 ID 局部更新字段；无有效字段或资产不存在时报错。"""
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")
    updated = DataAssetRepository.update(db, asset_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="数据资产不存在")
    return updated


@router.delete("/{asset_id}", response_model=DeleteResponse)
def delete_asset(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除数据资产接口（需登录）：根据 ID 删除，删除失败（不存在）返回 404。"""
    if not DataAssetRepository.delete(db, asset_id):
        raise HTTPException(status_code=404, detail="数据资产不存在")
    return DeleteResponse(success=True, message="删除成功")


@router.post("/{asset_id}/profile", response_model=AssetProfileResponse)
def create_profile(
    asset_id: int,
    body: ManualProfileRequest = ManualProfileRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """手动触发生成资产画像接口（需登录）：最近 1 小时内有画像且 force=False 则复用已有，否则重新生成。"""
    asset = DataAssetRepository.get(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="数据资产不存在")

    if not body.force:
        recent = AssetProfileRepository.get_recent_within(db, asset_id, minutes=60)
        if recent is not None:
            return recent

    try:
        profile = generate_profile(db, asset_id=asset_id, generated_by=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return profile


@router.get("/{asset_id}/profiles", response_model=list[AssetProfileResponse])
def list_profiles(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """历史画像列表接口（需登录）：按资产 ID 返回画像列表，按生成时间倒序。"""
    asset = DataAssetRepository.get(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="数据资产不存在")
    return AssetProfileRepository.list_by_asset(db, asset_id)
