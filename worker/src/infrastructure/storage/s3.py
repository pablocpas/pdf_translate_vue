import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from io import BytesIO
import logging
from typing import Optional

from ..config.settings import settings

logger = logging.getLogger(__name__)

# Common configuration for both clients
_common_config = {
    "region_name": settings.AWS_REGION,
    "use_ssl": settings.AWS_S3_USE_SSL,
    "config": Config(
        signature_version="s3v4",
        s3={
            'addressing_style': 'path'  # Better compatibility with MinIO
        }
    ),
    "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
    "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
}

# Global S3 client instances
_session = boto3.session.Session()
_operations_client = None
_presigned_client = None

def _initialize_clients():
    """Initialize S3 clients based on storage provider configuration"""
    global _operations_client, _presigned_client
    
    logger.info(f"Initializing S3 clients for provider: {settings.STORAGE_PROVIDER}")
    
    # Operations client (always uses internal endpoint)
    _operations_client = _session.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        **_common_config
    )
    
    if settings.STORAGE_PROVIDER == "minio":
        # Local development with MinIO: separate client for presigned URLs
        logger.info("Configuring separate presigned client for MinIO")
        public_endpoint = settings.AWS_S3_PUBLIC_ENDPOINT_URL or settings.AWS_S3_ENDPOINT_URL
        _presigned_client = _session.client(
            "s3",
            endpoint_url=public_endpoint,
            **_common_config
        )
    else:
        # Production with S3: same client for both operations and presigning
        logger.info("Using single client for AWS S3")
        _presigned_client = _operations_client

# Initialize clients on module load
_initialize_clients()

def ensure_bucket_exists():
    """Create bucket if it doesn't exist"""
    try:
        _operations_client.head_bucket(Bucket=settings.AWS_S3_BUCKET)
        logger.info(f"Bucket {settings.AWS_S3_BUCKET} exists")
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            logger.info(f"Creating bucket {settings.AWS_S3_BUCKET}")
            _operations_client.create_bucket(Bucket=settings.AWS_S3_BUCKET)
        else:
            logger.error(f"Error checking bucket: {e}")
            raise

def upload_bytes(key: str, data: bytes, content_type: Optional[str] = None):
    """Upload bytes to S3"""
    try:
        extra = {"ContentType": content_type} if content_type else {}
        
        # No usar ChecksumAlgorithm con MinIO por compatibilidad
        _operations_client.put_object(Bucket=settings.AWS_S3_BUCKET, Key=key, Body=data, **extra)
        logger.info(f"Uploaded {len(data)} bytes to s3://{settings.AWS_S3_BUCKET}/{key}")
        
        # Verificar que el archivo se subió correctamente
        if key_exists(key):
            logger.info(f"Upload verified for {key}")
        else:
            logger.warning(f"Upload verification failed for {key}")
            
    except Exception as e:
        logger.error(f"Error uploading to {key}: {e}")
        raise

def download_bytes(key: str) -> bytes:
    """Download bytes from S3"""
    try:
        obj = _operations_client.get_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
        data = obj["Body"].read()
        logger.info(f"Downloaded {len(data)} bytes from s3://{settings.AWS_S3_BUCKET}/{key}")
        return data
    except Exception as e:
        logger.error(f"Error downloading from {key}: {e}")
        raise

def key_exists(key: str) -> bool:
    """Check if a key exists in S3"""
    try:
        _operations_client.head_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
        return True
    except ClientError as e:
        if int(e.response['Error']['Code']) == 404:
            return False
        raise

def delete_prefix(prefix: str):
    """Delete all objects with a given prefix"""
    try:
        paginator = _operations_client.get_paginator("list_objects_v2")
        to_delete = []
        
        for page in paginator.paginate(Bucket=settings.AWS_S3_BUCKET, Prefix=prefix):
            for item in page.get("Contents", []):
                to_delete.append({"Key": item["Key"]})
            
            # Delete in batches of 1000 (S3 limit)
            if len(to_delete) >= 1000:
                _operations_client.delete_objects(
                    Bucket=settings.AWS_S3_BUCKET, 
                    Delete={"Objects": to_delete}
                )
                logger.info(f"Deleted batch of {len(to_delete)} objects with prefix {prefix}")
                to_delete.clear()
        
        # Delete remaining objects
        if to_delete:
            _operations_client.delete_objects(
                Bucket=settings.AWS_S3_BUCKET, 
                Delete={"Objects": to_delete}
            )
            logger.info(f"Deleted final batch of {len(to_delete)} objects with prefix {prefix}")
            
    except Exception as e:
        logger.error(f"Error deleting objects with prefix {prefix}: {e}")
        raise

def presigned_get_url(
    key: str,
    expires: int = 3600,
    inline_filename: Optional[str] = None,
    content_type: str = "application/pdf"
) -> str:
    """
    Generate a presigned URL for S3 object access.
    Uses the appropriate client based on storage provider configuration.
    """
    try:
        params = {
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": key
        }
        
        if inline_filename:
            params["ResponseContentType"] = content_type
            params["ResponseContentDisposition"] = f'inline; filename="{inline_filename}"'

        # Generate presigned URL using the dedicated presigned client
        # This will be configured with the correct endpoint based on the environment
        presigned_url = _presigned_client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires
        )
        
        logger.info(f"Generated presigned URL for {key}: {presigned_url}")
        return presigned_url

    except Exception as e:
        logger.error(f"Error generating presigned URL for {key}: {e}", exc_info=True)
        raise

def list_keys(prefix: str = "") -> list[str]:
    """List all keys with a given prefix"""
    try:
        paginator = _operations_client.get_paginator("list_objects_v2")
        keys = []
        
        for page in paginator.paginate(Bucket=settings.AWS_S3_BUCKET, Prefix=prefix):
            for item in page.get("Contents", []):
                keys.append(item["Key"])
                
        return keys
        
    except Exception as e:
        logger.error(f"Error listing keys with prefix {prefix}: {e}")
        raise

# Initialize bucket on import
try:
    ensure_bucket_exists()
except Exception as e:
    logger.warning(f"Could not ensure bucket exists: {e}")