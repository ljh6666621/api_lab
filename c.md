# API Lab 项目 - 成员 c 代码汇总

**负责模块**：API 路由框架  
**日期**：2026-07-10  

---

## routers/users.py

```python
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
```

---

## routers/department.py

```python
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
```

---

## routers/products.py

```python
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
```

---

**完成文件数**：3 个  
**代码行数**：约 150 行
