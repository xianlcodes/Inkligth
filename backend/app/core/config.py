import os
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="allow")

    PROJECT_NAME: str = "InkLight"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # Security
    SECRET_KEY: str = "inklight-secret-key-change-in-production"
    JWT_SECRET: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @model_validator(mode="after")
    def _apply_jwt_secret(self) -> "Settings":
        if self.JWT_SECRET and self.SECRET_KEY == "inklight-secret-key-change-in-production":
            self.SECRET_KEY = self.JWT_SECRET
        return self

    # 数据库和缓存的完整 URL（可选，由 OS 环境变量直接提供时最高优先）
    # 注意：.env 文件中的 DATABASE_URL / REDIS_URL 不会覆盖分散字段，
    # 因为分散字段可被 docker-compose / docker -e 逐个覆盖，更灵活。
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # PostgreSQL 分散字段（可通过 env var 逐个覆盖）
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_USER: str = "inklight"
    POSTGRES_PASSWORD: str = "inklight"
    POSTGRES_DB: str = "inklight"

    # Redis 分散字段（仅当 REDIS_URL 为空时使用）
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # AI Provider fallback settings
    DEFAULT_AI_PROVIDER: str = "openai"
    DEFAULT_AI_BASE_URL: str = "https://api.openai.com/v1"
    DEFAULT_AI_KEY: str = ""
    DEFAULT_AI_MODEL: str = "gpt-4o-mini"
    AI_KEY_SECRET: str = ""

    # Brevo email service
    BREVO_API_KEY: str = ""
    BREVO_SENDER_EMAIL: str = ""
    BREVO_SENDER_NAME: str = "InkLight"
    DEV_MODE: bool = False

    # Embedding model
    EMBEDDING_MODEL_PATH: str = "E:/InkLight/code/backend/all-MiniLM-L6-v2"

    # File storage
    UPLOAD_DIR: str = "uploads"

    # Proxy for AI API calls (e.g., http://127.0.0.1:7890)
    PROXY_URL: str = ""

    # Translation cache
    TRANSLATION_CACHE_TTL_DAYS: int = 7

    # ONNX Layout analysis model
    HF_ENDPOINT: str = "https://hf-mirror.com"
    LAYOUT_MODEL_PATH: str = ""
    LAYOUT_MODEL_REPO: str = "wybxc/DocLayout-YOLO-DocStructBench-onnx"
    LAYOUT_MODEL_FILENAME: str = "doclayout_yolo_docstructbench_imgsz1024.onnx"
    LAYOUT_MODEL_BACKEND: str = "cpu"

    @property
    def DATABASE_URL_FINAL(self) -> str:
        """返回实际使用的数据库 URL

        始终从分散字段构建 URL；docker-compose / docker -e 可通过
        POSTGRES_SERVER 等字段逐个覆盖，比整段 URL 更灵活。
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL_FINAL(self) -> str:
        """返回实际使用的 Redis URL

        始终从分散字段构建 URL；docker-compose / docker -e 可通过
        REDIS_HOST 等字段逐个覆盖，比整段 URL 更灵活。
        """
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()