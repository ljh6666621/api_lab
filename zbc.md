# API Lab 项目 - 成员 b 代码汇总

**负责模块**：配置与安全模块  
**日期**：2026-07-10  

---

## core/config.py

```python
from pathlib import Path

from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_DB_PATH = BASE_DIR / "data" / "api_lab.db"


class Settings(BaseSettings):
    DB_DRIVER: str = "sqlite"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "collab_platform_test"

    SECRET_KEY: str = "api-lab-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    DEFAULT_USER_PASSWORD: str = "123456"

    DEFAULT_MODEL_ID: int = 0
    IM_ENABLE: bool = True
    SCHEDULER_ENABLE: bool = True

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_DRIVER == "sqlite":
            return f"sqlite:///{SQLITE_DB_PATH}"
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

DB_DRIVER = settings.DB_DRIVER
DB_HOST = settings.DB_HOST
DB_PORT = settings.DB_PORT
DB_USER = settings.DB_USER
DB_PASSWORD = settings.DB_PASSWORD
DB_NAME = settings.DB_NAME
DATABASE_URL = settings.DATABASE_URL
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
DEFAULT_USER_PASSWORD = settings.DEFAULT_USER_PASSWORD
DEFAULT_MODEL_ID = settings.DEFAULT_MODEL_ID
IM_ENABLE = settings.IM_ENABLE
SCHEDULER_ENABLE = settings.SCHEDULER_ENABLE
```

---

## core/security.py

```python
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
```

---

## core/database.py

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import DATABASE_URL, DB_DRIVER

connect_args = {}
if DB_DRIVER == "sqlite":
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 模型基类，所有数据模型均需继承此类。"""
    pass


def get_db():
    """
    数据库会话依赖项（FastAPI Depends）。
    创建一个新的数据库会话，在请求结束后自动关闭连接。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## core/crypto.py

```python
import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from core.config import SECRET_KEY


def _derive_fernet_key(master_secret: str) -> bytes:
    """
    根据 SECRET_KEY 通过 SHA256 + base64 派生 Fernet 对称加密密钥。
    保证密钥与 JWT SECRET_KEY 同源，避免引入新的配置项。
    :param master_secret: 原始主密钥（通常是 config.SECRET_KEY）
    :return: 32 字节 base64 编码的 Fernet key（bytes）
    """
    digest = hashlib.sha256(master_secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet_instance: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """
    获取 Fernet 单例（基于 SECRET_KEY 派生）。
    :return: 已初始化的 Fernet 实例
    """
    global _fernet_instance
    if _fernet_instance is None:
        key = _derive_fernet_key(SECRET_KEY)
        _fernet_instance = Fernet(key)
    return _fernet_instance


def encrypt_secret(plain_text: Optional[str]) -> Optional[str]:
    """
    对敏感字段（例如 LLM api_key）进行 Fernet 对称加密。
    明文为 None 或空字符串时原样返回，避免把空值塞进数据库。
    :param plain_text: 明文字符串（如 api_key）
    :return: base64 格式的加密字符串；或 None
    """
    if plain_text is None or plain_text == "":
        return plain_text
    f = _get_fernet()
    token = f.encrypt(plain_text.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(cipher_text: Optional[str]) -> Optional[str]:
    """
    对加密过的敏感字段解密还原。
    入参为 None / 空字符串 或 非法 token 时返回 None（上层需自行处理）。
    :param cipher_text: encrypt_secret 返回的加密字符串
    :return: 明文字符串；或 None（解密失败/缺省）
    """
    if cipher_text is None or cipher_text == "":
        return None
    try:
        f = _get_fernet()
        return f.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None
```

---

**完成文件数**：4 个  
**代码行数**：约 150 行
