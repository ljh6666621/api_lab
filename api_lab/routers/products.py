from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.user import User
from schemas.product import DeleteResponse, ProductCreate, ProductResponse, ProductUpdate
from services.product import product_service

router = APIRouter(prefix="/products", tags=["商品管理"])


@router.get("", response_model=list[ProductResponse])
def list_products(
    name: Optional[str] = Query(None, description="按名称模糊搜索"),
    min_price: Optional[float] = Query(None, ge=0, description="最低价格"),
    max_price: Optional[float] = Query(None, ge=0, description="最高价格"),
    db: Session = Depends(get_db),
):
    """商品列表接口：支持按商品名称模糊搜索、按价格区间过滤。"""
    return product_service.list_all(db, name=name, min_price=min_price, max_price=max_price)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """根据商品 ID 获取单个商品详情；不存在时返回 HTTP 404。"""
    product = product_service.get(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    body: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新增商品接口（需登录）：接收商品信息并持久化到数据库，返回创建后的商品。"""
    return product_service.create(db, body.model_dump())


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    body: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新商品接口（需登录）：根据 ID 局部更新商品字段；无有效字段或商品不存在会报错。"""
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")
    updated = product_service.update(db, product_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="商品不存在")
    return updated


@router.delete("/{product_id}", response_model=DeleteResponse)
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除商品接口（需登录）：根据 ID 删除商品，删除失败（不存在）返回 404。"""
    if not product_service.delete(db, product_id):
        raise HTTPException(status_code=404, detail="商品不存在")
    return DeleteResponse(success=True, message="删除成功")
