from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "InkLight"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # Security (兼容 .env 中的 JWT_SECRET 或 SECRET_KEY)
    SECRET_KEY: str = "inklight-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 数据库和缓存的完整 URL（可选，如果 .env 中直接提供了则优先使用）
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # PostgreSQL 分散字段（仅当 DATABASE_URL 为空时使用）
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

    # Embedding model
    EMBEDDING_MODEL_PATH: str = "E:/InkLight/code/backend/all-MiniLM-L6-v2"

    # Translation cache
    TRANSLATION_CACHE_TTL_DAYS: int = 7

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 如果 .env 中没有提供 SECRET_KEY，但提供了 JWT_SECRET，则使用 JWT_SECRET
        # 注意：由于 pydantic 禁止额外字段，我们无法直接接收 JWT_SECRET。
        # 所以建议在 .env 中统一使用 SECRET_KEY。如果您的 .env 仍写着 JWT_SECRET，请改为 SECRET_KEY。
        # 此处保留兼容逻辑：从环境变量获取 JWT_SECRET 并赋值给 SECRET_KEY。
        import os
        jwt_secret = os.getenv("JWT_SECRET")
        if jwt_secret and self.SECRET_KEY == "inklight-secret-key-change-in-production":
            self.SECRET_KEY = jwt_secret

    @property
    def DATABASE_URL_FINAL(self) -> str:
        """返回实际使用的数据库 URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL_FINAL(self) -> str:
        """返回实际使用的 Redis URL"""
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        # 允许额外的环境变量，例如 JWT_SECRET
        extra = "allow"


settings = Settings()