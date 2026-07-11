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
