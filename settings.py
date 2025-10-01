import os
from core.utils import str_to_bool

if os.environ.get("ENVIRONTMENT") != "prod":
    from dotenv import load_dotenv
    load_dotenv()

# App
ENVIRONTMENT = os.environ.get("ENVIRONTMENT", "dev")
APPSNAME = os.environ.get("APPSNAME", "backend-dev")
TZ = os.environ.get("TZ", "Asia/Jakarta")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-dev-secret")
BACKEND_URL = os.environ.get("BACKEND_URL", "")

# CORS
_raw_cors = os.environ.get("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS = [s.strip() for s in _raw_cors.split(",") if s.strip()]

# Storage
FILE_STORAGE_ADAPTER = os.environ.get("FILE_STORAGE_ADAPTER", "local")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")

# Database
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 55432))
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "")
DB_NAME = os.environ.get("DB_NAME", "cv_eval")
DEFAULT_SCHEMA = os.environ.get("DEFAULT_SCHEMA", "public")

# RAG / Embeddings
EMBED_OPS = os.environ.get("EMBED_OPS", "l2").lower()

# LLM
USE_LLM = os.environ.get("USE_LLM", "1")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
LLM_TIMEOUT_SEC = int(os.environ.get("LLM_TIMEOUT_SEC", 30))
LLM_RETRIES = int(os.environ.get("LLM_RETRIES", 1))
LLM_FAILOPEN = os.environ.get("LLM_FAILOPEN", "1")

# Observability / Scheduler
SENTRY_DSN = os.environ.get("SENTRY_DSN")
SENTRY_TRACES_SAMPLE_RATES = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATES", "1.0"))
CRON_SCHEDULER = os.environ.get("CRON_SCHEDULER", "59 23 * * *")
