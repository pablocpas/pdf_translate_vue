# Utiliza una imagen base de Ubuntu
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# Instala dependencias necesarias
RUN apt-get update && apt-get install -y \
    python3-opencv \
    ca-certificates \
    python3-dev \
    poppler-utils \
    tesseract-ocr \
    git \
    wget \
    sudo \
    ninja-build \
    gcc \
    g++ \
    && apt-get clean

# Crea un enlace simbólico para python3
RUN ln -sv /usr/bin/python3 /usr/bin/python

# Crea el directorio models y descarga el modelo
RUN mkdir -p /app/models
RUN wget -O /app/models/model_final.pth https://www.dropbox.com/s/h7th27jfv19rxiy/model_final.pth?dl=1
RUN wget -O /app/models/config.yaml https://www.dropbox.com/s/yc92x97k50abynt/config.yaml?dl=1

# Crea un usuario no-root
ARG USER_ID=1000
RUN useradd -m --no-log-init --system --uid ${USER_ID} appuser -g sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Configura permisos antes de cambiar al usuario
RUN mkdir -p /app/src/uploads && chown -R appuser:sudo /app

USER appuser
WORKDIR /home/appuser

# Configura el entorno para instalar pip
ENV PATH="/home/appuser/.local/bin:${PATH}"
RUN wget https://bootstrap.pypa.io/get-pip.py && \
    python3 get-pip.py --user && \
    rm get-pip.py

# Instala PyTorch y torchvision para CPU desde PyTorch.org
RUN pip install --user torch==1.10 torchvision==0.11.1 -f https://download.pytorch.org/whl/cpu/torch_stable.html

# Instala dependencias adicionales y fvcore
RUN pip install --user tensorboard cmake onnx
RUN pip install --user 'git+https://github.com/facebookresearch/fvcore'

# Clona e instala detectron2 para CPU
RUN git clone https://github.com/facebookresearch/detectron2 detectron2_repo
RUN pip install --user -e detectron2_repo

# Instala Layout Parser y otras dependencias
RUN pip install --user layoutparser
RUN pip install --user pytesseract
RUN pip install --user reportlab
RUN pip install --user shapely
RUN pip install --user openai
RUN pip install --user fastapi
RUN pip install --user uvicorn
RUN pip install --user python-multipart
RUN pip install --user celery
RUN pip install --user redis
RUN pip install --user pdf2image

# Copia el código de la aplicación
WORKDIR /app
COPY . .

CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]
