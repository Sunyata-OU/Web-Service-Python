try:
    # Try new async models first
    from src.database import Base
    from src.models.s3 import S3Object  # type: ignore[misc]
except ImportError:
    # Fallback to legacy models for backward compatibility
    # Create a simple S3Object for backward compatibility
    from sqlalchemy import Column, String

    from src.models.database import Base, BaseModel

    class S3Object(BaseModel):  # type: ignore[no-redef]
        __tablename__ = "s3_objects"

        bucket_name = Column(String(255), nullable=False)
        object_name = Column(String(255), nullable=False)
        file_name = Column(String(255), nullable=False)
        file_type = Column(String(255), nullable=False)

        @property
        def url(self):
            return self.get_full_url()

        def get_full_url(self):
            from src.s3 import get_object_url

            return get_object_url(self.bucket_name, self.object_name)

        def __repr__(self):
            return f"<S3Object {self.id}>"


__all__ = [
    "Base",
    "S3Object",
]
