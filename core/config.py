"""
Core configuration module for RCA Engine.
Centralized configuration management with environment-based settings.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field, validator
from pathlib import Path


class SecuritySettings(BaseSettings):
    """Security-related settings."""
    
    # JWT Configuration
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    JWT_ISSUER: str = Field("rca-engine", env="JWT_ISSUER")
    JWT_AUDIENCE: str = Field("rca-users", env="JWT_AUDIENCE")
    
    # CORS Configuration
    CORS_ALLOW_ORIGINS: List[str] = Field(["*"], env="CORS_ALLOW_ORIGINS")
    CORS_ALLOW_CREDENTIALS: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    CORS_ALLOW_METHODS: List[str] = Field(["*"], env="CORS_ALLOW_METHODS")
    CORS_ALLOW_HEADERS: List[str] = Field(["*"], env="CORS_ALLOW_HEADERS")
    
    # CSRF Configuration
    CSRF_TOKEN_LENGTH: int = Field(32, env="CSRF_TOKEN_LENGTH")
    CSRF_TOKEN_EXPIRE_MINUTES: int = Field(60, env="CSRF_TOKEN_EXPIRE_MINUTES")
    CSRF_SAME_SITE: str = Field("strict", env="CSRF_SAME_SITE")
    CSRF_SECURE: bool = Field(True, env="CSRF_SECURE")
    CSRF_HTTP_ONLY: bool = Field(True, env="CSRF_HTTP_ONLY")
    
    # Rate Limiting
    RATE_LIMITING_ENABLED: bool = Field(True, env="RATE_LIMITING_ENABLED")
    RATE_LIMIT_DEFAULT: str = Field("100/hour", env="RATE_LIMIT_DEFAULT")
    RATE_LIMIT_AUTH: str = Field("1000/hour", env="RATE_LIMIT_AUTH")
    RATE_LIMIT_BURST: str = Field("10/minute", env="RATE_LIMIT_BURST")
    
    # Content Security Policy
    CSP_ENABLED: bool = Field(True, env="CSP_ENABLED")
    CSP_REPORT_ONLY: bool = Field(False, env="CSP_REPORT_ONLY")
    
    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    # PostgreSQL Configuration
    POSTGRES_HOST: str = Field("localhost", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_USER: str = Field("rca_user", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("rca_engine", env="POSTGRES_DB")
    
    # Connection Pool Settings
    DB_POOL_SIZE: int = Field(20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(40, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(3600, env="DB_POOL_RECYCLE")
    DB_POOL_PRE_PING: bool = Field(True, env="DB_POOL_PRE_PING")
    
    # Vector Settings
    VECTOR_DIMENSION: int = Field(384, env="VECTOR_DIMENSION")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    REDIS_ENABLED: bool = Field(False, env="REDIS_ENABLED")
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    REDIS_SSL: bool = Field(False, env="REDIS_SSL")
    
    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        protocol = "rediss" if self.REDIS_SSL else "redis"
        return f"{protocol}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class LLMSettings(BaseSettings):
    """LLM provider configuration."""
    
    # Default Provider
    DEFAULT_PROVIDER: str = Field("ollama", env="DEFAULT_PROVIDER")
    
    # Ollama Configuration
    OLLAMA_HOST: str = Field("http://ollama:11434", env="OLLAMA_HOST")
    OLLAMA_MODEL: str = Field("llama2", env="OLLAMA_MODEL")
    OLLAMA_TIMEOUT: int = Field(300, env="OLLAMA_TIMEOUT")
    OLLAMA_MAX_TOKENS: int = Field(4096, env="OLLAMA_MAX_TOKENS")
    
    # Embedding Configuration
    EMBEDDING_PROVIDER: str = Field("ollama", env="EMBEDDING_PROVIDER")
    EMBEDDING_MODEL: str = Field("nomic-embed-text", env="EMBEDDING_MODEL")
    EMBEDDING_DIMENSION: int = Field(384, env="EMBEDDING_DIMENSION")
    
    # Rate Limiting
    LLM_RATE_LIMIT_REQUESTS: int = Field(100, env="LLM_RATE_LIMIT_REQUESTS")
    LLM_RATE_LIMIT_PERIOD: int = Field(3600, env="LLM_RATE_LIMIT_PERIOD")


class FileSettings(BaseSettings):
    """File processing configuration."""
    
    # Upload Settings
    MAX_FILE_SIZE_MB: int = Field(100, env="MAX_FILE_SIZE_MB")
    ALLOWED_FILE_TYPES: List[str] = Field(
        ["log", "txt", "json", "xml", "csv", "yaml", "yml"], 
        env="ALLOWED_FILE_TYPES"
    )
    
    # Storage Settings
    UPLOAD_DIR: str = Field("uploads", env="UPLOAD_DIR")
    REPORTS_DIR: str = Field("reports", env="REPORTS_DIR")
    WATCH_FOLDER: str = Field("watch-folder", env="WATCH_FOLDER")
    
    # Security Settings
    ENABLE_VIRUS_SCAN: bool = Field(False, env="ENABLE_VIRUS_SCAN")
    ENABLE_FILE_VALIDATION: bool = Field(True, env="ENABLE_FILE_VALIDATION")
    
    # Processing Settings
    CHUNK_SIZE: int = Field(1024 * 1024, env="CHUNK_SIZE")  # 1MB
    MAX_CONCURRENT_UPLOADS: int = Field(10, env="MAX_CONCURRENT_UPLOADS")


class WorkerSettings(BaseSettings):
    """Worker configuration settings."""
    
    WORKER_POLL_INTERVAL: int = Field(5, env="WORKER_POLL_INTERVAL")
    WORKER_MAX_CONCURRENT_JOBS: int = Field(5, env="WORKER_MAX_CONCURRENT_JOBS")
    WORKER_TIMEOUT: int = Field(1800, env="WORKER_TIMEOUT")  # 30 minutes
    WORKER_RETRY_ATTEMPTS: int = Field(3, env="WORKER_RETRY_ATTEMPTS")
    WORKER_RETRY_DELAY: int = Field(60, env="WORKER_RETRY_DELAY")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Environment
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(False, env="DEBUG")
    
    # Application
    APP_NAME: str = "RCA Engine"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    security: SecuritySettings = SecuritySettings()
    
    # Database
    database: DatabaseSettings = DatabaseSettings()
    
    # Redis
    redis: RedisSettings = RedisSettings()
    
    # LLM
    llm: LLMSettings = LLMSettings()
    
    # Files
    files: FileSettings = FileSettings()
    
    # Worker
    worker: WorkerSettings = WorkerSettings()
    
    # Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", env="LOG_FORMAT")
    
    # Metrics
    METRICS_ENABLED: bool = Field(True, env="METRICS_ENABLED")
    METRICS_PORT: int = Field(8001, env="METRICS_PORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Derived properties
@property
def REDIS_ENABLED(self) -> bool:
    return settings.redis.REDIS_ENABLED

@property
def VECTOR_DIMENSION(self) -> int:
    return settings.database.VECTOR_DIMENSION

# Export commonly used settings
__all__ = ["settings", "Settings"]