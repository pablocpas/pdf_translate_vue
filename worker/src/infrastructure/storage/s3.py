import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, FlexibleChecksumError
from io import BytesIO
import logging
from typing import Optional
import time

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
        },
        # Enhanced MinIO compatibility settings
        disable_request_compression=True,
        retries={
            'max_attempts': 3,
            'mode': 'adaptive'
        },
        max_pool_connections=50
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

def download_bytes(key: str, max_retries: int = 3) -> bytes:
    """Download bytes from S3 with robust error handling and retry logic"""
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading {key} (attempt {attempt + 1}/{max_retries})")
            
            # Try different approaches based on attempt number
            if attempt == 0:
                # First attempt: try with ChecksumMode disabled if supported
                try:
                    obj = _client.get_object(
                        Bucket=settings.AWS_S3_BUCKET, 
                        Key=key,
                        ChecksumMode='DISABLED'
                    )
                except Exception:
                    # If ChecksumMode parameter not supported, fall back to normal request
                    obj = _client.get_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
            else:
                # Subsequent attempts: use standard get_object
                obj = _client.get_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
            
            # Read data with checksum error handling
            try:
                data = obj["Body"].read()
                logger.info(f"Downloaded {len(data)} bytes from s3://{settings.AWS_S3_BUCKET}/{key}")
                return data
                
            except FlexibleChecksumError as checksum_error:
                logger.warning(f"Checksum validation failed on attempt {attempt + 1}: {checksum_error}")
                last_exception = checksum_error
                
                # For checksum errors, try to read the body without validation
                # Reset the stream and read again
                try:
                    obj = _client.get_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
                    # Read raw data, accepting potential checksum mismatch
                    response_body = obj["Body"]._raw_stream
                    data = response_body.read()
                    logger.warning(f"Downloaded {len(data)} bytes from s3://{settings.AWS_S3_BUCKET}/{key} (bypassed checksum)")
                    return data
                except Exception as bypass_error:
                    logger.error(f"Failed to bypass checksum validation: {bypass_error}")
                    last_exception = bypass_error
            
        except (ClientError, FlexibleChecksumError) as e:
            logger.warning(f"Download attempt {attempt + 1} failed for {key}: {e}")
            last_exception = e
            
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1} for {key}: {e}")
            last_exception = e
        
        # Wait before retrying (exponential backoff)
        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 0.5  # 0.5s, 1s, 1.5s
            logger.info(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    # All attempts failed
    logger.error(f"Failed to download {key} after {max_retries} attempts")
    raise last_exception or Exception(f"Download failed after {max_retries} attempts")

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