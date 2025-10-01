# Backend Service AI

Backend service berbasis FastAPI, mendukung PostgreSQL, Redis, Sentry, Minio/local file storage, dan autentikasi JWT. Dirancang untuk aplikasi enterprise yang skalabel, aman, dan mudah dipelihara.

## Fitur

- FastAPI (async, modular)
- PostgreSQL (SQLAlchemy/asyncpg)
- Redis
- Minio (opsional, untuk file storage)
- Sentry (opsional, untuk monitoring)
- JWT Authentication

## Kebutuhan

- Python 3.11+
- PostgreSQL
- Redis
- Minio (opsional, untuk file storage)

## Instalasi

1. Clone repository:
   ```bash
   git clone <repo-url>
   cd fastapi-skeleton-main
   ```
2. Install dependencies:
   ```bash
   pip install uv
   uv python pin 3.13
   uv sync
   ```
3. Salin `.env.example` ke `.env` dan sesuaikan variabel lingkungan (lihat `settings.py`).
4. Setting PostgreSQL:
   ```sql
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   CREATE EXTENSION IF NOT EXISTS pg_trgm;
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
5. Jalankan migrasi database jika diperlukan:
   ```bash
   uv run python migrate.py
   ```

## Penggunaan

Menjalankan server FastAPI dengan Uvicorn:

```bash
uv run uvicorn main:app --reload
```
atau
```bash
uv run fastapi dev main.py
```

Server berjalan di `http://localhost:8000`  
Dokumentasi API di `http://localhost:8000/docs`

Menambah library baru:
```bash
uv add <library-name>
uv sync
```

## Skema Alur Penggunaan

### A. Offline (tanpa koneksi internet)
- `.env`: EMBED_PROVIDER=mock, LLM_PROVIDER, USE_LLM=0
- POST `/rag/seed-demo`
- Upload CV & project → POST `/upload`
- Enqueue → POST `/evaluate`
- Poll hasil → GET `/result/{job_id}?debug=true`

### B. Dengan Groq LLM + mock embeddings
- `.env`: EMBED_PROVIDER=mock, USE_LLM=1, set GROQ_API_KEY
- Alur sama seperti di atas

### C. Dengan Groq embeddings + Groq LLM
- `.env`: EMBED_PROVIDER=groq, EMBED_MODEL=text-embedding-3-small, set GROQ_API_KEY
- Seed/upload RAG, upload kandidat, evaluasi, ambil hasil

## Endpoints Utama

- `/docs` : Swagger UI (hanya untuk development)
- `/health` : Health check
- `/ready` : Readiness check

### Seed Demo RAG Docs (Quick Start)
- **POST** `/rag/seed-demo`  
  Menambahkan Backend JD dan dua rubrik (CV & Project) untuk mencoba pipeline.

### Upload Rubrik/JD ke Vector DB
- **POST** `/rag/upload`  
  Content-Type: multipart/form-data  
  Form fields:
    - `doc_type`: rubric | job_desc
    - `file`: PDF/DOCX/TXT
    - `title`: (opsional) string
    - `tags`: (opsional) comma-separated, contoh: "backend,cv"

### Upload File Kandidat
- **POST** `/upload`  
  Content-Type: multipart/form-data  
  Files:
    - `cv`: PDF/DOCX/TXT
    - `project_report`: PDF/DOCX/TXT

  Response:
  ```json
  { "upload_id": "<uuid>", "cv_path": "cv_xxx.pdf", "report_path": "report_xxx.pdf" }
  ```

### Evaluasi (Enqueue)
- **POST** `/evaluate`  
  Content-Type: application/json  
  ```json
  { "upload_id": "<uuid-from-upload>" }
  ```
  Response:
  ```json
  { "id": "<job_id>", "status": "queued|processing" }
  ```

### Ambil Hasil
- **GET** `/result/{job_id}?debug=true`  
  Status "completed" + objek hasil.  
  Dengan `debug=true`, dapatkan detail internal (skor, warning, response LLM, dll).

## Struktur Proyek

- `main.py` : Entry point & setup FastAPI
- `core/` : Utilities, logging, email, security, middleware
- `models/` : SQLAlchemy ORM models
- `repository/` : Data access/repository pattern
- `routes/` : FastAPI routers (auth, dll)
- `schemas/` : Pydantic schemas untuk request/response
- `tests/` : Unit & integration tests (pytest)
- `settings.py` : Konfigurasi & environment variables
- `requirements.txt` atau `uv.lock` : Dependencies Python
- `Dockerfile` : Containerization support
- `.env.example` : Contoh konfigurasi environment

---