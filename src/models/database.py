"""
Legacy database module - DEPRECATED
This module is maintained for backward compatibility only.
Use src.database and src.models.base for new async patterns.
"""

from datetime import datetime
from typing import Any, Generator
import warnings

from sqlalchemy import Column, DateTime, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings

# Show deprecation warning
warnings.warn(
    "src.models.database is deprecated. Use src.database and src.models.base for async patterns.",
    DeprecationWarning,
    stacklevel=2
)

settings = get_settings()

# Legacy sync engine - kept for backward compatibility
engine = create_engine(settings.database_url.replace('+asyncpg', ''))  # Remove async driver
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import Base from the new async database
try:
    from src.database import Base
except ImportError:
    # Fallback for backward compatibility
    Base = declarative_base()


def get_db() -> Generator[Session, Any, None]:
    """Legacy database session generator - use get_async_db for new code."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BaseModel(Base):
    """Legacy base model - DEPRECATED. Use AsyncBaseModel from src.models.base."""
    
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self, db):
        """Save instance to database."""
        db.add(self)
        db.commit()
        db.refresh(self)
        return self

    def delete(self, db) -> None:
        """Delete instance from database."""
        db.delete(self)
        db.commit()

    def update(self, db):
        """Update instance in database."""
        db.commit()
        db.refresh(self)
        return self

    @classmethod
    def get(cls, id, db) -> Any:
        """Get instance by ID."""
        return db.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_all(cls, db) -> Any:
        """Get all instances."""
        return db.query(cls).all()

    @classmethod
    def get_by(cls, db, **kwargs) -> Any:
        """Get instances by filter criteria."""
        return db.query(cls).filter_by(**kwargs).all()

    @classmethod
    def get_first(cls, db, **kwargs) -> Any:
        """Get first instance by filter criteria."""
        return db.query(cls).filter_by(**kwargs).first()

    @classmethod
    def create(cls, db, **kwargs):
        """Create new instance."""
        instance = cls(**kwargs)
        db.add(instance)
        db.commit()
        return instance

    @classmethod
    def bulk_create(cls, db, items) -> Any:
        """Bulk create instances."""
        db.bulk_save_objects(items)
        db.commit()
        return items
