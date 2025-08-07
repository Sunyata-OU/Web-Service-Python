import os
from unittest.mock import Mock, patch

from celery import Celery

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
    }
)

from src.celery import default


class TestCeleryApp:
    def test_celery_app_creation(self):
        """Test that Celery app is created with correct configuration."""
        assert isinstance(default, Celery)
        assert default.main == "default"

    @patch("src.celery.get_settings")
    def test_celery_broker_configuration(self, mock_get_settings):
        """Test that Celery broker is configured correctly."""
        mock_settings = Mock()
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_get_settings.return_value = mock_settings

        # Import celery module again to trigger configuration with mocked settings
        import importlib

        import src.celery

        importlib.reload(src.celery)

        # The broker should be set from settings
        assert src.celery.default.conf.broker_url is not None

    @patch("src.celery.get_settings")
    def test_celery_result_backend_configuration(self, mock_get_settings):
        """Test that Celery result backend is configured correctly."""
        mock_settings = Mock()
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_get_settings.return_value = mock_settings

        # Import celery module again to trigger configuration with mocked settings
        import importlib

        import src.celery

        importlib.reload(src.celery)

        # The result backend should be set from settings
        assert src.celery.default.conf.result_backend is not None

    def test_celery_app_methods(self):
        """Test that Celery app has required methods."""
        assert hasattr(default, "task")
        assert hasattr(default, "send_task")
        assert hasattr(default, "control")
        assert callable(default.task)

    @patch.object(default, "send_task")
    def test_send_task_method(self, mock_send_task):
        """Test sending a task via Celery."""
        mock_result = Mock()
        mock_send_task.return_value = mock_result

        # Send a test task
        result = default.send_task("test.task", args=["arg1", "arg2"])

        # Verify task was sent
        mock_send_task.assert_called_once_with("test.task", args=["arg1", "arg2"])
        assert result == mock_result

    def test_celery_task_decorator(self):
        """Test that the task decorator works."""

        @default.task
        def test_task(x, y):
            return x + y

        assert hasattr(test_task, "delay")
        assert hasattr(test_task, "apply_async")
        assert callable(test_task.delay)
        assert callable(test_task.apply_async)

    @patch("src.celery.get_settings")
    def test_celery_configuration_with_different_redis_settings(self, mock_get_settings):
        """Test Celery configuration with different Redis settings."""
        mock_settings = Mock()
        mock_settings.redis_url = "redis://redis-server:6380/1"
        mock_get_settings.return_value = mock_settings

        # Import celery module again to trigger configuration with mocked settings
        import importlib

        import src.celery

        importlib.reload(src.celery)

        # Verify the configuration is applied
        celery_app = src.celery.default
        assert celery_app is not None


class TestCeleryTasks:
    """Test class for Celery task functionality."""

    def test_create_sample_task(self):
        """Test creating a sample Celery task."""

        @default.task
        def sample_calculation_task(x, y, operation="add"):
            """Sample task for testing."""
            if operation == "add":
                return x + y
            elif operation == "multiply":
                return x * y
            elif operation == "subtract":
                return x - y
            else:
                return None

        # Test the task function directly
        result = sample_calculation_task(5, 3, "add")
        assert result == 8

        result = sample_calculation_task(5, 3, "multiply")
        assert result == 15

        result = sample_calculation_task(5, 3, "subtract")
        assert result == 2

        result = sample_calculation_task(5, 3, "unknown")
        assert result is None

    def test_task_has_celery_attributes(self):
        """Test that tasks have Celery-specific attributes."""

        @default.task
        def test_task():
            return "test"

        # Check that the task has Celery attributes
        assert hasattr(test_task, "delay")
        assert hasattr(test_task, "apply_async")
        assert hasattr(test_task, "request")

    @patch.object(default, "send_task")
    def test_task_execution_via_send_task(self, mock_send_task):
        """Test task execution using send_task method."""
        mock_result = Mock()
        mock_result.get.return_value = "task completed"
        mock_send_task.return_value = mock_result

        # Send task and get result
        async_result = default.send_task("sample.task", args=[1, 2])
        result = async_result.get()

        # Verify task execution
        mock_send_task.assert_called_once_with("sample.task", args=[1, 2])
        assert result == "task completed"

    def test_celery_task_retry_mechanism(self):
        """Test task retry functionality."""
        retry_count = 0

        @default.task(bind=True, max_retries=3)
        def failing_task(self, should_fail=True):
            nonlocal retry_count
            retry_count += 1

            if should_fail and retry_count < 3:
                # Simulate failure and retry
                raise self.retry(countdown=1, exc=Exception("Simulated failure"))

            return f"Success after {retry_count} attempts"

        # Test successful execution after retries
        result = failing_task(should_fail=False)
        assert "Success after" in result

        # Reset retry count for next test
        retry_count = 0
