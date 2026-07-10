from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import create_access_token, get_current_user
from models.user import User
from schemas.user import LoginResponse, UserRegister, UserResponse
from services.user import user_service

router = APIRouter(prefix="/users", tags=["用户"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: UserRegister, db: Session = Depends(get_db)):
    """
    用户注册接口：创建新用户账号。
    用户名与邮箱不可重复，密码将通过 bcrypt 哈希后存入数据库。
    """
    user = user_service.register(
        db,
        username=body.username,
        email=body.email,
        password=body.password,
        mobile=body.mobile or "",
        dept_id=body.dept_id or 0,
    )
    if not user:
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")
    return user


@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    用户登录接口（OAuth2 Password 模式）：校验用户名/邮箱 + 密码。
    验证通过后签发 JWT Access Token，并附带当前用户基本信息。
    """
    user = user_service.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != 1:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    token = create_access_token(data={"sub": user.id})
    return LoginResponse(access_token=token, token_type="bearer", user=user)


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户自身的信息（无需传 user_id，由 JWT 自动解析）。"""
    return current_user


@router.get("", response_model=dict)
def list_users(
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    用户列表接口（需登录）：支持按状态过滤、按用户名模糊搜索。
    返回总条数与用户明细列表。
    """
    users = user_service.list_all(db, status=status, keyword=keyword)
    return {"total": len(users), "items": [UserResponse.model_validate(u) for u in users]}


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """根据用户 ID 获取单个用户的详情信息；用户不存在返回 404。"""
    user = user_service.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
