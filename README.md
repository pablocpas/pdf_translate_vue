# PDF Translator

A document translation system that preserves the original layout structure of PDF documents. This project uses modern document layout analysis with YOLOv10 models combined with state-of-the-art language models to provide accurate translations while maintaining document formatting.

## Overview

PDF Translator addresses the challenge of document translation while preserving complex layouts. The system processes documents through an advanced pipeline that:

1. Analyzes and extracts the document's layout structure using YOLOv10
2. Performs OCR text extraction with spatial awareness
3. Translates content using OpenAI/OpenRouter API with structured outputs
4. Reconstructs the document with translated text in original positions

## Technical Architecture

The system is built with a microservices architecture across three main components:

### 1. Document Analysis
- Layout detection and segmentation using **DocLayout-YOLO** (YOLOv10)
- OCR text extraction with PyTesseract
- Image region identification for tables, figures, and formulas
- Batch processing optimization for multiple pages

### 2. Translation Engine
- Neural machine translation using **OpenAI/OpenRouter API**
- Structured outputs with Pydantic validation
- Asynchronous batch processing for improved performance
- Support for 30+ languages including:
  - European languages (English, Spanish, French, German, etc.)
  - Asian languages (Chinese, Japanese, Korean)
  - Middle Eastern languages (Arabic, Hebrew)
  - South Asian languages (Hindi, Bengali, Tamil)

### 3. Document Reconstruction
- Layout-aware text placement with ReportLab
- Dynamic font sizing and selection
- Image region preservation
- PDF generation with original formatting
- Support for regeneration from edited translations

## Implementation Stack

### Frontend
- **Vue 3** with Composition API and TypeScript
- **Mantine UI** components for modern interface
- **Pinia** for state management with persistence
- **Vue Router** for navigation
- **Zod** for schema validation
- **Axios** for API communication
- **TanStack Query** for data fetching

### Backend
- **FastAPI** with async/await patterns
- **Celery** for distributed task processing
- **Redis** as message broker and result backend
- **MinIO** (S3-compatible) for file storage
- **Pydantic** for data validation
- Docker containerization with multi-stage builds

### Translation Pipeline
- **doclayout-yolo** for document structure analysis
- **PyTesseract** for OCR text extraction
- **OpenAI API** for neural machine translation
- **ReportLab** for PDF reconstruction
- **pdf2image** for PDF to image conversion
- **Pillow** for image processing

## Getting Started

### Prerequisites
```bash
# System requirements
- Docker and Docker Compose
- 8GB+ RAM (recommended for YOLO model)
- 10GB+ free disk space
- OpenAI API key (for translation services)
```

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pdf-translate-vue
```

2. Configure environment:
```bash
# Create .env file with required keys
OPENAI_API_KEY=your_api_key_here
```

3. Build and run with Docker:
```bash
docker-compose up -d --build
```

The application will be available at:
- **Web Interface**: http://localhost:80
- **API Endpoint**: http://localhost:8000
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Redis**: localhost:6379

## Development

### Docker Development (Recommended)
```bash
# Start all services
docker-compose up -d --build

# View logs for specific service
docker-compose logs -f worker
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down
```

### Local Development

#### Frontend (pdf-translator/)
```bash
cd pdf-translator
npm install
npm run dev          # Development server at http://localhost:5173
npm run build        # Production build
npm run preview      # Preview production build
```

#### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Worker
```bash
cd worker
pip install -r requirements.txt

# Install PyTorch CPU version
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Download YOLO model (required for local development)
mkdir -p models
wget -O models/doclayout_yolo_docstructbench_imgsz1024.pt \
  https://huggingface.co/juliozhao/DocLayout-YOLO-DocStructBench/resolve/main/doclayout_yolo_docstructbench_imgsz1024.pt

celery -A tasks worker --loglevel=info
```

## Environment Configuration

Required environment variables:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# File Storage Configuration (S3-compatible)
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_REGION=us-east-1
AWS_S3_BUCKET=pdf-translator-bucket
AWS_S3_ENDPOINT_URL=http://minio:9000
AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000
AWS_S3_USE_SSL=false

# File Management
TRANSLATED_TTL_DAYS=7
UPLOAD_FOLDER=/app/uploads
TRANSLATED_FOLDER=/app/translated
```

## Project Structure

```
pdf-translate-vue/
├── pdf-translator/                 # Vue 3 Frontend Application
│   ├── src/
│   │   ├── components/            # Vue components (TranslationEditor, FileUploader, etc.)
│   │   ├── stores/               # Pinia stores (translationStore, authStore)
│   │   ├── types/               # TypeScript definitions and Zod schemas
│   │   └── main.ts             # Application entry point
│   ├── package.json
│   └── Dockerfile
│
├── backend/                       # FastAPI Backend Service
│   ├── main.py                   # FastAPI application with endpoints
│   ├── requirements.txt
│   └── Dockerfile
│
├── worker/                        # Celery Translation Worker
│   ├── src/
│   │   ├── domain/
│   │   │   └── translator/      # Core translation domain logic
│   │   │       ├── processor.py  # Main page processing pipeline
│   │   │       ├── layout.py    # YOLOv10 document layout analysis
│   │   │       ├── translator.py # OpenAI API integration
│   │   │       ├── ocr.py       # Text extraction utilities
│   │   │       ├── pdf_utils.py # PDF manipulation utilities
│   │   │       └── utils.py     # Helper functions and font management
│   │   └── infrastructure/      # Configuration and external services
│   ├── tasks.py                 # Celery task definitions
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml             # Multi-service orchestration
├── uploads/                      # PDF upload storage (created at runtime)
├── translated/                   # Processed document storage (created at runtime)
└── README.md
```

## Key Features

### Advanced Document Processing
- **Multi-page batch processing** with optimized memory usage
- **Parallel translation processing** using Celery distributed tasks
- **Layout-aware text extraction** preserving document structure
- **Image region preservation** for tables, figures, and formulas

### Translation Capabilities
- **30+ supported languages** with automatic font selection
- **Structured API responses** using Pydantic validation
- **Batch translation optimization** reducing API calls
- **Translation editing interface** with real-time preview

### System Architecture
- **Microservices design** with Docker containerization
- **S3-compatible storage** using MinIO for scalability
- **Redis-based task queuing** for distributed processing
- **Multi-stage Docker builds** for optimized images

### Development Features
- **TypeScript throughout** for type safety
- **Hot reload** for all services during development
- **Comprehensive logging** with structured error handling
- **Modern UI/UX** with Mantine components

## Performance Optimizations

- **YOLO model pre-loading** in Docker build stage
- **Batch processing** for layout detection (up to 16 pages)
- **Concurrent translation requests** using async/await
- **Image caching** and optimized storage patterns
- **Memory-efficient** page processing pipeline

## Monitoring and Logging

The system provides comprehensive logging across all components:

```bash
# View real-time logs
docker-compose logs -f worker    # Translation processing
docker-compose logs -f backend   # API requests and responses
docker-compose logs -f frontend  # UI interactions
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

This project uses several open-source technologies:

- **DocLayout-YOLO**: Advanced document layout analysis using YOLOv10
- **OpenAI API**: State-of-the-art neural machine translation
- **Vue.js Ecosystem**: Modern reactive frontend framework
- **FastAPI**: High-performance Python web framework
- **Celery**: Distributed task queue system

---

*Note: This project has evolved from using LayoutParser to a custom implementation with DocLayout-YOLO for improved performance and maintainability.*
