FROM python:3.9-slim-buster as builder

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

# Download models
RUN mkdir -p models && \
    wget -O models/model_final.pth https://www.dropbox.com/s/h7th27jfv19rxiy/model_final.pth?dl=1 && \
    wget -O models/config.yaml https://www.dropbox.com/s/yc92x97k50abynt/config.yaml?dl=1

# Runtime stage
FROM python:3.9-slim-buster

# Runtime dependencies
RUN apt-get update && apt-get install -y \
    python3-opencv \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home appuser
WORKDIR /app
USER appuser

# Copy installed packages and models
COPY --from=builder --chown=appuser /root/.local /home/appuser/.local
COPY --from=builder --chown=appuser /app/models ./models
COPY --chown=appuser . .

ENV PATH="/home/appuser/.local/bin:${PATH}"

CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]
