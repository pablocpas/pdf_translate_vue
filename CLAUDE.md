# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDF Translator is a document translation system that preserves PDF layout structure using LayoutParser for document analysis and OpenAI/OpenRouter for neural machine translation. The system processes PDFs by analyzing layout, extracting text with OCR, translating content, and reconstructing documents with original formatting.

## Architecture

### Core Components
- **Frontend**: Vue 3 + TypeScript + Mantine UI (`pdf-translator/`)
- **Backend**: FastAPI with async processing (`backend/`)
- **Worker**: Celery worker with LayoutParser integration (`worker/`)
- **Message Queue**: Redis for task coordination

### Key Directories
- `pdf-translator/src/components/` - Vue components including TranslationEditor, FileUploader, ResultPDF
- `pdf-translator/src/stores/` - Pinia stores for state management (translationStore, authStore)
- `backend/main.py` - FastAPI endpoints and Celery task management
- `worker/src/domain/translator/` - Core translation logic with LayoutParser integration
- `uploads/` and `translated/` - File storage directories

## Development Commands

### Docker Development (Recommended)
```bash
# Start all services
docker-compose up -d --build

# View logs
docker-compose logs -f [service-name]

# Stop services
docker-compose down
```

### Local Development

#### Frontend (pdf-translator/)
```bash
cd pdf-translator
npm install
npm run dev          # Development server
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
celery -A tasks worker --loglevel=info
```

## Environment Setup

Required environment variables:
- `OPENAI_API_KEY` - OpenAI API key for translation
- `CELERY_BROKER_URL` - Redis URL (default: redis://redis:6379/0)
- `CELERY_RESULT_BACKEND` - Redis URL for results

## Key Technologies

### Frontend Stack
- Vue 3 with Composition API and TypeScript
- Pinia for state management
- Mantine UI components
- Vue Router for navigation
- Zod for schema validation
- Monaco Editor for translation editing

### Backend Stack
- FastAPI with async/await patterns
- Celery for distributed task processing
- Redis as message broker
- Pydantic for data validation

### Translation Pipeline
- LayoutParser for document structure analysis
- PyTesseract for OCR text extraction
- OpenAI API for neural machine translation
- ReportLab for PDF reconstruction
- pdf2image for PDF to image conversion

## Key Files

### Frontend Architecture
- `pdf-translator/src/stores/translationStore.ts` - Central state management for translation tasks
- `pdf-translator/src/components/TranslationEditor.vue` - Interactive translation editing interface
- `pdf-translator/src/types/schemas.ts` - Zod schemas for API validation

### Backend Architecture
- `backend/main.py` - FastAPI application with CORS, file upload, and task management endpoints
- `worker/tasks.py` - Celery task definitions with parallel processing
- `worker/src/domain/translator/processor.py` - Core translation processing logic

### Translation Domain
- `worker/src/domain/translator/layout.py` - LayoutParser integration for document analysis
- `worker/src/domain/translator/ocr.py` - OCR text extraction utilities
- `worker/src/domain/translator/pdf_utils.py` - PDF manipulation and conversion utilities

## Development Notes

### Task Processing
The system uses Celery with Redis for distributed task processing. Translation tasks are processed in parallel by converting PDF pages to images, analyzing layout with LayoutParser, extracting text via OCR, translating with OpenAI, and reconstructing PDFs.

### State Management
Frontend uses Pinia stores with persistence to localStorage. Translation progress is tracked through WebSocket-like polling of Celery task states.

### File Handling
PDFs are uploaded to `uploads/` directory, processed asynchronously, and results saved to `translated/` with accompanying metadata JSON files.

### API Integration
The system integrates with OpenAI API for translation services. Model selection includes options for different translation approaches (primalayout, etc.).