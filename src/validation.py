"""
Validation utilities and decorators.
"""

import functools
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from src.exceptions import ValidationError as AppValidationError

T = TypeVar("T", bound=BaseModel)


def validate_model(model_class: Type[T], data: Dict[str, Any]) -> T:
    """Validate data against a Pydantic model."""
    try:
        return model_class.model_validate(data)
    except ValidationError as e:
        # Convert Pydantic validation errors to app validation error
        field_errors = {}
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            field_errors[field_path] = error["msg"]

        raise AppValidationError(message="Validation failed", details={"field_errors": field_errors})


def validate_request_body(model_class: Type[T]):
    """Decorator to validate request body against a Pydantic model."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the request body parameter
            for key, value in kwargs.items():
                if isinstance(value, dict):
                    try:
                        kwargs[key] = validate_model(model_class, value)
                        break
                    except AppValidationError:
                        raise

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class QueryParamsValidator:
    """Validator for query parameters."""

    @staticmethod
    def validate_pagination(
        page: Optional[int] = None, size: Optional[int] = None, max_size: int = 100
    ) -> Dict[str, int]:
        """Validate pagination parameters."""
        errors = {}

        if page is not None and page < 1:
            errors["page"] = "Page must be greater than 0"

        if size is not None and size < 1:
            errors["size"] = "Size must be greater than 0"

        if size is not None and size > max_size:
            errors["size"] = f"Size cannot exceed {max_size}"

        if errors:
            raise AppValidationError(message="Invalid pagination parameters", details={"field_errors": errors})

        return {"page": page or 1, "size": min(size or 20, max_size)}

    @staticmethod
    def validate_sort_params(
        sort_by: Optional[str] = None, sort_order: Optional[str] = None, allowed_fields: Optional[List[str]] = None
    ) -> Dict[str, Optional[str]]:
        """Validate sorting parameters."""
        errors = {}

        if sort_by and allowed_fields and sort_by not in allowed_fields:
            errors["sort_by"] = f"Sort field must be one of: {', '.join(allowed_fields)}"

        if sort_order and sort_order.lower() not in ["asc", "desc"]:
            errors["sort_order"] = "Sort order must be 'asc' or 'desc'"

        if errors:
            raise AppValidationError(message="Invalid sorting parameters", details={"field_errors": errors})

        return {"sort_by": sort_by, "sort_order": sort_order.lower() if sort_order else "desc"}


class FileValidator:
    """File validation utilities."""

    @staticmethod
    def validate_file_upload(
        filename: str,
        file_size: int,
        content_type: str,
        allowed_types: Optional[List[str]] = None,
        max_size_mb: Optional[float] = None,
    ) -> None:
        """Validate file upload parameters."""
        errors = {}

        # Validate filename
        if not filename or not filename.strip():
            errors["filename"] = "Filename is required"
        elif len(filename) > 255:
            errors["filename"] = "Filename is too long (max 255 characters)"

        # Validate file size
        if max_size_mb and file_size > (max_size_mb * 1024 * 1024):
            errors["file_size"] = f"File size exceeds {max_size_mb}MB limit"

        # Validate content type
        if allowed_types and content_type not in allowed_types:
            errors["content_type"] = f"File type not allowed. Allowed types: {', '.join(allowed_types)}"

        # Validate file extension
        if filename and "." in filename:
            extension = filename.lower().split(".")[-1]
            if allowed_types:
                allowed_extensions = [mime_type.split("/")[-1] for mime_type in allowed_types if "/" in mime_type]
                if allowed_extensions and extension not in allowed_extensions:
                    errors["filename"] = (
                        f"File extension not allowed. Allowed extensions: {', '.join(allowed_extensions)}"
                    )

        if errors:
            raise AppValidationError(message="File validation failed", details={"field_errors": errors})

    @staticmethod
    def get_file_type_from_extension(filename: str) -> str:
        """Get MIME type from file extension."""
        if not filename or "." not in filename:
            return "application/octet-stream"

        extension = filename.lower().split(".")[-1]

        mime_types = {
            "txt": "text/plain",
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "mp4": "video/mp4",
            "avi": "video/x-msvideo",
            "mov": "video/quicktime",
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "zip": "application/zip",
            "tar": "application/x-tar",
            "gz": "application/gzip",
            "json": "application/json",
            "xml": "application/xml",
            "csv": "text/csv",
        }

        return mime_types.get(extension, "application/octet-stream")


class BusinessRuleValidator:
    """Business rule validation utilities."""

    @staticmethod
    def validate_user_permissions(
        user_role: str,
        required_roles: List[str],
        resource_owner_id: Optional[int] = None,
        current_user_id: Optional[int] = None,
    ) -> None:
        """Validate user permissions for an action."""
        # Admin can do anything
        if user_role == "admin":
            return

        # Check if user has required role
        if user_role not in required_roles:
            raise AppValidationError(
                message="Insufficient permissions", details={"required_roles": required_roles, "user_role": user_role}
            )

        # Check resource ownership if applicable
        if resource_owner_id and current_user_id and resource_owner_id != current_user_id:
            raise AppValidationError(message="You can only access your own resources")

    @staticmethod
    def validate_business_hours(hour: int, allowed_hours: List[int]) -> None:
        """Validate operation within business hours."""
        if hour not in allowed_hours:
            raise AppValidationError(
                message=f"Operation only allowed during business hours: {', '.join(map(str, allowed_hours))}"
            )

    @staticmethod
    def validate_rate_limit(
        user_id: int, action: str, max_requests: int, time_window_minutes: int, current_count: int
    ) -> None:
        """Validate rate limiting for user actions."""
        if current_count >= max_requests:
            raise AppValidationError(
                message=f"Rate limit exceeded. Maximum {max_requests} {action} requests allowed per {time_window_minutes} minutes",
                details={
                    "action": action,
                    "max_requests": max_requests,
                    "time_window_minutes": time_window_minutes,
                    "current_count": current_count,
                },
            )


def validate_id_parameter(id_value: Any, parameter_name: str = "id") -> int:
    """Validate ID parameter from URL."""
    try:
        id_int = int(id_value)
        if id_int < 1:
            raise ValueError("ID must be positive")
        return id_int
    except (ValueError, TypeError):
        raise AppValidationError(
            message=f"Invalid {parameter_name} parameter. Must be a positive integer.",
            details={"parameter": parameter_name, "value": str(id_value)},
        )


def validate_enum_parameter(value: str, enum_values: List[str], parameter_name: str = "parameter") -> str:
    """Validate enum parameter."""
    if value not in enum_values:
        raise AppValidationError(
            message=f"Invalid {parameter_name}. Must be one of: {', '.join(enum_values)}",
            details={"parameter": parameter_name, "allowed_values": enum_values, "provided_value": value},
        )
    return value


def validate_date_range(
    start_date: Optional[str] = None, end_date: Optional[str] = None, date_format: str = "%Y-%m-%d"
) -> Dict[str, Optional[str]]:
    """Validate date range parameters."""
    from datetime import datetime

    errors = {}
    parsed_start = None
    parsed_end = None

    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, date_format)
        except ValueError:
            errors["start_date"] = f"Invalid date format. Expected: {date_format}"

    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, date_format)
        except ValueError:
            errors["end_date"] = f"Invalid date format. Expected: {date_format}"

    if parsed_start and parsed_end and parsed_start > parsed_end:
        errors["date_range"] = "Start date cannot be after end date"

    if errors:
        raise AppValidationError(message="Invalid date parameters", details={"field_errors": errors})

    return {"start_date": start_date, "end_date": end_date}
