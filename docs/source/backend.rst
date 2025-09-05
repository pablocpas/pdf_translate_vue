Documentación del Backend
=========================

El backend es una aplicación FastAPI que gestiona las solicitudes de traducción,
el estado de las tareas y la descarga de archivos.

.. contents::
   :local:
   :depth: 2

API Principal
-------------
Este módulo contiene la aplicación FastAPI, define todos los endpoints, los
modelos de datos Pydantic y la configuración inicial de Celery.

.. automodule:: backend.main
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: app, celery_app

Infraestructura de Almacenamiento
---------------------------------
Este módulo abstrae toda la lógica de comunicación con el servicio de
almacenamiento compatible con S3 (como MinIO), incluyendo la subida,
descarga y generación de URLs seguras.

.. automodule:: backend.src.infrastructure.storage.s3
   :members:
   :undoc-members:
   :show-inheritance: