import uuid

import boto3

from src.config import get_settings
from src.logger import logger


def get_s3_client():
    """Get S3 client.
    Returns:
        boto3.client: The S3 client."""

    settings = get_settings()
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_access_key,
        aws_session_token=None,
        verify=False,
    )
    return s3_client


def upload_object_to_s3(file_name: str, file, bucket: str | None = None):
    settings = get_settings()
    bucket = bucket or settings.s3_bucket
    filename = f"{uuid.uuid4().hex}{file_name}"
    s3_client = get_s3_client()
    if not s3_client:
        return
    s3_client.upload_fileobj(file, bucket, filename)
    logger.info("Uploaded %s to %s", filename, bucket)
    return filename


def download_object_from_s3(bucket_name, object_name, file_name):
    """Download a file from an S3 bucket.
    Args:
        bucket_name (str): Bucket to download from.
        object_name (str): S3 object name.
        file_name (str): Local file name to save to.
    Returns:
        bool: True if file was downloaded, else False."""

    s3_client = get_s3_client()
    try:
        s3_client.download_file(bucket_name, object_name, file_name)
    except Exception as e:
        logger.error(e)
        return False
    return True


def get_object_url(bucket_name, object_name):
    """Get the url of an object in S3.
    Args:
        bucket_name (str): Bucket name.
        object_name (str): Object name.
    Returns:
        str: The url of the object."""

    s3_client = get_s3_client()
    try:
        url = s3_client.generate_presigned_url("get_object", Params={"Bucket": bucket_name, "Key": object_name})
    except Exception as e:
        logger.error(e)
        return None
    return url
