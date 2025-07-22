# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDF Translator is a document translation system that preserves the original layout structure of PDF documents. It uses LayoutParser for document analysis and OpenAI/OpenRouter API for translation.

### Architecture

**3-tier microservices architecture:**
- **Frontend**: Vue 3 + TypeScript (Vite) with Mantine UI (`pdf-translator/`)
- **Backend**: FastAPI service for file handling and task coordination (`backend/`)
- **Worker**: Celery worker for PDF processing and translation (`worker/`)

**Key Dependencies:**
- `LayoutParser` (document analysis)
- `OpenAI API` (translation)
- `Redis` (Celery message broker)
- `ReportLab` (PDF generation)

## Development Commands

### Full Stack Development (Docker)
```bash
# Build and run all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Application URLs:**
- Frontend: http://localhost:80
- Backend API: http://localhost:8000
- Redis: localhost:6379

### Frontend Development (`pdf-translator/`)
```bash
cd pdf-translator
npm install           # Install dependencies
npm run dev           # Development server (Vite)
npm run build         # Production build
npm run preview       # Preview production build
```

### Backend Development (`backend/`)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload    # Development server
```

### Worker Development (`worker/`)
```bash
cd worker
pip install -r requirements.txt
celery -A tasks worker --loglevel=info    # Start Celery worker
```

## Environment Setup

**Required environment variables:**
```bash
OPENAI_API_KEY=your_api_key_here
VITE_API_URL=http://localhost:8000  # Frontend API URL
```

## Code Architecture

### Frontend (`pdf-translator/src/`)

**State Management:**
- Pinia stores: `translationStore.ts`, `authStore.ts`
- Persistent task history and current task tracking

**API Layer:**
- `api/client.ts`: Axios client with retry logic and error handling
- `api/pdfs.ts`: PDF upload/download endpoints

**Key Components:**
- `FileUploader.vue`: PDF upload interface
- `TranslationEditor.vue`: Text editing during translation
- `ResultPDF.vue`: Download and preview translated PDFs

### Backend (`backend/main.py`)

**FastAPI service handling:**
- File upload/download endpoints
- Celery task management and status tracking
- CORS configuration for frontend communication

### Worker (`worker/`)

**Core Translation Logic:**
- `src/domain/translator/processor.py`: Main PDF processing pipeline
- `src/domain/translator/ocr.py`: LayoutParser integration
- `src/domain/translator/translator.py`: OpenAI API integration
- `src/domain/translator/layout.py`: PDF reconstruction with ReportLab

**Task Processing:**
- `tasks.py`: Celery task definitions for async PDF processing
- Supports layout-preserving translation and PDF regeneration

## File Storage

**Volume mounts:**
- `./uploads/`: Original PDF files
- `./translated/`: Processed translation results
- Translation data stored as JSON with position information

## Translation Process

1. **Upload**: PDF uploaded via frontend to backend
2. **Analysis**: Worker extracts layout using LayoutParser
3. **OCR**: Text extraction while preserving spatial coordinates
4. **Translation**: OpenAI API translates text segments
5. **Reconstruction**: ReportLab regenerates PDF with translated text
6. **Download**: Frontend retrieves completed translation

## Multi-language Support

**Font handling in worker:**
- OpenSans for Latin scripts
- UnicodeCIDFont support for CJK languages (Chinese, Japanese, Korean)
- Font selection based on target language in `processor.py:get_font_for_language()`