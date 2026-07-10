from typing import Optional

from sqlalchemy.orm import Session

from models.product import Product


class ProductRepository:
    """商品仓储服务：封装商品 CRUD 及按条件查询的数据库操作。"""

    def list_all(
        self,
        db: Session,
        name: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> list[Product]:
        """
        查询商品列表，支持按名称模糊匹配、按价格区间过滤。
        :param db: 数据库会话
        :param name: 商品名称关键字（可选）
        :param min_price: 最低价格（可选，含等于）
        :param max_price: 最高价格（可选，含等于）
        :return: 满足条件的商品列表
        """
        query = db.query(Product)
        if name:
            query = query.filter(Product.name.contains(name))
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        return query.all()

    def get(self, db: Session, product_id: int) -> Optional[Product]:
        """
        按商品 ID 查找单个商品。
        :param db: 数据库会话
        :param product_id: 商品主键
        :return: 找到返回 Product，否则 None
        """
        return db.query(Product).filter(Product.id == product_id).first()

    def create(self, db: Session, data: dict) -> Product:
        """
        创建新商品，写入数据库并刷新获取自增 ID、创建/更新时间。
        :param db: 数据库会话
        :param data: 商品字段字典，对应 ProductCreate schema
        :return: 新建后的商品实体
        """
        item = Product(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update(self, db: Session, product_id: int, data: dict) -> Optional[Product]:
        """
        按 ID 局部更新商品字段；若商品不存在返回 None。
        :param db: 数据库会话
        :param product_id: 目标商品 ID
        :param data: 待更新字段字典（仅包含需要修改的键）
        :return: 更新后的商品实体，或 None
        """
        item = self.get(db, product_id)
        if not item:
            return None
        for key, value in data.items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return item

    def delete(self, db: Session, product_id: int) -> bool:
        """
        按 ID 删除商品。
        :param db: 数据库会话
        :param product_id: 目标商品 ID
        :return: 删除成功返回 True，商品不存在返回 False
        """
        item = self.get(db, product_id)
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True


product_service = ProductRepository()
