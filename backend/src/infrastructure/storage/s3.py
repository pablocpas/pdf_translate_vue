"""Módulo de infraestructura para la interacción con el almacenamiento S3 (o compatible como MinIO).

Proporciona funciones de alto nivel para subir, descargar, verificar, eliminar
y generar URLs prefirmadas para objetos en un bucket S3. La configuración
del cliente se realiza de forma global al importar el módulo.
"""
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from io import BytesIO
import logging
from typing import Optional

from urllib.parse import urlparse, urlunparse
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
    """Verifica si el bucket configurado existe y lo crea si es necesario.
    
    Usa una llamada `head_bucket` para comprobar la existencia, que es más
    eficiente que listar todos los buckets.

    :raises ClientError: Si ocurre un error al contactar con el servicio S3
                         que no sea un '404 Not Found'.
    """
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
    """Sube un objeto de bytes a una clave específica en S3.

    :param key: La ruta completa (clave) donde se almacenará el objeto en el bucket.
    :type key: str
    :param data: El contenido del objeto en bytes.
    :type data: bytes
    :param content_type: El tipo MIME del contenido (ej. 'application/pdf').
    :type content_type: Optional[str]
    :raises Exception: Propaga cualquier excepción ocurrida durante la subida.
    """
    try:
        extra = {"ContentType": content_type} if content_type else {}
        _client.put_object(Bucket=settings.AWS_S3_BUCKET, Key=key, Body=data, **extra)
        logger.info(f"Uploaded {len(data)} bytes to s3://{settings.AWS_S3_BUCKET}/{key}")
        
        if key_exists(key):
            logger.info(f"Upload verified for {key}")
        else:
            logger.warning(f"Upload verification failed for {key}")
            
    except Exception as e:
        logger.error(f"Error uploading to {key}: {e}")
        raise

def download_bytes(key: str) -> bytes:
    """Descarga un objeto de S3 como bytes.

    :param key: La clave del objeto a descargar.
    :type key: str
    :return: El contenido del objeto.
    :rtype: bytes
    :raises Exception: Propaga cualquier excepción si el objeto no existe o hay un error.
    """
    try:
        obj = _client.get_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
        data = obj["Body"].read()
        logger.info(f"Downloaded {len(data)} bytes from s3://{settings.AWS_S3_BUCKET}/{key}")
        return data
    except Exception as e:
        logger.error(f"Error downloading from {key}: {e}")
        raise

def key_exists(key: str) -> bool:
    """Comprueba de forma eficiente si una clave existe en el bucket.

    :param key: La clave a comprobar.
    :type key: str
    :return: True si el objeto existe, False en caso contrario.
    :rtype: bool
    :raises ClientError: Si ocurre un error de Boto3 que no sea un 404.
    """
    try:
        _client.head_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
        return True
    except ClientError as e:
        if int(e.response['Error']['Code']) == 404:
            return False
        raise

def delete_prefix(prefix: str):
    """Elimina todos los objetos en S3 que comiencen con un prefijo dado.

    Es útil para limpiar todos los archivos asociados a una tarea. Maneja la
    paginación y la eliminación en lotes de 1000 objetos.

    :param prefix: El prefijo de las claves a eliminar (ej. 'task-id/').
    :type prefix: str
    """
    try:
        paginator = _client.get_paginator("list_objects_v2")
        to_delete = []
        
        for page in paginator.paginate(Bucket=settings.AWS_S3_BUCKET, Prefix=prefix):
            for item in page.get("Contents", []):
                to_delete.append({"Key": item["Key"]})
            
            if len(to_delete) >= 1000:
                _client.delete_objects(Bucket=settings.AWS_S3_BUCKET, Delete={"Objects": to_delete})
                logger.info(f"Deleted batch of {len(to_delete)} objects with prefix {prefix}")
                to_delete.clear()
        
        if to_delete:
            _client.delete_objects(Bucket=settings.AWS_S3_BUCKET, Delete={"Objects": to_delete})
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
    """Genera una URL S3 prefirmada y la adapta a la URL pública si está configurada.

    El proceso consiste en generar primero una URL interna (ej. http://minio:9000/...)
    y luego, si se ha definido una URL pública (AWS_S3_PUBLIC_ENDPOINT_URL),
    reemplaza el host y el puerto manteniendo la ruta y los parámetros de firma,
    resultando en una URL accesible desde el exterior.

    :param key: La clave del objeto para el que se generará la URL.
    :type key: str
    :param expires: Duración de la validez de la URL en segundos.
    :type expires: int
    :param inline_filename: Si se proporciona, la URL incluirá cabeceras para
                            que el navegador muestre el archivo en lugar de descargarlo,
                            con el nombre de archivo especificado.
    :type inline_filename: Optional[str]
    :param content_type: El tipo MIME del contenido, usado con `inline_filename`.
    :type content_type: str
    :return: Una URL temporal y segura para acceder al objeto.
    :rtype: str
    """
    try:
        params = {
            "Bucket": settings.AWS_S3_BUCKET,
            "Key": key
        }
        
        if inline_filename:
            params["ResponseContentType"] = content_type
            params["ResponseContentDisposition"] = f'inline; filename="{inline_filename}"'

        internal_url = _client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires
        )
        
        if not settings.AWS_S3_PUBLIC_ENDPOINT_URL:
            logger.warning("AWS_S3_PUBLIC_ENDPOINT_URL no está definida. Devolviendo URL interna.")
            return internal_url

        internal_parts = urlparse(internal_url)
        public_parts = urlparse(settings.AWS_S3_PUBLIC_ENDPOINT_URL)
        final_path = public_parts.path.rstrip('/') + internal_parts.path

        final_url_parts = (
            public_parts.scheme,
            public_parts.netloc,
            final_path,
            internal_parts.params,
            internal_parts.query,
            internal_parts.fragment
        )
        
        public_url = urlunparse(final_url_parts)
        
        logger.info(f"URL prefirmada generada y convertida a pública para {key}: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"Error generando URL prefirmada para {key}: {e}", exc_info=True)
        raise

def list_keys(prefix: str = "") -> list[str]:
    """Lista todas las claves en el bucket que coinciden con un prefijo.

    :param prefix: El prefijo a buscar. Si está vacío, lista todas las claves.
    :type prefix: str
    :return: Una lista de strings, donde cada string es una clave de objeto.
    :rtype: list[str]
    """
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