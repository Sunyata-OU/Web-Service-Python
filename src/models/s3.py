from sqlalchemy import Column, String
from src.models.database import BaseModel
from src.s3 import get_object_url


class S3Object(BaseModel):
    __tablename__ = "s3_objects"

    bucket_name = Column(String(255), nullable=False)
    object_name = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(255), nullable=False)

    @property
    def url(self):
        return self.get_full_url()

    def __repr__(self):
        return f"<S3Object {self.id}>"

    def get_full_url(self):
        url = get_object_url(self.bucket_name, self.object_name)
        return url
