try:
    # Try new async models first
    from src.database import Base
    from src.models.s3 import S3Object
except ImportError:
    # Fallback to legacy models for backward compatibility
    from src.models.database import Base, BaseModel
    
    # Create a simple S3Object for backward compatibility
    from sqlalchemy import Column, String
    
    class S3Object(BaseModel):
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
