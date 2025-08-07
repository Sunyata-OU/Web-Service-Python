import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from src.config import get_settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        # Basic log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields from record
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "url"):
            log_data["url"] = record.url

        if hasattr(record, "method"):
            log_data["method"] = record.method

        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code

        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        if hasattr(record, "error_code"):
            log_data["error_code"] = record.error_code

        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "exc_info",
                "exc_text",
                "stack_info",
            ] and not key.startswith("_"):
                if key not in log_data:
                    log_data[key] = value

        # Format as JSON-like string for readability
        formatted_parts = []
        for key, value in log_data.items():
            formatted_parts.append(f"{key}={value}")

        return " | ".join(formatted_parts)


class ApplicationLogger:
    """Enhanced application logger with structured logging."""

    def __init__(self, name: str = "web-service"):
        self.settings = get_settings()
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """Set up logger with handlers and formatting."""
        self.logger.setLevel(getattr(logging, self.settings.log_level.upper()))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Ensure log directory exists
        if not os.path.exists(self.settings.log_path):
            try:
                os.makedirs(self.settings.log_path, exist_ok=True)
            except OSError:
                self.settings.log_path = "./logs/"
                os.makedirs(self.settings.log_path, exist_ok=True)

        # File handler with rotation
        log_file = os.path.join(self.settings.log_path, "application.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Error file handler for errors only
        error_log_file = os.path.join(self.settings.log_path, "errors.log")
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)

        # Use structured formatter for all handlers
        formatter = StructuredFormatter()
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.addHandler(error_handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

    def debug(self, message: str, **kwargs):
        """Log debug message with extra data."""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """Log info message with extra data."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with extra data."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with extra data."""
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message with extra data."""
        self.logger.critical(message, extra=kwargs)

    def log_request(
        self,
        method: str,
        url: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[int] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ):
        """Log HTTP request with structured data."""
        level = logging.INFO
        message = f"{method} {url}"

        if status_code >= 400:
            level = logging.WARNING if status_code < 500 else logging.ERROR
            message = f"{method} {url} - {status_code}"

        extra_data = {
            "method": method,
            "url": url,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "type": "http_request",
        }

        if user_id:
            extra_data["user_id"] = user_id

        if request_id:
            extra_data["request_id"] = request_id

        extra_data.update(kwargs)

        self.logger.log(level, message, extra=extra_data)

    def log_database_operation(
        self,
        operation: str,
        table: str,
        duration_ms: float,
        success: bool = True,
        affected_rows: Optional[int] = None,
        **kwargs,
    ):
        """Log database operation with structured data."""
        level = logging.DEBUG if success else logging.ERROR
        message = f"DB {operation} on {table}"

        if not success:
            message += " FAILED"

        extra_data = {
            "operation": operation,
            "table": table,
            "duration_ms": round(duration_ms, 2),
            "success": success,
            "type": "database_operation",
        }

        if affected_rows is not None:
            extra_data["affected_rows"] = affected_rows

        extra_data.update(kwargs)

        self.logger.log(level, message, extra=extra_data)

    def log_business_event(
        self,
        event: str,
        user_id: Optional[int] = None,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Log business event with structured data."""
        message = f"Business event: {event}"

        extra_data = {"event": event, "type": "business_event"}

        if user_id:
            extra_data["user_id"] = user_id

        if resource_id:
            extra_data["resource_id"] = resource_id

        if details:
            extra_data["details"] = details

        extra_data.update(kwargs)

        self.logger.info(message, extra=extra_data)

    def log_security_event(
        self,
        event: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: str = "medium",
        **kwargs,
    ):
        """Log security event with structured data."""
        level = logging.WARNING if severity == "medium" else logging.ERROR
        message = f"Security event: {event}"

        extra_data = {"event": event, "severity": severity, "type": "security_event"}

        if user_id:
            extra_data["user_id"] = user_id

        if ip_address:
            extra_data["ip_address"] = ip_address

        if user_agent:
            extra_data["user_agent"] = user_agent

        extra_data.update(kwargs)

        self.logger.log(level, message, extra=extra_data)


# Create global logger instance
logger = ApplicationLogger()


# For backward compatibility
def setup_logger():
    """Legacy function - logger is now automatically set up."""
    return logger.logger
