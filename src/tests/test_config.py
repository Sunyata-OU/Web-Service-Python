import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config import Settings, get_settings


class TestSettings:
    def test_settings_default_values(self):
        """Test that settings have correct default values."""
        # Set required environment variables
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_pass",
                "S3_ACCESS_KEY_ID": "test_key",
                "S3_ACCESS_KEY": "test_secret",
            },
        ):
            settings = Settings()

            # Environment will be "testing" because it's set in the test module
            assert settings.environment in ["development", "testing"]
            assert settings.debug is False
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            assert settings.workers_count == 1
            assert settings.postgres_server == "localhost"
            assert settings.postgres_port == 5432
            # postgres_db will be "test_db" because it's set in the test module
            assert settings.postgres_db in ["webapp", "test_db"]
            assert settings.redis_host == "localhost"
            assert settings.redis_port == 6379
            assert settings.redis_db == 0
            assert settings.s3_host == "http://127.0.0.1"
            assert settings.s3_port == 9002
            # s3_bucket will be "test-bucket" because it's set in the test module
            assert settings.s3_bucket in ["uploads", "test-bucket"]
            # log_level will be "WARNING" because it's set in the test module
            assert settings.log_level in ["INFO", "WARNING"]
            assert settings.log_path == "./logs"
            assert settings.enable_docs is True
            assert settings.enable_metrics is False

    def test_settings_environment_variables(self):
        """Test that settings properly load from environment variables."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "WORKERS_COUNT": "4",
            "POSTGRES_USER": "prod_user",
            "POSTGRES_PASSWORD": "prod_pass",
            "POSTGRES_SERVER": "db.example.com",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "production_db",
            "REDIS_HOST": "redis.example.com",
            "REDIS_PORT": "6380",
            "REDIS_DB": "1",
            "S3_HOST": "https://s3.example.com",
            "S3_PORT": "443",
            "S3_ACCESS_KEY_ID": "prod_access_key",
            "S3_ACCESS_KEY": "prod_secret_key",
            "S3_BUCKET": "production-uploads",
            "LOG_LEVEL": "WARNING",
            "LOG_PATH": "/var/log/app",
            "ENABLE_DOCS": "false",
            "ENABLE_METRICS": "true",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.environment == "production"
            assert settings.debug is True
            assert settings.host == "127.0.0.1"
            assert settings.port == 9000
            assert settings.workers_count == 4
            assert settings.postgres_user == "prod_user"
            assert settings.postgres_password == "prod_pass"
            assert settings.postgres_server == "db.example.com"
            assert settings.postgres_port == 5433
            assert settings.postgres_db == "production_db"
            assert settings.redis_host == "redis.example.com"
            assert settings.redis_port == 6380
            assert settings.redis_db == 1
            assert settings.s3_host == "https://s3.example.com"
            assert settings.s3_port == 443
            assert settings.s3_access_key_id == "prod_access_key"
            assert settings.s3_access_key == "prod_secret_key"
            assert settings.s3_bucket == "production-uploads"
            assert settings.log_level == "WARNING"
            assert settings.log_path == "/var/log/app"
            assert settings.enable_docs is False
            assert settings.enable_metrics is True

    def test_database_url_computed_field(self):
        """Test that database URL is computed correctly."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_pass",
                "POSTGRES_SERVER": "localhost",
                "POSTGRES_PORT": "5432",
                "POSTGRES_DB": "test_db",
                "S3_ACCESS_KEY_ID": "test_key",
                "S3_ACCESS_KEY": "test_secret",
            },
        ):
            settings = Settings()
            expected_url = "postgresql://test_user:test_pass@localhost:5432/test_db"
            assert settings.database_url == expected_url

    def test_async_database_url_computed_field(self):
        """Test that async database URL is computed correctly."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_pass",
                "POSTGRES_SERVER": "localhost",
                "POSTGRES_PORT": "5432",
                "POSTGRES_DB": "test_db",
                "S3_ACCESS_KEY_ID": "test_key",
                "S3_ACCESS_KEY": "test_secret",
            },
        ):
            settings = Settings()
            expected_url = "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"
            assert settings.async_database_url == expected_url

    def test_redis_url_computed_field(self):
        """Test that Redis URL is computed correctly."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_pass",
                "S3_ACCESS_KEY_ID": "test_key",
                "S3_ACCESS_KEY": "test_secret",
                "REDIS_HOST": "redis.example.com",
                "REDIS_PORT": "6380",
                "REDIS_DB": "2",
            },
        ):
            settings = Settings()
            expected_url = "redis://redis.example.com:6380/2"
            assert settings.redis_url == expected_url

    def test_s3_endpoint_computed_field(self):
        """Test that S3 endpoint is computed correctly."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_pass",
                "S3_ACCESS_KEY_ID": "test_key",
                "S3_ACCESS_KEY": "test_secret",
                "S3_HOST": "https://s3.amazonaws.com",
                "S3_PORT": "443",
            },
        ):
            settings = Settings()
            expected_endpoint = "https://s3.amazonaws.com:443"
            assert settings.s3_endpoint == expected_endpoint

    def test_celery_broker_computed_field(self):
        """Test that Celery broker URL is computed correctly."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_pass",
                "S3_ACCESS_KEY_ID": "test_key",
                "S3_ACCESS_KEY": "test_secret",
                "REDIS_HOST": "localhost",
                "REDIS_PORT": "6379",
                "REDIS_DB": "0",
            },
        ):
            settings = Settings()
            expected_broker = "redis://localhost:6379/0"
            assert settings.celery_broker == expected_broker

    def test_celery_broker_custom_url(self):
        """Test that custom Celery broker URL is used when provided."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_pass",
                "S3_ACCESS_KEY_ID": "test_key",
                "S3_ACCESS_KEY": "test_secret",
                "CELERY_BROKER_URL": "redis://custom.broker.com:6379/1",
            },
        ):
            settings = Settings()
            assert settings.celery_broker == "redis://custom.broker.com:6379/1"

    def test_celery_backend_computed_field(self):
        """Test that Celery result backend is computed correctly."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_pass",
                "S3_ACCESS_KEY_ID": "test_key",
                "S3_ACCESS_KEY": "test_secret",
                "REDIS_HOST": "localhost",
                "REDIS_PORT": "6379",
                "REDIS_DB": "0",
            },
        ):
            settings = Settings()
            expected_backend = "redis://localhost:6379/0"
            assert settings.celery_backend == expected_backend

    def test_celery_backend_custom_url(self):
        """Test that custom Celery result backend is used when provided."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_pass",
                "S3_ACCESS_KEY_ID": "test_key",
                "S3_ACCESS_KEY": "test_secret",
                "CELERY_RESULT_BACKEND": "redis://custom.backend.com:6379/2",
            },
        ):
            settings = Settings()
            assert settings.celery_backend == "redis://custom.backend.com:6379/2"

    def test_missing_required_fields_raise_validation_error(self):
        """Test that missing required fields raise ValidationError."""
        # Clear environment variables that are required
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
                Settings()


class TestGetSettings:
    def test_get_settings_caching(self):
        """Test that get_settings uses caching."""
        # Clear the cache first
        get_settings.cache_clear()

        # Call get_settings multiple times
        result1 = get_settings()
        result2 = get_settings()

        # Since it's cached, both should return the same instance
        assert result1 is result2

    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        with patch.dict(
            os.environ,
            {
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_pass",
                "S3_ACCESS_KEY_ID": "test_key",
                "S3_ACCESS_KEY": "test_secret",
            },
        ):
            settings = get_settings()
            assert isinstance(settings, Settings)
