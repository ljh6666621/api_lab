from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime

from core.database import Base


class User(Base):
    """用户数据模型：存储系统用户的基本信息、账号状态及关联部门。"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    mobile = Column(String(20), default="")
    password_hash = Column(String(255), nullable=False)
    dept_id = Column(Integer, default=0, index=True)
    status = Column(Integer, default=1, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
