from typing import Optional

from sqlalchemy.orm import Session

from models.department import Department


class DepartmentRepository:
    """部门仓储服务：封装部门 CRUD、唯一性校验与条件查询等操作。"""

    def list_all(
        self,
        db: Session,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> list[Department]:
        """
        查询部门列表，支持按状态过滤、按部门名称模糊搜索。
        :param db: 数据库会话
        :param status: 可选，1=正常 2=禁用
        :param keyword: 可选，部门名称关键字
        :return: 符合条件的部门列表
        """
        query = db.query(Department)
        if status is not None:
            query = query.filter(Department.status == status)
        if keyword:
            query = query.filter(Department.name.contains(keyword))
        return query.all()

    def get(self, db: Session, dept_id: int) -> Optional[Department]:
        """
        按部门 ID 查找单个部门。
        :param db: 数据库会话
        :param dept_id: 部门主键
        :return: 找到返回 Department，否则 None
        """
        return db.query(Department).filter(Department.id == dept_id).first()

    def get_by_name(self, db: Session, name: str) -> Optional[Department]:
        """
        按部门名称查找，用于创建/编辑前的唯一性校验。
        :param db: 数据库会话
        :param name: 部门名称
        :return: 已存在返回 Department，否则 None
        """
        return db.query(Department).filter(Department.name == name).first()

    def create(self, db: Session, data: dict) -> Optional[Department]:
        """
        新增部门：若同名部门已存在则返回 None，否则写入数据库。
        :param db: 数据库会话
        :param data: 部门字段字典
        :return: 新建后的部门实体；名称冲突为 None
        """
        if self.get_by_name(db, data.get("name", "")):
            return None
        item = Department(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update(self, db: Session, dept_id: int, data: dict) -> Optional[Department]:
        """
        按 ID 局部更新部门字段；部门不存在返回 None。
        :param db: 数据库会话
        :param dept_id: 目标部门 ID
        :param data: 待更新字段字典
        :return: 更新后的部门实体，或 None
        """
        item = self.get(db, dept_id)
        if not item:
            return None
        for key, value in data.items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return item

    def delete(self, db: Session, dept_id: int) -> bool:
        """
        按 ID 删除部门。
        :param db: 数据库会话
        :param dept_id: 目标部门 ID
        :return: 删除成功返回 True；部门不存在返回 False
        """
        item = self.get(db, dept_id)
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True


dept_service = DepartmentRepository()
