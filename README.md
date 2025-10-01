
# Backend Service AI

Backend service built with FastAPI, supporting PostgreSQL, Redis, Sentry, Minio/local file storage, and JWT authentication. Designed for scalable, secure, and maintainable enterprise applications.

## Features

- FastAPI (async, modular)
- PostgreSQL (SQLAlchemy/asyncpg)
- Redis (token/cache)
- Sentry (error monitoring)
- Minio/local file storage
- JWT authentication (access/refresh tokens)
- Role & permission management
- Modular repository pattern
- Custom logging & security middleware
- Health/readiness endpoints for OpenShift
- XSS & security headers middleware
- Cron/scheduled tasks
- Email (SMTP) integration

## Requirements

- Python 3.11+
- PostgreSQL
- Redis
- Minio (optional, for file storage)

## Installation

1. Clone this repository:
   ```bash
   git clone <repo-url>
   cd be-backend-dev
   ```
2. Install dependencies:
   ```bash
   pip install uv
   uv python pin 3.13
   uv sync
   ```
3. Copy `.env.example` to `.env` and adjust environment variables as needed (see `settings.py`).
4. Setting PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;
5. Run database migration if needed:
   ```bash
   uv run python migrate.py
   ```
## Usage

Start FastAPI server with Uvicorn:

```bash
uv run uvicorn main:app --reload
```
or
```bash
uv run fastapi dev main.py
```

Server runs at `http://localhost:8000`.
Docs at `http://localhost:8000/docs`.

Add new library:
```bash
uv add <library-name>
uv sync
```

Typical Flows

A) Fully offline (no network):

.env: EMBED_PROVIDER=mock, LLM_PROVIDER, USE_LLM=0

POST /rag/seed-demo

Upload sample CV & project → POST /upload

Enqueue → POST /evaluate

Poll result → GET /result/{job_id}?debug=true

B) With Groq LLM + mock embeddings:

.env: EMBED_PROVIDER=mock, USE_LLM=1, set GROQ_API_KEY

Same flow as above.

C) With Groq embeddings + Groq LLM:

.env: EMBED_PROVIDER=groq, EMBED_MODEL=text-embedding-3-small, set GROQ_API_KEY

Seed/upload RAG, upload candidate, evaluate, get result.

## Endpoints

- `/docs` : Swagger UI (development only)
- `/health` : Health check
- `/ready` : Readiness check
- etc
Seed demo RAG docs (quick start)
POST /rag/seed-demo


Inserts a basic Backend JD and two rubrics (CV & Project). Useful to try the pipeline immediately.

Upload custom rubric / JD to vector DB
POST /rag/upload
Content-Type: multipart/form-data
Form fields:
  - doc_type: rubric | job_desc
  - file: (PDF/DOCX/TXT)
  - title: (optional) string
  - tags: (optional) comma-separated, e.g. "backend,cv"

Upload candidate files
POST /upload
Content-Type: multipart/form-data
Files:
  - cv: (PDF/DOCX/TXT)
  - project_report: (PDF/DOCX/TXT)


Response:

{ "upload_id": "<uuid>", "cv_path": "cv_xxx.pdf", "report_path": "report_xxx.pdf" }

Evaluate (enqueue)
POST /evaluate
Content-Type: application/json

{ "upload_id": "<uuid-from-upload>" }


Response (job queued/processing):

{ "id": "<job_id>", "status": "queued|processing" }

Get result
GET /result/{job_id}?debug=true


When done: status="completed" + result object.

With debug=true, you also get internal details (scores breakdown, warnings, raw LLM responses, etc.).
## Project Structure

- `main.py` : App entry point & FastAPI setup
- `core/` : Utilities, logging, email, security, middleware
- `models/` : SQLAlchemy ORM models
- `repository/` : Data access/repository pattern
- `routes/` : FastAPI routers (auth, etc.)
- `schemas/` : Pydantic schemas for request/response
- `tests/` : Pytest-based unit & integration tests
- `settings.py` : Configuration & environment variables
- `requirements.txt` or `uv.lock` : Python dependencies
- `Dockerfile` : Containerization support
- `.env.example` : Example environment config
