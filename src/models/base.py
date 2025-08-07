"""
Enhanced base model with async operations and utility methods.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import as_declarative, declared_attr

from src.database import Base

T = TypeVar("T", bound="AsyncBaseModel")


@as_declarative()
class AsyncBaseModel(Base):
    """Enhanced base model with async CRUD operations and utility methods."""

    __abstract__ = True

    # Common fields for all models
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower() + "s"

    # Async CRUD Operations
    @classmethod
    async def create(cls: type[T], db: AsyncSession, **kwargs: Any) -> T:
        """Create a new instance."""
        instance = cls(**kwargs)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    @classmethod
    async def get(cls: type[T], db: AsyncSession, id: int) -> Optional[T]:
        """Get instance by ID."""
        result = await db.execute(select(cls).where(cls.id == id))
        return result.scalar_one_or_none()

    @classmethod
    async def get_multi(
        cls: type[T],
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[T]:
        """Get multiple instances with pagination and filtering."""
        query = select(cls)

        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(cls, key):
                    query = query.where(getattr(cls, key) == value)

        # Apply ordering
        if order_by and hasattr(cls, order_by):
            query = query.order_by(getattr(cls, order_by))
        else:
            query = query.order_by(cls.id.desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @classmethod
    async def count(cls, db: AsyncSession, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count instances with optional filtering."""
        query = select(func.count(cls.id))

        if filters:
            for key, value in filters.items():
                if hasattr(cls, key):
                    query = query.where(getattr(cls, key) == value)

        result = await db.execute(query)
        return result.scalar() or 0

    async def update(self, db: AsyncSession, **kwargs: Any) -> None:
        """Update instance fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(self)

    @classmethod
    async def update_by_id(cls, db: AsyncSession, id: int, **kwargs: Any) -> bool:
        """Update instance by ID."""
        kwargs["updated_at"] = datetime.utcnow()

        result = await db.execute(update(cls).where(cls.id == id).values(**kwargs))
        await db.commit()
        return result.rowcount > 0

    async def delete(self, db: AsyncSession) -> None:
        """Delete this instance."""
        await db.delete(self)
        await db.flush()

    @classmethod
    async def delete_by_id(cls, db: AsyncSession, id: int) -> bool:
        """Delete instance by ID."""
        result = await db.execute(delete(cls).where(cls.id == id))
        await db.commit()
        return result.rowcount > 0

    @classmethod
    async def bulk_create(cls: type[T], db: AsyncSession, objects: List[Dict[str, Any]]) -> List[T]:
        """Bulk create multiple instances."""
        instances = [cls(**obj) for obj in objects]
        db.add_all(instances)
        await db.flush()

        # Refresh all instances to get IDs
        for instance in instances:
            await db.refresh(instance)

        return instances

    @classmethod
    async def exists(cls, db: AsyncSession, id: int) -> bool:
        """Check if instance exists by ID."""
        result = await db.execute(select(func.count(cls.id)).where(cls.id == id))
        count = result.scalar() or 0
        return count > 0

    # Utility methods
    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to dictionary."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def to_dict_with_relations(self, relations: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert instance to dictionary including specified relations."""
        result = self.to_dict()

        if relations:
            for relation in relations:
                if hasattr(self, relation):
                    relation_obj = getattr(self, relation)
                    if relation_obj:
                        if isinstance(relation_obj, list):
                            result[relation] = [
                                obj.to_dict() if hasattr(obj, "to_dict") else str(obj) for obj in relation_obj
                            ]
                        else:
                            result[relation] = (
                                relation_obj.to_dict() if hasattr(relation_obj, "to_dict") else str(relation_obj)
                            )

        return result

    @classmethod
    def from_dict(cls: type[T], data: Dict[str, Any]) -> T:
        """Create instance from dictionary."""
        # Filter out fields that don't exist on the model
        valid_fields = {key: value for key, value in data.items() if hasattr(cls, key)}
        return cls(**valid_fields)

    def __repr__(self) -> str:
        """String representation of the instance."""
        return f"<{self.__class__.__name__}(id={self.id})>"


# Pydantic models for API schemas
class BaseSchema(BaseModel):
    """Base Pydantic schema with common configuration."""

    class Config:
        from_attributes = True  # For Pydantic v2
        use_enum_values = True
        validate_assignment = True


class TimestampedSchema(BaseSchema):
    """Base schema with timestamp fields."""

    id: int
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Pagination parameters for API endpoints."""

    page: int = 1
    size: int = 10

    def get_offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model."""

    items: List[T]
    page: int
    size: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int) -> "PaginatedResponse[T]":
        """Create paginated response from data."""
        pages = (total + size - 1) // size if size > 0 else 0

        return cls(
            items=items, page=page, size=size, total=total, pages=pages, has_next=page < pages, has_prev=page > 1
        )
