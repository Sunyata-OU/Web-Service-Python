from typing import Optional
from sqlalchemy import Column, String, Index
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.models.base import AsyncBaseModel, BaseSchema, TimestampedSchema
from src.s3 import get_object_url


class S3Object(AsyncBaseModel):
    __tablename__ = "s3_objects"

    bucket_name = Column(String(255), nullable=False, index=True)
    object_name = Column(String(255), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False, index=True)
    file_size = Column(String(50), nullable=True)  # Store as string to handle large files
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('ix_s3_bucket_object', 'bucket_name', 'object_name', unique=True),
        Index('ix_s3_file_type', 'file_type'),
    )

    @property
    def url(self) -> str:
        """Get the full URL for this S3 object."""
        return self.get_full_url()

    def get_full_url(self) -> str:
        """Generate the full URL for this S3 object."""
        return get_object_url(self.bucket_name, self.object_name)
    
    @classmethod
    async def get_by_bucket_and_object(
        cls,
        db: AsyncSession,
        bucket_name: str,
        object_name: str
    ) -> Optional['S3Object']:
        """Get S3Object by bucket name and object name."""
        from sqlalchemy import select
        result = await db.execute(
            select(cls).where(
                cls.bucket_name == bucket_name,
                cls.object_name == object_name
            )
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def get_by_file_type(
        cls,
        db: AsyncSession,
        file_type: str,
        limit: int = 100
    ) -> list['S3Object']:
        """Get S3Objects by file type."""
        return await cls.get_multi(
            db,
            limit=limit,
            filters={'file_type': file_type}
        )
    
    def __repr__(self):
        return f"<S3Object(id={self.id}, bucket={self.bucket_name}, object={self.object_name})>"


# Pydantic schemas for API
class S3ObjectBase(BaseSchema):
    """Base S3Object schema."""
    bucket_name: str = Field(..., max_length=255, description="S3 bucket name")
    object_name: str = Field(..., max_length=255, description="S3 object key")
    file_name: str = Field(..., max_length=255, description="Original filename")
    file_type: str = Field(..., max_length=100, description="File MIME type")
    file_size: Optional[str] = Field(None, max_length=50, description="File size in bytes")


class S3ObjectCreate(S3ObjectBase):
    """Schema for creating S3Objects."""
    pass


class S3ObjectUpdate(BaseModel):
    """Schema for updating S3Objects."""
    file_name: Optional[str] = Field(None, max_length=255)
    file_type: Optional[str] = Field(None, max_length=100)
    file_size: Optional[str] = Field(None, max_length=50)


class S3ObjectResponse(S3ObjectBase, TimestampedSchema):
    """Schema for S3Object responses."""
    url: str = Field(..., description="Pre-signed URL for accessing the object")
    
    @classmethod
    def from_orm_with_url(cls, s3_object: S3Object) -> 'S3ObjectResponse':
        """Create response schema from ORM object with URL."""
        data = s3_object.to_dict()
        data['url'] = s3_object.url
        return cls(**data)
