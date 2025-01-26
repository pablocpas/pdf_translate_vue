# PDF Translator

A document translation system that preserves the original layout structure of PDF documents. This project leverages advanced document layout analysis techniques using [LayoutParser](https://github.com/Layout-Parser/layout-parser) combined with state-of-the-art language models to provide accurate translations while maintaining document formatting.

## Overview

PDF Translator addresses the challenge of document translation while preserving complex layouts. By utilizing LayoutParser's document image analysis capabilities [1] along with modern language models, the system:

1. Analyzes and extracts the document's layout structure
2. Processes text while maintaining spatial relationships
3. Generates translated content preserving the original formatting
4. Reconstructs the document with the translated text

## Technical Architecture

The system is built on three main components:

### 1. Document Analysis
- Layout detection and segmentation using LayoutParser
- Text extraction with OCR integration
- Structural hierarchy preservation

### 2. Translation Engine
- Neural machine translation using OpenAI/OpenRouter API
- Support for 30+ languages including:
  - European languages (English, Spanish, French, etc.)
  - Asian languages (Chinese, Japanese, Korean)
  - Middle Eastern languages (Arabic, Hebrew)
  - South Asian languages (Hindi, Bengali, Tamil)

### 3. Document Reconstruction
- Layout-aware text placement
- Font and style preservation
- PDF generation with original formatting

## Implementation

### Frontend
- Vue 3 + TypeScript
- Real-time translation progress tracking
- Interactive document preview
- Mantine UI components

### Backend
- FastAPI (Python)
- Asynchronous processing with Celery
- Redis message broker
- Docker containerization

## Getting Started

### Prerequisites
```bash
# System requirements
- Docker and Docker Compose
- 8GB+ RAM
- 10GB+ free disk space
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

3. Build and run:
```bash
docker-compose up -d --build
```

The application will be available at:
- Web Interface: http://localhost:80
- API Endpoint: http://localhost:8000

## Development

For local development:

```bash
# Frontend
cd pdf-translator
npm install
npm run dev

# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Worker
cd worker
pip install -r requirements.txt
celery -A tasks worker --loglevel=info
```

## Project Structure

```
.
├── pdf-translator/          # Frontend application
├── backend/                 # FastAPI service
├── worker/                 # Translation worker
│   └── src/
│       └── domain/        # Core translation logic
├── uploads/               # Document storage
└── translated/            # Processed documents
```

## References

[1] Shen, Z., Zhang, R., Dell, M., Lee, B. C. G., Carlson, J., & Li, W. (2021). LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis. arXiv preprint arXiv:2103.15348.

```bibtex
@article{shen2021layoutparser,
  title={LayoutParser: A Unified Toolkit for Deep Learning Based Document Image Analysis},
  author={Shen, Zejiang and Zhang, Ruochen and Dell, Melissa and Lee, Benjamin Charles Germain and Carlson, Jacob and Li, Weining},
  journal={arXiv preprint arXiv:2103.15348},
  year={2021}
}
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

*Note: This project uses LayoutParser, an open-source tool for document image analysis. We acknowledge and thank the LayoutParser team for their contributions to the field.*
