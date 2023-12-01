from datetime import datetime
from typing import Any, Generator

from sqlalchemy import Column, DateTime, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from src.config import Settings

engine = create_engine(Settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, Any, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BaseModel(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self, db):
        db.add(self)
        db.commit()
        db.refresh(self)
        return self

    def delete(self, db) -> None:
        db.delete(self)
        db.commit()

    def update(self, db):
        db.commit()
        db.refresh(self)
        return self

    @classmethod
    def get(cls, id, db) -> Any:
        return db.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_all(cls, db) -> Any:
        return db.query(cls).all()

    @classmethod
    def get_by(cls, db, **kwargs) -> Any:
        return db.query(cls).filter_by(**kwargs).all()

    @classmethod
    def get_first(cls, db, **kwargs) -> Any:
        return db.query(cls).filter_by(**kwargs).first()

    @classmethod
    def create(cls, db, **kwargs):
        instance = cls(**kwargs)
        db.add(instance)
        db.commit()
        return instance

    @classmethod
    def bulk_create(cls, db, items) -> Any:
        db.bulk_save_objects(items)
        db.commit()
        return items
