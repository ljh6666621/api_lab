from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime

from core.database import Base


class Department(Base):
    """部门数据模型：描述组织架构中的部门，支持 parent_id 建立层级关系。"""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    parent_id = Column(Integer, default=0, index=True)
    leader = Column(String(50), default="")
    phone = Column(String(20), default="")
    status = Column(Integer, default=1, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
