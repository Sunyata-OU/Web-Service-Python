from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_current_user, get_optional_user
from src.config import get_settings
from src.database import get_async_db
from src.logger import logger
from src.models.base import PaginatedResponse
from src.models.s3 import S3Object, S3ObjectResponse
from src.models.user import User
from src.s3 import upload_object_to_s3

router = APIRouter(prefix="/s3", tags=["File Storage"])


@router.post("/upload", response_model=S3ObjectResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Upload a file to S3 storage."""
    settings = get_settings()

    if not file or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    # Upload to S3
    try:
        object_name = upload_object_to_s3(file.filename, file.file, settings.s3_bucket)
        if not object_name:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload file to storage"
            )
    except Exception as e:
        logger.error(f"S3 upload failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="File upload failed")

    # Get file size
    file_size = None
    if hasattr(file, "size"):
        file_size = str(file.size)

    # Create database record
    s3_object = await S3Object.create(
        db,
        file_name=file.filename,
        file_type=file.content_type or "application/octet-stream",
        bucket_name=settings.s3_bucket,
        object_name=object_name,
        file_size=file_size,
    )

    await db.commit()

    return S3ObjectResponse.from_orm_with_url(s3_object)


@router.get("/objects", response_model=PaginatedResponse[S3ObjectResponse])
async def list_objects(
    page: int = 1,
    size: int = 20,
    file_type: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List uploaded files with pagination."""
    if size > 100:
        size = 100  # Limit page size

    skip = (page - 1) * size

    # Apply filters
    filters = {}
    if file_type:
        filters["file_type"] = file_type

    # Get objects and total count
    objects = await S3Object.get_multi(db, skip=skip, limit=size, filters=filters, order_by="created_at")

    total = await S3Object.count(db, filters=filters)

    # Convert to response format
    object_responses = [S3ObjectResponse.from_orm_with_url(obj) for obj in objects]

    return PaginatedResponse.create(items=object_responses, total=total, page=page, size=size)


@router.get("/objects/{object_id}", response_model=S3ObjectResponse)
async def get_object(
    object_id: int, current_user: Optional[User] = Depends(get_optional_user), db: AsyncSession = Depends(get_async_db)
):
    """Get details of a specific uploaded file."""
    s3_object = await S3Object.get(db, object_id)

    if not s3_object:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")

    return S3ObjectResponse.from_orm_with_url(s3_object)


@router.delete("/objects/{object_id}")
async def delete_object(
    object_id: int,
    current_user: User = Depends(get_current_user),  # Require auth for deletion
    db: AsyncSession = Depends(get_async_db),
):
    """Delete an uploaded file."""
    s3_object = await S3Object.get(db, object_id)

    if not s3_object:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")

    # TODO: Also delete from S3 storage
    # This would require implementing delete_object_from_s3() in src.s3

    await s3_object.delete(db)
    await db.commit()

    return {"message": "Object deleted successfully"}


@router.get("/objects/by-type/{file_type}", response_model=List[S3ObjectResponse])
async def get_objects_by_type(
    file_type: str,
    limit: int = 50,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get objects by file type."""
    if limit > 100:
        limit = 100

    objects = await S3Object.get_by_file_type(db, file_type, limit)

    return [S3ObjectResponse.from_orm_with_url(obj) for obj in objects]


# Legacy endpoints for backward compatibility
@router.post("/s3-upload")
async def legacy_upload(request: Request, file: UploadFile = File(...), db: AsyncSession = Depends(get_async_db)):
    """Legacy upload endpoint - deprecated, use /upload instead."""
    try:
        response = await upload_file(file=file, current_user=None, db=db)
        return {"result": "success", "object": response}
    except HTTPException:
        return {"result": "fail"}


@router.get("/s3-objects")
async def legacy_list_objects(request: Request, db: AsyncSession = Depends(get_async_db)):
    """Legacy list objects endpoint - deprecated, use /objects instead."""
    objects = await S3Object.get_multi(db, limit=50)

    return {"s3_objects": [{**obj.to_dict(), "url": obj.url} for obj in objects]}
