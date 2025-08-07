from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with Pydantic validation and environment loading."""
    
    model_config = SettingsConfigDict(
        env_file=[".env", ".env.local", ".env.prod"],
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Application settings
    environment: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers_count: int = Field(default=1, description="Number of worker processes")
    
    # Security settings
    allowed_hosts: Optional[List[str]] = Field(default=None, description="Allowed host names")
    cors_origins: Optional[List[str]] = Field(default=None, description="CORS allowed origins")
    
    # Database settings
    postgres_user: str = Field(description="PostgreSQL username")
    postgres_password: str = Field(description="PostgreSQL password")
    postgres_server: str = Field(default="localhost", description="PostgreSQL server")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="webapp", description="PostgreSQL database name")
    
    @computed_field
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @computed_field  
    @property
    def async_database_url(self) -> str:
        """Construct async PostgreSQL database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )
    
    # Redis settings
    redis_host: str = Field(default="localhost", description="Redis server host")
    redis_port: int = Field(default=6379, description="Redis server port")
    redis_db: int = Field(default=0, description="Redis database number")
    
    @computed_field
    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # S3/MinIO settings
    s3_host: str = Field(default="http://127.0.0.1", description="S3 host URL")
    s3_port: int = Field(default=9002, description="S3 port")
    s3_access_key_id: str = Field(description="S3 access key ID")
    s3_access_key: str = Field(description="S3 secret access key")
    s3_bucket: str = Field(default="uploads", description="Default S3 bucket name")
    
    @computed_field
    @property
    def s3_endpoint(self) -> str:
        """Construct S3 endpoint URL."""
        return f"{self.s3_host}:{self.s3_port}"
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_path: str = Field(default="./logs", description="Log file directory path")
    
    # Celery settings
    celery_broker_url: Optional[str] = Field(default=None, description="Celery broker URL")
    celery_result_backend: Optional[str] = Field(default=None, description="Celery result backend")
    
    @computed_field
    @property
    def celery_broker(self) -> str:
        """Get Celery broker URL, default to Redis."""
        return self.celery_broker_url or self.redis_url
    
    @computed_field
    @property  
    def celery_backend(self) -> str:
        """Get Celery result backend, default to Redis."""
        return self.celery_result_backend or self.redis_url
    
    # Authentication settings
    secret_key: str = Field(
        default="changeme-super-secret-key-in-production",
        description="Secret key for JWT tokens"
    )
    algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(
        default=30, 
        description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=30,
        description="Refresh token expiration in days"
    )
    
    # Password policy
    password_min_length: int = Field(default=8, description="Minimum password length")
    password_require_uppercase: bool = Field(
        default=False, 
        description="Require uppercase in passwords"
    )
    password_require_lowercase: bool = Field(
        default=False,
        description="Require lowercase in passwords"
    )
    password_require_numbers: bool = Field(
        default=True,
        description="Require numbers in passwords"
    )
    password_require_symbols: bool = Field(
        default=False,
        description="Require symbols in passwords"
    )
    
    # Account lockout
    max_login_attempts: int = Field(default=5, description="Max failed login attempts")
    lockout_duration_minutes: int = Field(default=30, description="Account lockout duration")
    
    # Feature flags
    enable_docs: bool = Field(default=True, description="Enable API documentation")
    enable_metrics: bool = Field(default=False, description="Enable metrics collection")
    enable_registration: bool = Field(default=True, description="Allow user registration")
    enable_email_verification: bool = Field(default=False, description="Require email verification")


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
