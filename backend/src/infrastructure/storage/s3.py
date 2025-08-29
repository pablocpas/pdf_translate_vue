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
    Genera una URL S3 prefirmada.
    Como el cliente Boto3 ya está configurado con el endpoint público,
    la URL generada será correcta de forma nativa.
    """
    try:
        params = {
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": key
        }
        
        if inline_filename:
            params["ResponseContentType"] = content_type
            params["ResponseContentDisposition"] = f'inline; filename="{inline_filename}"'
    # Genera la URL prefirmada usando el cliente configurado (con el endpoint INTERNO)
        internal_presigned_url = _client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires
        )

        # Si tenemos una URL pública definida y difiere de la interna,
        # reemplazamos el endpoint interno por el público para que el navegador del cliente pueda acceder.
        if settings.AWS_S3_PUBLIC_ENDPOINT_URL and settings.AWS_S3_ENDPOINT_URL:
            # Asegurarse de que ambos endpoints tienen un esquema (http:// o https://) para el replace
            # y que la comparación sea robusta.
            # Convertimos a esquema y dominio base para un reemplazo más seguro.
            internal_base_url = f"{internal_presigned_url.split('/minio')[0]}/minio" if '/minio' in internal_presigned_url else settings.AWS_S3_ENDPOINT_URL
            public_base_url = settings.AWS_S3_PUBLIC_ENDPOINT_URL

            # Reemplazar solo si son diferentes
            if internal_base_url != public_base_url:
                final_url = internal_presigned_url.replace(internal_base_url, public_base_url)
                logger.info(f"URL prefirmada generada (interna: {internal_presigned_url}) y convertida a pública para {key}: {final_url}")
                return final_url
        
        # Si no hay URL pública o es la misma, o el reemplazo no se aplicó,
        # devolvemos la URL generada por defecto (que ya debería ser la correcta si no hay proxy,
        # o la interna si es para uso interno).
        logger.info(f"URL prefirmada generada (sin conversión a pública) para {key}: {internal_presigned_url}")
        return internal_presigned_url

    except Exception as e:
        logger.error(f"Error generando URL prefirmada para {key}: {e}", exc_info=True)
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