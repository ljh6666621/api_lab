from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL_ID: str = "qwen-plus"
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.7

    model_config = {"env_file": str(BASE_DIR / ".env"), "extra": "ignore"}


settings = Settings()