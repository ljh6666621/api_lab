from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from core.database import get_db
from models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login", auto_error=False)


def hash_password(plain_password: str) -> str:
    """
    使用 bcrypt 算法对明文密码进行哈希加密（12轮盐）。
    :param plain_password: 用户输入的明文密码
    :return: 加密后的密码哈希字符串（存储至 password_hash 字段）
    """
    if isinstance(plain_password, str):
        plain_password = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证用户输入的明文密码是否与数据库中存储的哈希密码匹配。
    :param plain_password: 用户登录时输入的明文密码
    :param hashed_password: 数据库中存储的 bcrypt 哈希密码
    :return: 匹配成功返回 True，失败或异常返回 False
    """
    if isinstance(plain_password, str):
        plain_password = plain_password.encode("utf-8")
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode("utf-8")
    try:
        return bcrypt.checkpw(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    生成 JWT 访问令牌（Access Token）。
    :param data: 需要编码进令牌的数据，例如 {"sub": 用户ID}
    :param expires_delta: 可选的过期时长；为 None 时使用配置中的默认时长
    :return: 签好名的 JWT 字符串
    """
    to_encode = data.copy()
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    从请求头中解析 JWT Bearer Token，验证并获取当前登录用户。
    用作 FastAPI 路由的权限依赖项：登录 + 账号状态为正常(status=1) 才能通过。
    :param token: OAuth2 从 Authorization 头中提取的 Bearer Token
    :param db: 数据库会话依赖
    :return: 当前请求对应的 User 实体；鉴权失败会抛出 HTTP 401/403
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的身份凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        user_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if user.status != 1:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return user
