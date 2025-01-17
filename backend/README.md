# PDF Translator Backend

Backend en FastAPI para el servicio de traducción de PDFs.

## Instalación

1. Crear un entorno virtual:
```bash
python -m venv venv
```

2. Activar el entorno virtual:
- Windows:
```bash
.\venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Ejecutar el servidor

```bash
uvicorn main:app --reload
```

El servidor estará disponible en http://localhost:8000

## API Endpoints

### POST /pdfs/translate
Sube un archivo PDF para traducir.
- Request: `multipart/form-data` con el archivo PDF
- Response: `{ "taskId": "string" }`

### GET /pdfs/status/{task_id}
Obtiene el estado de una tarea de traducción.
- Response: 
```json
{
  "id": "string",
  "status": "pending|processing|completed|failed",
  "originalFile": "string",
  "translatedFile": "string|null",
  "error": "string|null"
}
```

### GET /pdfs/download/{task_id}
Descarga el PDF traducido.
- Response: Archivo PDF traducido
- Errores:
  - 404: Si la tarea no existe o el archivo no se encuentra
  - 400: Si la traducción no está completa

## Estructura de directorios

- `/uploads`: Almacena los PDFs originales subidos
- `/translated`: Almacena los PDFs traducidos

## Notas para desarrollo

- La API usa almacenamiento en memoria para las tareas. En producción, usar una base de datos.
- CORS está configurado para desarrollo local (localhost:5173).
- Los workers para traducción serán implementados posteriormente.
