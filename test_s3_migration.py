#!/usr/bin/env python3
"""
Script de prueba para la migración a S3/MinIO.
Verifica que los componentes principales funcionen correctamente.
"""

import os
import sys
import logging
import json
import tempfile
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_s3_connection():
    """Prueba la conexión con S3/MinIO"""
    try:
        # Agregar el directorio worker al path para importar módulos
        worker_path = Path(__file__).parent / "worker"
        sys.path.insert(0, str(worker_path))
        
        from src.infrastructure.storage.s3 import upload_bytes, download_bytes, key_exists, list_keys
        
        logger.info("🔧 Probando conexión con S3/MinIO...")
        
        # Test 1: Subir archivo de prueba
        test_key = "test/hello.txt"
        test_content = b"Hello, MinIO!"
        
        upload_bytes(test_key, test_content, content_type="text/plain")
        logger.info("✅ Upload exitoso")
        
        # Test 2: Verificar que existe
        if key_exists(test_key):
            logger.info("✅ Key exists funciona")
        else:
            logger.error("❌ Key exists falló")
            return False
        
        # Test 3: Descargar archivo
        downloaded = download_bytes(test_key)
        if downloaded == test_content:
            logger.info("✅ Download exitoso")
        else:
            logger.error("❌ Download falló - contenido no coincide")
            return False
        
        # Test 4: Listar keys
        keys = list_keys("test/")
        if test_key in keys:
            logger.info("✅ List keys funciona")
        else:
            logger.error("❌ List keys falló")
            return False
        
        logger.info("🎉 Conexión con S3/MinIO funcionando correctamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en conexión S3: {e}")
        return False

def test_settings():
    """Prueba que las settings se carguen correctamente"""
    try:
        worker_path = Path(__file__).parent / "worker"
        sys.path.insert(0, str(worker_path))
        
        from src.infrastructure.config.settings import settings
        
        logger.info("🔧 Probando configuración...")
        
        required_settings = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY', 
            'AWS_S3_BUCKET',
            'AWS_S3_ENDPOINT_URL'
        ]
        
        for setting in required_settings:
            value = getattr(settings, setting)
            if value:
                logger.info(f"✅ {setting}: {value}")
            else:
                logger.error(f"❌ {setting} no configurado")
                return False
        
        logger.info("🎉 Configuración cargada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error cargando configuración: {e}")
        return False

def test_tasks_import():
    """Prueba que las nuevas tareas se importen correctamente"""
    try:
        worker_path = Path(__file__).parent / "worker"
        sys.path.insert(0, str(worker_path))
        
        logger.info("🔧 Probando imports de tareas...")
        
        from tasks import translate_pdf_orchestrator, process_page_task, finalize_task
        
        logger.info("✅ Tareas principales importadas")
        
        # Verificar que las tareas legacy también funcionen
        from tasks import translate_pdf_legacy, regenerate_pdf_s3_task
        
        logger.info("✅ Tareas legacy importadas")
        logger.info("🎉 Todos los imports de tareas funcionan")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error importando tareas: {e}")
        return False

def test_backend_imports():
    """Prueba que el backend se importe correctamente"""
    try:
        backend_path = Path(__file__).parent / "backend"
        sys.path.insert(0, str(backend_path))
        
        logger.info("🔧 Probando imports del backend...")
        
        from src.infrastructure.storage.s3 import upload_bytes, download_bytes
        from src.infrastructure.config.settings import settings
        
        logger.info("✅ Imports de storage funcionan")
        logger.info("✅ Imports de configuración funcionan")
        logger.info("🎉 Backend imports funcionan")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error importando backend: {e}")
        return False

def test_docker_compose():
    """Verifica la configuració n del docker-compose"""
    try:
        logger.info("🔧 Verificando docker-compose.yml...")
        
        compose_path = Path(__file__).parent / "docker-compose.yml"
        if not compose_path.exists():
            logger.error("❌ docker-compose.yml no encontrado")
            return False
        
        with open(compose_path, 'r') as f:
            content = f.read()
        
        # Verificar que MinIO esté configurado
        if 'minio:' in content and 'minio/minio:latest' in content:
            logger.info("✅ MinIO configurado en docker-compose")
        else:
            logger.error("❌ MinIO no encontrado en docker-compose")
            return False
        
        # Verificar variables de entorno S3
        s3_vars = [
            'AWS_ACCESS_KEY_ID=minioadmin',
            'AWS_S3_BUCKET=pdf-translator-bucket',
            'AWS_S3_ENDPOINT_URL=http://minio:9000'
        ]
        
        for var in s3_vars:
            if var in content:
                logger.info(f"✅ Variable encontrada: {var}")
            else:
                logger.error(f"❌ Variable faltante: {var}")
                return False
        
        logger.info("🎉 docker-compose.yml configurado correctamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verificando docker-compose: {e}")
        return False

def main():
    """Ejecuta todas las pruebas"""
    logger.info("🚀 Iniciando pruebas de migración S3/MinIO")
    logger.info("=" * 50)
    
    tests = [
        ("Configuración", test_settings),
        ("Docker Compose", test_docker_compose),
        ("Backend Imports", test_backend_imports),
        ("Tasks Imports", test_tasks_import),
        ("Conexión S3", test_s3_connection),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n📋 Ejecutando: {test_name}")
        result = test_func()
        results.append((test_name, result))
        if result:
            logger.info(f"✅ {test_name}: PASSED")
        else:
            logger.error(f"❌ {test_name}: FAILED")
    
    # Resumen
    logger.info("\n" + "=" * 50)
    logger.info("📊 RESUMEN DE PRUEBAS")
    logger.info("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nResultado: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        logger.info("🎉 ¡MIGRACIÓN EXITOSA! Todos los componentes funcionan correctamente.")
        logger.info("\nPróximos pasos:")
        logger.info("1. Ejecutar: docker-compose up -d --build")
        logger.info("2. Verificar que MinIO esté disponible en http://localhost:9001")
        logger.info("3. Probar subir un PDF a través del frontend")
        return True
    else:
        logger.error("💥 MIGRACIÓN INCOMPLETA - Algunos componentes fallan.")
        logger.error("Revisa los errores arriba antes de continuar.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)