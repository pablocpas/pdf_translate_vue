# Docker Testing Plan for Refactored PDF Translator

## 🐳 Why Docker is Essential

**LayoutParser & Detectron2 Requirements:**
- CUDA/GPU dependencies
- Specific Python/PyTorch versions
- Model downloads and caching
- Complex system dependencies (OpenCV, etc.)
- Environment-specific compilation

## 📋 Systematic Testing Approach

### Phase 1: Docker Environment Setup
```bash
# In WSL with Docker
cd /mnt/c/Users/user_/Documents/pdftranslate

# Check current docker-compose
docker-compose ps
docker-compose down  # Clean slate

# Build with refactored code
docker-compose build --no-cache

# Verify builds succeeded
docker images | grep pdftranslate
```

### Phase 2: Shared Module Testing (Worker Container)
```bash
# Test shared configuration
docker-compose run worker python -c "
from shared.config import get_settings
settings = get_settings()
print('✅ Config loaded')
print(f'Upload: {settings.upload_folder}')
"

# Test shared models
docker-compose run worker python -c "
from shared.models.translation import TranslationTask
from shared.models.exceptions import ProcessingError
print('✅ Models imported successfully')
"

# Test shared utilities
docker-compose run worker python -c "
from shared.utils.file_utils import ensure_directory_exists
from shared.utils.logging_utils import get_logger
print('✅ Utilities working')
"
```

### Phase 3: Backend API Testing
```bash
# Start services
docker-compose up -d

# Test health endpoint
curl http://localhost:8000/api/health

# Test detailed health
curl http://localhost:8000/api/health/detailed

# Check logs
docker-compose logs backend
```

### Phase 4: Worker Component Testing
```bash
# Test worker startup
docker-compose logs worker

# Test LayoutParser imports
docker-compose run worker python -c "
try:
    import layoutparser as lp
    print('✅ LayoutParser available')
    # Test model loading (this might download models)
    model = lp.Detectron2LayoutModel('lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config')
    print('✅ LayoutParser model loaded')
except Exception as e:
    print(f'⚠️ LayoutParser issue: {e}')
"

# Test translation imports
docker-compose run worker python -c "
from worker.core.translation.translator import TranslationEngine
from worker.core.document.analyzer import DocumentAnalyzer
print('✅ Worker core components imported')
"
```

### Phase 5: Integration Testing
```bash
# Test file upload (need to mount test files)
curl -F "file=@test.pdf" -F "target_language=es" \
     http://localhost:8000/api/upload

# Monitor task processing
docker-compose logs -f worker

# Test task status
curl http://localhost:8000/api/translation/{task_id}/status
```

## 🚨 Common Issues to Watch For

### 1. Pydantic Version Conflicts
- **Problem**: BaseSettings import errors
- **Solution**: Use pydantic v1 or install pydantic-settings
- **Test in**: Worker container first

### 2. LayoutParser Model Downloads
- **Problem**: Models not cached, slow first run
- **Solution**: Pre-download in Docker build or mount cache volume
- **Test**: Model loading time and success

### 3. GPU Access (if using CUDA)
- **Problem**: CUDA not available in container
- **Solution**: Add GPU support to docker-compose.yml
- **Test**: CUDA availability check

### 4. Import Path Issues
- **Problem**: Python can't find shared modules
- **Solution**: Fix PYTHONPATH in Dockerfile
- **Test**: All import statements

## 🔧 Docker-Compose Updates Needed

```yaml
# Add to docker-compose.yml if not present
worker:
  environment:
    - PYTHONPATH=/app:/app/shared
  volumes:
    - ./shared:/app/shared:ro  # Mount shared modules
```

## 📊 Success Criteria

### ✅ Phase 1: Environment
- [ ] All containers build successfully
- [ ] No import errors on startup
- [ ] Environment variables loaded

### ✅ Phase 2: Shared Modules  
- [ ] Configuration loads without errors
- [ ] Models validate correctly
- [ ] Utilities function properly

### ✅ Phase 3: Backend
- [ ] API starts and responds
- [ ] Health checks pass
- [ ] Routes accessible

### ✅ Phase 4: Worker
- [ ] LayoutParser loads models
- [ ] Translation components work
- [ ] Celery connects to Redis

### ✅ Phase 5: Integration
- [ ] File upload works
- [ ] Translation tasks execute
- [ ] PDF output generated

## 🎯 Priority Order

1. **Fix any blocking import issues first**
2. **Verify LayoutParser works in container**
3. **Test basic PDF processing pipeline**
4. **Full end-to-end validation**

This approach ensures we test in the proper environment from the start!