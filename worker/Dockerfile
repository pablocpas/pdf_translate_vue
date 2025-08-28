# Etapa 1: Builder - Instala las dependencias
FROM python:3.10-slim-bullseye as builder

# Instala dependencias del sistema necesarias para compilar algunas librerías de Python.
# Incluimos wget para descargar el modelo YOLO.
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia solo el archivo de requisitos para aprovechar el cache de Docker
COPY requirements.txt .

# 1. Instalar PyTorch para CPU (Paso CRÍTICO)
# Se usa el índice específico de PyTorch para garantizar que no se instale la versión con CUDA.
RUN pip install --no-cache-dir --user \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 2. Instalar el resto de las dependencias desde requirements.txt
# Esto incluye doclayout-yolo, opencv, etc.
RUN pip install --no-cache-dir --user -r requirements.txt

# 3. Descargar el modelo YOLO directamente durante la construcción
# Esto evita la descarga en tiempo de ejecución y mejora el rendimiento
RUN mkdir -p /tmp/models && \
    wget -O /tmp/models/doclayout_yolo_docstructbench_imgsz1024.pt \
    https://huggingface.co/juliozhao/DocLayout-YOLO-DocStructBench/resolve/main/doclayout_yolo_docstructbench_imgsz1024.pt


# Etapa 2: Runtime - La imagen final y optimizada
FROM python:3.10-slim-bullseye

# Instala dependencias de tiempo de ejecución que necesita la aplicación (ej: para procesar PDFs e imágenes)
# opencv-python se instala vía pip, por lo que python3-opencv ya no es necesario.
RUN apt-get update && apt-get install -y \
    libgl1 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Crea un usuario no-root para mejorar la seguridad
RUN useradd --create-home appuser
WORKDIR /app

# Crea directorios necesarios con los permisos correctos
RUN mkdir -p /app/uploads /app/translated /app/models && \
    chown -R appuser:appuser /app/uploads /app/translated /app/models

COPY --from=builder --chown=appuser /tmp/models/doclayout_yolo_docstructbench_imgsz1024.pt /app/models/

# Cambia al usuario no-root
USER appuser

# Copia los paquetes de Python instalados en la etapa de builder
# El destino es el home del nuevo usuario
COPY --from=builder --chown=appuser /root/.local /home/appuser/.local

# Copia el código de la aplicación
COPY --chown=appuser . .

# Añade el directorio de binarios del usuario al PATH
ENV PATH="/home/appuser/.local/bin:${PATH}"
# Comando para iniciar la aplicación
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]