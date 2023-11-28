from fastapi import APIRouter, Depends, Request, UploadFile, File
from src.logger import logger

from src.models.database import get_db
from src.models.s3 import S3Object
from src.config import Settings
from src.s3 import upload_object_to_s3

router = APIRouter()


@router.post("/s3-upload")
async def s3_upload(request: Request, file: UploadFile = File(...), db=Depends(get_db)):
    if not file or not file.filename:
        logger.error("No file uploaded")
        return {"result": "fail"}
    filename = upload_object_to_s3(file.filename, file.file, Settings.S3_BUCKET)
    if not filename:
        logger.error("Failed to upload file to S3")
        return {"result": "fail"}
    s3_object = S3Object(
        file_name=filename, file_type=file.content_type, bucket_name=Settings.S3_BUCKET, object_name=filename
    )
    db.add(s3_object)
    db.commit()
    return {"result": "success"}


@router.get("/s3-objects")
async def s3_objects(request: Request, db=Depends(get_db)):
    s3_objects = db.query(S3Object).all()

    return {"s3_objects": s3_objects}
