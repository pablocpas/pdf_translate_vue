import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from io import BytesIO
import logging
from typing import Optional

from ..config.settings import settings

logger = logging.getLogger(__name__)

# Global S3 client configuration
_session = boto3.session.Session()
_client = _session.client(
    "s3",
    region_name=settings.AWS_REGION,
    endpoint_url=settings.AWS_S3_ENDPOINT_URL,
    use_ssl=settings.AWS_S3_USE_SSL,
    config=Config(
        signature_version="s3v4",
        s3={
            'addressing_style': 'path'  # Mejor compatibilidad con MinIO
        }
    ),
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)

def ensure_bucket_exists():
    """Create bucket if it doesn't exist"""

            

    try:
        _client.head_bucket(Bucket=settings.AWS_S3_BUCKET)
        logger.info(f"Bucket {settings.AWS_S3_BUCKET} exists")
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            logger.info(f"Creating bucket {settings.AWS_S3_BUCKET}")
            _client.create_bucket(Bucket=settings.AWS_S3_BUCKET)
        else:
            logger.error(f"Error checking bucket: {e}")
            raise

def upload_bytes(key: str, data: bytes, content_type: Optional[str] = None):
    """Upload bytes to S3"""
    try:
        extra = {"ContentType": content_type} if content_type else {}
        
        # No usar ChecksumAlgorithm con MinIO por compatibilidad
        _client.put_object(Bucket=settings.AWS_S3_BUCKET, Key=key, Body=data, **extra)
        logger.info(f"Uploadedeeeee {len(data)} bytes to s3://{settings.AWS_S3_BUCKET}/{key}")
        logger.info(f"public endpoint URL: {settings.AWS_S3_PUBLIC_ENDPOINT_URL}")
        logger.info(f"internal endpoint URL: {settings.AWS_S3_ENDPOINT_URL}")
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
        obj = _client.get_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
        data = obj["Body"].read()
        logger.info(f"Downloaded {len(data)} bytes from s3://{settings.AWS_S3_BUCKET}/{key}")
        return data
    except Exception as e:
        logger.error(f"Error downloading from {key}: {e}")
        raise

def key_exists(key: str) -> bool:
    """Check if a key exists in S3"""
    try:
        _client.head_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
        return True
    except ClientError as e:
        if int(e.response['Error']['Code']) == 404:
            return False
        raise

def delete_prefix(prefix: str):
    """Delete all objects with a given prefix"""
    try:
        paginator = _client.get_paginator("list_objects_v2")
        to_delete = []
        
        for page in paginator.paginate(Bucket=settings.AWS_S3_BUCKET, Prefix=prefix):
            for item in page.get("Contents", []):
                to_delete.append({"Key": item["Key"]})
            
            # Delete in batches of 1000 (S3 limit)
            if len(to_delete) >= 1000:
                _client.delete_objects(
                    Bucket=settings.AWS_S3_BUCKET, 
                    Delete={"Objects": to_delete}
                )
                logger.info(f"Deleted batch of {len(to_delete)} objects with prefix {prefix}")
                to_delete.clear()
        
        # Delete remaining objects
        if to_delete:
            _client.delete_objects(
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
    Generate a presigned URL for downloading an object, ensuring the
    signature is calculated against the public-facing endpoint.
    """
    try:
        # Determinar el endpoint correcto para la generación de la URL.
        # Usar el endpoint público si está definido, de lo contrario, usar el interno.
        presign_endpoint_url = settings.AWS_S3_PUBLIC_ENDPOINT_URL or settings.AWS_S3_ENDPOINT_URL

        # Crear un cliente S3 dedicado SOLO para generar esta URL prefirmada.
        # Esto es crucial para que la firma se calcule con el endpoint correcto (el público).
        presign_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            endpoint_url=presign_endpoint_url,
            use_ssl=settings.AWS_S3_USE_SSL,
            config=Config(
                signature_version="s3v4",
                s3={'addressing_style': 'path'}
            ),
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        params = {"Bucket": settings.AWS_S3_BUCKET, "Key": key}
        
        # Cabeceras para forzar la visualización en el navegador en lugar de la descarga
        response_headers = {
            "ResponseContentType": content_type,
            "ResponseContentDisposition": f'inline; filename="{inline_filename or key.split("/")[-1]}"'
        }

        url = presign_client.generate_presigned_url(
            "get_object",
            Params={**params, **response_headers},
            ExpiresIn=expires
        )

        logger.info(f"Generated presigned URL with endpoint {presign_endpoint_url} for {key}")
        return url

    except Exception as e:
        logger.error(f"Error generating presigned URL for {key}: {e}")
        raise

def list_keys(prefix: str = "") -> list[str]:
    """List all keys with a given prefix"""
    try:
        paginator = _client.get_paginator("list_objects_v2")
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