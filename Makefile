# PDF Translator Development Makefile

.PHONY: help install install-dev install-all clean lint format test test-unit test-integration run-backend run-worker run-all build docker-build docker-up docker-down

# Default target
help:
	@echo "PDF Translator Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  install      Install production dependencies"
	@echo "  install-dev  Install development dependencies"
	@echo "  install-all  Install all dependencies including optional"
	@echo ""
	@echo "Development Commands:"
	@echo "  clean        Clean up temporary files and caches"
	@echo "  lint         Run linting (flake8, mypy)"
	@echo "  format       Format code (black, isort)"
	@echo "  test         Run all tests"
	@echo "  test-unit    Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo ""
	@echo "Run Commands:"
	@echo "  run-backend  Start FastAPI backend server"
	@echo "  run-worker   Start Celery worker"
	@echo "  run-all      Start both backend and worker"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build Build Docker images"
	@echo "  docker-up    Start all services with Docker Compose"
	@echo "  docker-down  Stop all Docker services"
	@echo ""

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[dev,layout,lang]"

# Development
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/

lint:
	@echo "Running flake8..."
	flake8 shared/ backend/ worker/
	@echo "Running mypy..."
	mypy shared/ backend/ worker/

format:
	@echo "Running black..."
	black shared/ backend/ worker/
	@echo "Running isort..."
	isort shared/ backend/ worker/

# Testing
test:
	pytest

test-unit:
	pytest -m "unit"

test-integration:
	pytest -m "integration"

test-coverage:
	pytest --cov=shared --cov=backend --cov=worker --cov-report=html

# Local development
run-backend:
	cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-worker:
	cd worker && celery -A tasks worker --loglevel=info

run-all:
	@echo "Starting Redis, Backend, and Worker..."
	@echo "Make sure Redis is running on localhost:6379"
	# Run backend and worker in parallel
	make run-backend & make run-worker & wait

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Services started. Check status with: docker-compose ps"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:80"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Development setup
dev-setup: install-dev
	@echo "Development environment setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Copy .env.example to .env and configure"
	@echo "2. Ensure Redis is running"
	@echo "3. Run 'make run-all' to start services"

# Production build
build:
	python -m build

# Health checks
check-redis:
	@redis-cli ping || echo "Redis not running. Start with: redis-server"

check-deps:
	@echo "Checking critical dependencies..."
	@python -c "import fastapi; print('✓ FastAPI installed')"
	@python -c "import celery; print('✓ Celery installed')"
	@python -c "import redis; print('✓ Redis client installed')"
	@python -c "import pdf2image; print('✓ PDF2Image installed')"
	@python -c "import reportlab; print('✓ ReportLab installed')"
	@echo "All critical dependencies are installed!"

# Database/Storage setup
setup-folders:
	mkdir -p uploads/
	mkdir -p translated/
	mkdir -p temp/
	@echo "Required folders created successfully!"