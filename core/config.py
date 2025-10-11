"""
Centralised configuration module for the RCA Engine.
Provides a single Settings object with nested helper views for the
security, database, redis, LLM, file-processing, and worker subsystems.
"""

from functools import cached_property
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str) -> List[str]:
    """Convert simple comma separated values into a list."""
    return [item.strip() for item in value.split(",") if item.strip()]


class SecuritySettings(BaseModel):
    """Security-related configuration."""

    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "rca-engine"
    JWT_AUDIENCE: str = "rca-users"

    CORS_ALLOW_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default_factory=lambda: ["*"])

    CSRF_TOKEN_LENGTH: int = 32
    CSRF_TOKEN_EXPIRE_MINUTES: int = 60
    CSRF_SAME_SITE: str = "strict"
    CSRF_SECURE: bool = True
    CSRF_HTTP_ONLY: bool = True

    RATE_LIMITING_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/hour"
    RATE_LIMIT_AUTH: str = "1000/hour"
    RATE_LIMIT_BURST: str = "10/minute"

    CSP_ENABLED: bool = True
    CSP_REPORT_ONLY: bool = False


class DatabaseSettings(BaseModel):
    """Database configuration."""

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "rca_user"
    POSTGRES_PASSWORD: str = "rca_password"
    POSTGRES_DB: str = "rca_engine"

    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True

    VECTOR_DIMENSION: int = 1536

    @computed_field(return_type=str)
    def DATABASE_URL(self) -> str:  # noqa: N802 (keep uppercase for compatibility)
        """Async SQLAlchemy connection string."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


class RedisSettings(BaseModel):
    """Redis configuration."""

    REDIS_ENABLED: bool = False
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_SSL: bool = False

    @computed_field(return_type=str)
    def REDIS_URL(self) -> str:  # noqa: N802
        """Redis connection URL."""
        if not self.REDIS_ENABLED:
            return ""

        scheme = "rediss" if self.REDIS_SSL else "redis"
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"{scheme}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class LLMSettings(BaseModel):
    """LLM provider configuration."""

    DEFAULT_PROVIDER: str = "ollama"

    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_HOST: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama2"
    OLLAMA_TIMEOUT: int = 300
    OLLAMA_MAX_TOKENS: int = 4096

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_ORG_ID: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 4096

    BEDROCK_REGION: str = "us-east-1"
    BEDROCK_MODEL: str = "anthropic.claude-v2"
    BEDROCK_MAX_TOKENS: int = 4096

    EMBEDDING_PROVIDER: str = "openai"


class FileSettings(BaseModel):
    """File processing configuration."""

    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_FILE_TYPES: List[str] = Field(
        default_factory=lambda: ["log", "txt", "json", "xml", "csv", "yaml", "yml"]
    )

    UPLOAD_DIR: str = "uploads"
    REPORTS_DIR: str = "reports"
    WATCH_FOLDER: str = "watch-folder"

    ENABLE_VIRUS_SCAN: bool = False
    ENABLE_FILE_VALIDATION: bool = True

    CHUNK_SIZE: int = 1024 * 1024  # 1MB
    MAX_CONCURRENT_UPLOADS: int = 10


class WorkerSettings(BaseModel):
    """Background worker configuration."""

    WORKER_POLL_INTERVAL: int = 5
    WORKER_MAX_CONCURRENT_JOBS: int = 5
    WORKER_TIMEOUT: int = 1800
    WORKER_RETRY_ATTEMPTS: int = 3
    WORKER_RETRY_DELAY: int = 60


class Settings(BaseSettings):
    """Main application settings exposed as a singleton."""

    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(False, env="DEBUG")

    APP_NAME: str = "RCA Engine"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", env="LOG_FORMAT")

    METRICS_ENABLED: bool = Field(True, env="METRICS_ENABLED")
    METRICS_PORT: int = Field(8001, env="METRICS_PORT")

    # Security
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    JWT_ISSUER: str = Field("rca-engine", env="JWT_ISSUER")
    JWT_AUDIENCE: str = Field("rca-users", env="JWT_AUDIENCE")

    CORS_ALLOW_ORIGINS: List[str] = Field(default_factory=lambda: ["*"], env="CORS_ALLOW_ORIGINS")
    CORS_ALLOW_CREDENTIALS: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    CORS_ALLOW_METHODS: List[str] = Field(default_factory=lambda: ["*"], env="CORS_ALLOW_METHODS")
    CORS_ALLOW_HEADERS: List[str] = Field(default_factory=lambda: ["*"], env="CORS_ALLOW_HEADERS")

    CSRF_TOKEN_LENGTH: int = Field(32, env="CSRF_TOKEN_LENGTH")
    CSRF_TOKEN_EXPIRE_MINUTES: int = Field(60, env="CSRF_TOKEN_EXPIRE_MINUTES")
    CSRF_SAME_SITE: str = Field("strict", env="CSRF_SAME_SITE")
    CSRF_SECURE: bool = Field(True, env="CSRF_SECURE")
    CSRF_HTTP_ONLY: bool = Field(True, env="CSRF_HTTP_ONLY")

    RATE_LIMITING_ENABLED: bool = Field(True, env="RATE_LIMITING_ENABLED")
    RATE_LIMIT_DEFAULT: str = Field("100/hour", env="RATE_LIMIT_DEFAULT")
    RATE_LIMIT_AUTH: str = Field("1000/hour", env="RATE_LIMIT_AUTH")
    RATE_LIMIT_BURST: str = Field("10/minute", env="RATE_LIMIT_BURST")
    CSP_ENABLED: bool = Field(True, env="CSP_ENABLED")
    CSP_REPORT_ONLY: bool = Field(False, env="CSP_REPORT_ONLY")

    # Database
    POSTGRES_HOST: str = Field("localhost", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_USER: str = Field("rca_user", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("rca_engine", env="POSTGRES_DB")

    DB_POOL_SIZE: int = Field(20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(40, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(3600, env="DB_POOL_RECYCLE")
    DB_POOL_PRE_PING: bool = Field(True, env="DB_POOL_PRE_PING")
    VECTOR_DIMENSION: int = Field(1536, env="VECTOR_DIMENSION")

    # Redis
    REDIS_ENABLED: bool = Field(False, env="REDIS_ENABLED")
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    REDIS_SSL: bool = Field(False, env="REDIS_SSL")

    # LLM
    DEFAULT_PROVIDER: str = Field("ollama", env="DEFAULT_PROVIDER")
    OLLAMA_BASE_URL: str = Field("http://ollama:11434", env="OLLAMA_BASE_URL")
    OLLAMA_HOST: str = Field("http://ollama:11434", env="OLLAMA_HOST")
    OLLAMA_MODEL: str = Field("llama2", env="OLLAMA_MODEL")
    OLLAMA_TIMEOUT: int = Field(300, env="OLLAMA_TIMEOUT")
    OLLAMA_MAX_TOKENS: int = Field(4096, env="OLLAMA_MAX_TOKENS")

    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    OPENAI_ORG_ID: Optional[str] = Field(None, env="OPENAI_ORG_ID")
    OPENAI_MODEL: str = Field("gpt-4", env="OPENAI_MODEL")
    OPENAI_MAX_TOKENS: int = Field(4096, env="OPENAI_MAX_TOKENS")

    BEDROCK_REGION: str = Field("us-east-1", env="BEDROCK_REGION")
    BEDROCK_MODEL: str = Field("anthropic.claude-v2", env="BEDROCK_MODEL")
    BEDROCK_MAX_TOKENS: int = Field(4096, env="BEDROCK_MAX_TOKENS")
    EMBEDDING_PROVIDER: str = Field("openai", env="EMBEDDING_PROVIDER")

    # Files
    MAX_FILE_SIZE_MB: int = Field(100, env="MAX_FILE_SIZE_MB")
    ALLOWED_FILE_TYPES: List[str] = Field(
        default_factory=lambda: ["log", "txt", "json", "xml", "csv", "yaml", "yml"],
        env="ALLOWED_FILE_TYPES",
    )
    UPLOAD_DIR: str = Field("uploads", env="UPLOAD_DIR")
    REPORTS_DIR: str = Field("reports", env="REPORTS_DIR")
    WATCH_FOLDER: str = Field("watch-folder", env="WATCH_FOLDER")
    ENABLE_VIRUS_SCAN: bool = Field(False, env="ENABLE_VIRUS_SCAN")
    ENABLE_FILE_VALIDATION: bool = Field(True, env="ENABLE_FILE_VALIDATION")
    CHUNK_SIZE: int = Field(1024 * 1024, env="CHUNK_SIZE")
    MAX_CONCURRENT_UPLOADS: int = Field(10, env="MAX_CONCURRENT_UPLOADS")

    # Worker
    WORKER_POLL_INTERVAL: int = Field(5, env="WORKER_POLL_INTERVAL")
    WORKER_MAX_CONCURRENT_JOBS: int = Field(5, env="WORKER_MAX_CONCURRENT_JOBS")
    WORKER_TIMEOUT: int = Field(1800, env="WORKER_TIMEOUT")
    WORKER_RETRY_ATTEMPTS: int = Field(3, env="WORKER_RETRY_ATTEMPTS")
    WORKER_RETRY_DELAY: int = Field(60, env="WORKER_RETRY_DELAY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @field_validator(
        "CORS_ALLOW_ORIGINS",
        "CORS_ALLOW_METHODS",
        "CORS_ALLOW_HEADERS",
        "ALLOWED_FILE_TYPES",
        mode="before",
    )
    @classmethod
    def _coerce_list(cls, v):
        if isinstance(v, str):
            return _split_csv(v)
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return value

    @cached_property
    def security(self) -> SecuritySettings:
        """Convenience wrapper exposing security configuration."""
        return SecuritySettings(
            JWT_SECRET_KEY=self.JWT_SECRET_KEY,
            JWT_ALGORITHM=self.JWT_ALGORITHM,
            JWT_ACCESS_TOKEN_EXPIRE_MINUTES=self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            JWT_REFRESH_TOKEN_EXPIRE_DAYS=self.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
            JWT_ISSUER=self.JWT_ISSUER,
            JWT_AUDIENCE=self.JWT_AUDIENCE,
            CORS_ALLOW_ORIGINS=self.CORS_ALLOW_ORIGINS,
            CORS_ALLOW_CREDENTIALS=self.CORS_ALLOW_CREDENTIALS,
            CORS_ALLOW_METHODS=self.CORS_ALLOW_METHODS,
            CORS_ALLOW_HEADERS=self.CORS_ALLOW_HEADERS,
            CSRF_TOKEN_LENGTH=self.CSRF_TOKEN_LENGTH,
            CSRF_TOKEN_EXPIRE_MINUTES=self.CSRF_TOKEN_EXPIRE_MINUTES,
            CSRF_SAME_SITE=self.CSRF_SAME_SITE,
            CSRF_SECURE=self.CSRF_SECURE,
            CSRF_HTTP_ONLY=self.CSRF_HTTP_ONLY,
            RATE_LIMITING_ENABLED=self.RATE_LIMITING_ENABLED,
            RATE_LIMIT_DEFAULT=self.RATE_LIMIT_DEFAULT,
            RATE_LIMIT_AUTH=self.RATE_LIMIT_AUTH,
            RATE_LIMIT_BURST=self.RATE_LIMIT_BURST,
            CSP_ENABLED=self.CSP_ENABLED,
            CSP_REPORT_ONLY=self.CSP_REPORT_ONLY,
        )

    @cached_property
    def database(self) -> DatabaseSettings:
        """Database configuration view."""
        return DatabaseSettings(
            POSTGRES_HOST=self.POSTGRES_HOST,
            POSTGRES_PORT=self.POSTGRES_PORT,
            POSTGRES_USER=self.POSTGRES_USER,
            POSTGRES_PASSWORD=self.POSTGRES_PASSWORD,
            POSTGRES_DB=self.POSTGRES_DB,
            DB_POOL_SIZE=self.DB_POOL_SIZE,
            DB_MAX_OVERFLOW=self.DB_MAX_OVERFLOW,
            DB_POOL_TIMEOUT=self.DB_POOL_TIMEOUT,
            DB_POOL_RECYCLE=self.DB_POOL_RECYCLE,
            DB_POOL_PRE_PING=self.DB_POOL_PRE_PING,
            VECTOR_DIMENSION=self.VECTOR_DIMENSION,
        )

    @cached_property
    def redis(self) -> RedisSettings:
        """Redis configuration view."""
        return RedisSettings(
            REDIS_ENABLED=self.REDIS_ENABLED,
            REDIS_HOST=self.REDIS_HOST,
            REDIS_PORT=self.REDIS_PORT,
            REDIS_PASSWORD=self.REDIS_PASSWORD,
            REDIS_DB=self.REDIS_DB,
            REDIS_SSL=self.REDIS_SSL,
        )

    @cached_property
    def llm(self) -> LLMSettings:
        """LLM configuration view."""
        return LLMSettings(
            DEFAULT_PROVIDER=self.DEFAULT_PROVIDER,
            OLLAMA_BASE_URL=self.OLLAMA_BASE_URL,
            OLLAMA_HOST=self.OLLAMA_HOST,
            OLLAMA_MODEL=self.OLLAMA_MODEL,
            OLLAMA_TIMEOUT=self.OLLAMA_TIMEOUT,
            OLLAMA_MAX_TOKENS=self.OLLAMA_MAX_TOKENS,
            OPENAI_API_KEY=self.OPENAI_API_KEY,
            OPENAI_ORG_ID=self.OPENAI_ORG_ID,
            OPENAI_MODEL=self.OPENAI_MODEL,
            OPENAI_MAX_TOKENS=self.OPENAI_MAX_TOKENS,
            BEDROCK_REGION=self.BEDROCK_REGION,
            BEDROCK_MODEL=self.BEDROCK_MODEL,
            BEDROCK_MAX_TOKENS=self.BEDROCK_MAX_TOKENS,
            EMBEDDING_PROVIDER=self.EMBEDDING_PROVIDER,
        )

    @cached_property
    def files(self) -> FileSettings:
        """File-processing configuration view."""
        return FileSettings(
            MAX_FILE_SIZE_MB=self.MAX_FILE_SIZE_MB,
            ALLOWED_FILE_TYPES=self.ALLOWED_FILE_TYPES,
            UPLOAD_DIR=self.UPLOAD_DIR,
            REPORTS_DIR=self.REPORTS_DIR,
            WATCH_FOLDER=self.WATCH_FOLDER,
            ENABLE_VIRUS_SCAN=self.ENABLE_VIRUS_SCAN,
            ENABLE_FILE_VALIDATION=self.ENABLE_FILE_VALIDATION,
            CHUNK_SIZE=self.CHUNK_SIZE,
            MAX_CONCURRENT_UPLOADS=self.MAX_CONCURRENT_UPLOADS,
        )

    @cached_property
    def worker(self) -> WorkerSettings:
        """Worker configuration view."""
        return WorkerSettings(
            WORKER_POLL_INTERVAL=self.WORKER_POLL_INTERVAL,
            WORKER_MAX_CONCURRENT_JOBS=self.WORKER_MAX_CONCURRENT_JOBS,
            WORKER_TIMEOUT=self.WORKER_TIMEOUT,
            WORKER_RETRY_ATTEMPTS=self.WORKER_RETRY_ATTEMPTS,
            WORKER_RETRY_DELAY=self.WORKER_RETRY_DELAY,
        )

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        return self.database.DATABASE_URL

    @property
    def REDIS_URL(self) -> str:  # noqa: N802
        return self.redis.REDIS_URL


# Expose a singleton instance mirroring the previous API.
settings = Settings()

__all__ = ["Settings", "settings"]
