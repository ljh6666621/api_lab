import models  # noqa: F401 - 触发 ORM 子类注册到 Base.metadata
from core.database import Base, engine


def create_tables():
    """根据 ORM 模型定义自动创建所有数据表（仅创建不存在的表，幂等）。"""
    Base.metadata.create_all(bind=engine)


def init_all(verbose: bool = True):
    """
    数据库初始化总入口：仅创建数据表，不填充任何种子数据。
    由 FastAPI lifespan 事件在服务启动时自动调用。
    :param verbose: 是否打印初始化日志
    """
    create_tables()
    if verbose:
        print("[init_db] 数据表创建完成")


if __name__ == "__main__":
    init_all()