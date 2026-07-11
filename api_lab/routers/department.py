from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.user import User
from schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from schemas.product import DeleteResponse
from services.department import dept_service

router = APIRouter(prefix="/departments", tags=["部门管理"])


@router.get("", response_model=list[DepartmentResponse])
def list_departments(
    status: Optional[int] = Query(None, description="按状态过滤"),
    keyword: Optional[str] = Query(None, description="按部门名称搜索"),
    db: Session = Depends(get_db),
):
    """部门列表接口：支持按状态过滤、按部门名称模糊搜索。"""
    return dept_service.list_all(db, status=status, keyword=keyword)


@router.get("/{dept_id}", response_model=DepartmentResponse)
def get_department(dept_id: int, db: Session = Depends(get_db)):
    """根据部门 ID 获取部门详情；部门不存在时返回 HTTP 404。"""
    dept = dept_service.get(db, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")
    return dept


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    body: DepartmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新增部门接口（需登录）：部门名称不能重复，创建成功返回部门实体。"""
    dept = dept_service.create(db, body.model_dump())
    if not dept:
        raise HTTPException(status_code=400, detail="部门名称已存在")
    return dept


@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(
    dept_id: int,
    body: DepartmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新部门接口（需登录）：根据 ID 局部更新部门信息；无字段或不存在时报错。"""
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")
    updated = dept_service.update(db, dept_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="部门不存在")
    return updated


@router.delete("/{dept_id}", response_model=DeleteResponse)
def delete_department(
    dept_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除部门接口（需登录）：按 ID 删除部门，部门不存在返回 HTTP 404。"""
    if not dept_service.delete(db, dept_id):
        raise HTTPException(status_code=404, detail="部门不存在")
    return DeleteResponse(success=True, message="删除成功")
