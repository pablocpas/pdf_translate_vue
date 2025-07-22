FROM python:3.9-slim-bullseye as builder

RUN apt-get update && apt-get install -y \
    wget \
    git \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

COPY requirements.txt .

# Install PyTorch first
RUN pip install --user --no-cache-dir \
    torch==1.10 torchvision==0.11.1 -f https://download.pytorch.org/whl/cpu/torch_stable.html

# Install requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt

RUN git clone https://github.com/facebookresearch/detectron2 detectron2_repo
RUN pip install --user ./detectron2_repo

# Download models with new directory structure
RUN mkdir -p models/primalayout && \
    wget -O models/primalayout/model_final.pth https://www.dropbox.com/s/h7th27jfv19rxiy/model_final.pth?dl=1 && \
    wget -O models/primalayout/config.yaml https://www.dropbox.com/s/yc92x97k50abynt/config.yaml?dl=1

RUN mkdir -p models/publaynet && \
    wget -O models/publaynet/model_final.pth https://huggingface.co/truefoundry/layout-parser/resolve/main/mask_rcnn_X_101_32x8d_FPN_3x.pth && \
    wget -O models/publaynet/config.yaml https://huggingface.co/truefoundry/layout-parser/resolve/main/mask_rcnn_X_101_32x8d_FPN_3x.yml

# Runtime stage
FROM python:3.9-slim-bullseye

# Runtime dependencies
RUN apt-get update && apt-get install -y \
    python3-opencv \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and required directories
RUN useradd --create-home appuser
WORKDIR /app

# Create required directories with correct permissions
RUN mkdir -p /app/uploads /app/translated && \
    chown -R appuser:appuser /app/uploads /app/translated

USER appuser

# Copy installed packages and models
COPY --from=builder --chown=appuser /root/.local /home/appuser/.local
COPY --from=builder --chown=appuser /app/models ./models
COPY --chown=appuser . .

ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV PYTHONPATH="/app:/app/shared"

CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]
