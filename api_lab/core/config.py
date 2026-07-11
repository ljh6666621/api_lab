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