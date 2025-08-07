"""
Test configuration and fixtures.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment variables BEFORE importing anything else
os.environ.update(
    {
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_pass",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test_db",
        "S3_ACCESS_KEY_ID": "test_key",
        "S3_ACCESS_KEY": "test_secret",
        "S3_BUCKET": "test-bucket",
        "ENVIRONMENT": "testing",
        "DEBUG": "false",
        "LOG_LEVEL": "WARNING",
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "1",  # Use different DB for testing
    }
)

from src.database import Base, get_async_db
from src.main import create_app
from src.models.s3 import S3Object
from src.models.user import APIKey, User


# Test database setup
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_test_engine():
    """Create async test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def sync_test_engine():
    """Create sync test database engine for legacy tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
async def async_db_session(async_test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for testing."""
    async_session_maker = async_sessionmaker(async_test_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture
def sync_db_session(sync_test_engine) -> Generator:
    """Create sync database session for legacy tests."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_test_engine)

    connection = sync_test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# Application setup
@pytest.fixture
def app():
    """Create test FastAPI application."""
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    """Create test client for sync tests."""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# Database dependency overrides
@pytest.fixture
def override_async_db(async_db_session):
    """Override async database dependency."""

    async def _override_get_async_db():
        yield async_db_session

    return _override_get_async_db


# User fixtures
@pytest.fixture
async def test_user(async_db_session: AsyncSession) -> User:
    """Create test user."""
    user = await User.create_user(
        db=async_db_session,
        email="test@example.com",
        username="testuser",
        password="testpass123",
        full_name="Test User",
    )
    await async_db_session.commit()
    return user


@pytest.fixture
async def admin_user(async_db_session: AsyncSession) -> User:
    """Create test admin user."""
    from src.auth import UserRole

    user = await User.create_user(
        db=async_db_session,
        email="admin@example.com",
        username="admin",
        password="adminpass123",
        full_name="Admin User",
        role=UserRole.ADMIN,
    )
    await async_db_session.commit()
    return user


@pytest.fixture
def user_token(test_user: User) -> str:
    """Create access token for test user."""
    from src.auth import create_access_token

    return create_access_token(subject=test_user.email, user_id=test_user.id, role=test_user.role)


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Create access token for admin user."""
    from src.auth import create_access_token

    return create_access_token(subject=admin_user.email, user_id=admin_user.id, role=admin_user.role)


@pytest.fixture
async def test_api_key(async_db_session: AsyncSession, test_user: User) -> tuple[APIKey, str]:
    """Create test API key."""
    api_key, raw_key = await APIKey.create_for_user(db=async_db_session, user_id=test_user.id, name="Test API Key")
    await async_db_session.commit()
    return api_key, raw_key


# S3 Object fixtures
@pytest.fixture
async def test_s3_object(async_db_session: AsyncSession) -> S3Object:
    """Create test S3 object."""
    s3_obj = await S3Object.create(
        async_db_session,
        bucket_name="test-bucket",
        object_name="test-file.txt",
        file_name="test-file.txt",
        file_type="text/plain",
        file_size="123",
    )
    await async_db_session.commit()
    return s3_obj


# Mock fixtures
@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    with patch("src.cache.redis") as mock_redis_module:
        mock_client = Mock()
        mock_client.from_url.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_client.set.return_value = True
        mock_client.delete.return_value = 1
        mock_client.keys.return_value = []
        mock_client.exists.return_value = False
        mock_client.ttl.return_value = -1
        mock_client.incr.return_value = 1

        mock_redis_module.from_url = Mock(return_value=mock_client)
        yield mock_client


@pytest.fixture
def mock_s3_client():
    """Mock S3/MinIO client."""
    mock_client = Mock()
    mock_client.upload_fileobj.return_value = None
    mock_client.download_file.return_value = None
    mock_client.generate_presigned_url.return_value = "http://localhost:9000/test-bucket/test-file.txt"
    return mock_client


@pytest.fixture
def mock_celery_task():
    """Mock Celery task."""
    mock_task = AsyncMock()
    mock_task.delay.return_value = Mock(id="test-task-id")
    mock_task.apply_async.return_value = Mock(id="test-task-id")
    return mock_task


# File upload fixtures
@pytest.fixture
def sample_text_file():
    """Sample text file for testing."""
    from io import BytesIO

    content = b"This is a test file content"
    return BytesIO(content)


@pytest.fixture
def sample_image_file():
    """Sample image file for testing."""
    from io import BytesIO

    # Minimal PNG file header
    content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
    return BytesIO(content)


@pytest.fixture
def upload_file_data(sample_text_file):
    """File upload data for multipart form."""
    return {"file": ("test.txt", sample_text_file, "text/plain")}


# Authentication helpers
@pytest.fixture
def auth_headers(user_token):
    """Authentication headers for requests."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_auth_headers(admin_token):
    """Admin authentication headers for requests."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def api_key_headers(test_api_key):
    """API key authentication headers."""
    _, raw_key = test_api_key
    return {"Authorization": f"Bearer {raw_key}"}


# Application dependency overrides for testing
@pytest.fixture(autouse=True)
def override_dependencies(app, override_async_db):
    """Override app dependencies for testing."""
    app.dependency_overrides[get_async_db] = override_async_db
    yield
    app.dependency_overrides.clear()


# Test data factories
class UserFactory:
    """Factory for creating test users."""

    @staticmethod
    async def create(
        db: AsyncSession, email: str = None, username: str = None, password: str = "testpass123", **kwargs
    ) -> User:
        """Create user with unique email/username if not provided."""
        import uuid

        suffix = str(uuid.uuid4())[:8]

        return await User.create_user(
            db=db,
            email=email or f"user-{suffix}@example.com",
            username=username or f"user{suffix}",
            password=password,
            **kwargs,
        )


class S3ObjectFactory:
    """Factory for creating test S3 objects."""

    @staticmethod
    async def create(db: AsyncSession, bucket_name: str = "test-bucket", object_name: str = None, **kwargs) -> S3Object:
        """Create S3 object with unique object name if not provided."""
        import uuid

        return await S3Object.create(
            db,
            bucket_name=bucket_name,
            object_name=object_name or f"test-{uuid.uuid4().hex[:8]}.txt",
            file_name=kwargs.get("file_name", "test.txt"),
            file_type=kwargs.get("file_type", "text/plain"),
            **kwargs,
        )


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment."""
    # Disable external connections during testing
    os.environ["TESTING"] = "true"
    yield
    # Cleanup if needed
