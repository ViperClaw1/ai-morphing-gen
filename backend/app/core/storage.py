import boto3
from botocore.client import Config

from app.core.config import get_settings


def get_r2_client():
    """R2 is S3-API-compatible — boto3's `s3` client works unmodified once pointed at the
    account's R2 endpoint, no separate SDK needed."""
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
