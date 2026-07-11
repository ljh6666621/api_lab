from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime

from core.database import Base


class Product(Base):
    """商品数据模型：记录商品名称、品类、单价、库存等核心信息。"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
