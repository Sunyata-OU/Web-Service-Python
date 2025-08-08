"""
Custom exceptions and error handling for the application.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class BaseAppException(Exception):
    """Base exception for application-specific errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseAppException):
    """Validation failed."""

    pass


class NotFoundError(BaseAppException):
    """Resource not found."""

    pass


class DuplicateError(BaseAppException):
    """Duplicate resource."""

    pass


class PermissionDeniedError(BaseAppException):
    """Permission denied."""

    pass


class ConfigurationError(BaseAppException):
    """Configuration error."""

    pass


class DatabaseError(BaseAppException):
    """Database operation error."""

    pass


class StorageError(BaseAppException):
    """File storage error."""

    pass


class ExternalServiceError(BaseAppException):
    """External service error."""

    pass


# HTTP Exception classes that map to proper HTTP status codes
class BadRequestException(HTTPException):
    """400 Bad Request"""

    def __init__(self, detail: str = "Bad request", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, headers=headers)


class UnauthorizedException(HTTPException):
    """401 Unauthorized"""

    def __init__(self, detail: str = "Unauthorized", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=headers)


class ForbiddenException(HTTPException):
    """403 Forbidden"""

    def __init__(self, detail: str = "Forbidden", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail, headers=headers)


class NotFoundException(HTTPException):
    """404 Not Found"""

    def __init__(self, detail: str = "Not found", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, headers=headers)


class ConflictException(HTTPException):
    """409 Conflict"""

    def __init__(self, detail: str = "Conflict", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail, headers=headers)


class UnprocessableEntityException(HTTPException):
    """422 Unprocessable Entity"""

    def __init__(self, detail: str = "Unprocessable entity", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail, headers=headers)


class TooManyRequestsException(HTTPException):
    """429 Too Many Requests"""

    def __init__(self, detail: str = "Too many requests", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail, headers=headers)


class InternalServerErrorException(HTTPException):
    """500 Internal Server Error"""

    def __init__(self, detail: str = "Internal server error", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail, headers=headers)


class ServiceUnavailableException(HTTPException):
    """503 Service Unavailable"""

    def __init__(self, detail: str = "Service unavailable", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail, headers=headers)


# Error response models
class ErrorDetail:
    """Structured error detail."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.field = field
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"message": self.message}

        if self.error_code:
            result["error_code"] = self.error_code
        if self.field:
            result["field"] = self.field
        if self.details:
            result["details"] = self.details

        return result


class ErrorResponse:
    """Structured error response."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        errors: Optional[list[ErrorDetail]] = None,
        request_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.errors = errors or []
        self.request_id = request_id
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        errors_list = []
        for error in self.errors:
            if hasattr(error, "to_dict"):
                errors_list.append(error.to_dict())
            else:
                errors_list.append(error)  # Already a dict
        result = {"message": self.message, "errors": errors_list}

        if self.error_code:
            result["error_code"] = self.error_code
        if self.request_id:
            result["request_id"] = self.request_id
        if self.timestamp:
            result["timestamp"] = self.timestamp

        return result


# Exception mapping functions
def map_app_exception_to_http(exc: BaseAppException) -> HTTPException:
    """Map application exception to HTTP exception."""

    mapping = {
        ValidationError: BadRequestException,
        NotFoundError: NotFoundException,
        DuplicateError: ConflictException,
        PermissionDeniedError: ForbiddenException,
        ConfigurationError: InternalServerErrorException,
        DatabaseError: InternalServerErrorException,
        StorageError: InternalServerErrorException,
        ExternalServiceError: ServiceUnavailableException,
    }

    exception_class = mapping.get(type(exc), InternalServerErrorException)
    return exception_class(detail=exc.message)


def create_error_response(
    message: str,
    error_code: Optional[str] = None,
    field_errors: Optional[Dict[str, str]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a structured error response."""
    from datetime import datetime

    errors = []
    if field_errors:
        errors = [ErrorDetail(message=msg, field=field).to_dict() for field, msg in field_errors.items()]

    error_response = ErrorResponse(
        message=message,
        error_code=error_code,
        errors=errors,
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat(),
    )

    return error_response.to_dict()


# Validation helper functions
def validate_required_fields(data: Dict[str, Any], required_fields: list[str]) -> None:
    """Validate that required fields are present."""
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]

    if missing_fields:
        raise ValidationError(message="Missing required fields", details={"missing_fields": missing_fields})


def validate_field_length(
    value: str, field_name: str, min_length: Optional[int] = None, max_length: Optional[int] = None
) -> None:
    """Validate field length."""
    if min_length and len(value) < min_length:
        raise ValidationError(message=f"{field_name} must be at least {min_length} characters long")

    if max_length and len(value) > max_length:
        raise ValidationError(message=f"{field_name} must be at most {max_length} characters long")


def validate_email_format(email: str) -> None:
    """Validate email format."""
    import re

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        raise ValidationError(message="Invalid email format")


def validate_password_strength(password: str) -> None:
    """Validate password strength."""
    from src.config import get_settings

    settings = get_settings()
    errors = []

    if len(password) < settings.password_min_length:
        errors.append(f"Password must be at least {settings.password_min_length} characters long")

    if settings.password_require_uppercase and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if settings.password_require_lowercase and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if settings.password_require_numbers and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")

    if settings.password_require_symbols and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")

    if errors:
        raise ValidationError(message="Password does not meet requirements", details={"requirements": errors})


# Database operation helpers
async def handle_database_errors(operation_name: str):
    """Context manager to handle database errors."""
    from contextlib import asynccontextmanager

    from sqlalchemy.exc import IntegrityError, SQLAlchemyError

    @asynccontextmanager
    async def _handler():
        try:
            yield
        except IntegrityError as e:
            # Handle unique constraint violations
            if "unique constraint" in str(e).lower():
                raise DuplicateError(
                    message="Resource already exists", details={"operation": operation_name, "original_error": str(e)}
                )
            else:
                raise DatabaseError(
                    message=f"Database integrity error in {operation_name}", details={"original_error": str(e)}
                )
        except SQLAlchemyError as e:
            raise DatabaseError(message=f"Database error in {operation_name}", details={"original_error": str(e)})
        except Exception as e:
            raise DatabaseError(message=f"Unexpected error in {operation_name}", details={"original_error": str(e)})

    return _handler()


# File validation helpers
def validate_file_type(filename: str, allowed_extensions: list[str]) -> None:
    """Validate file type by extension."""
    if not filename:
        raise ValidationError(message="Filename is required")

    extension = filename.lower().split(".")[-1] if "." in filename else ""

    if extension not in [ext.lower() for ext in allowed_extensions]:
        raise ValidationError(
            message=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}",
            details={"allowed_extensions": allowed_extensions, "provided_extension": extension},
        )


def validate_file_size(file_size: int, max_size_bytes: int) -> None:
    """Validate file size."""
    if file_size > max_size_bytes:
        max_size_mb = max_size_bytes / (1024 * 1024)
        raise ValidationError(
            message=f"File size exceeds limit of {max_size_mb:.1f}MB",
            details={"max_size_bytes": max_size_bytes, "provided_size_bytes": file_size},
        )
