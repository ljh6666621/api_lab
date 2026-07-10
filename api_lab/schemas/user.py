from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """用户通用字段基类：定义了注册、响应等场景共用的基础字段。"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")
    mobile: Optional[str] = Field("", max_length=20, description="手机号")
    dept_id: Optional[int] = Field(0, description="部门ID")


class UserRegister(UserBase):
    """用户注册请求体：继承通用字段并补充明文密码，含密码长度校验。"""
    password: str = Field(..., min_length=6, max_length=50, description="明文密码")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Pydantic 字段校验器：确保注册密码长度不小于 6 位。"""
        if len(v) < 6:
            raise ValueError("密码长度不能少于 6 位")
        return v


class UserLogin(BaseModel):
    """用户登录请求体：接收用户名/邮箱 + 密码进行认证。"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    """登录成功响应体：返回 JWT 访问令牌、令牌类型及用户基本信息。"""
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    """用户信息响应体：返回给前端的用户公开字段，不包含密码哈希。"""
    id: int
    username: str
    email: str
    mobile: str
    dept_id: int
    status: int = Field(description="1正常 2禁用")

    model_config = {"from_attributes": True}


LoginResponse.model_rebuild()
