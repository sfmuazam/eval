import os
from core.utils import getenv_bool, getenv_int, getenv_float

if os.environ.get("ENVIRONTMENT", "dev") != "prod":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

ENVIRONTMENT = os.getenv("ENVIRONTMENT", "dev")
APPSNAME = os.getenv("APPSNAME", "backend-dev")
TZ = os.getenv("TZ", "Asia/Jakarta")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-dev-secret")
CORS_ALLOWED_ORIGINS = [x for x in os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",") if x]

FILE_STORAGE_ADAPTER = os.getenv("FILE_STORAGE_ADAPTER", "local")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = getenv_int("DB_PORT", 55432)
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "cv_eval")
DEFAULT_SCHEMA = os.getenv("DEFAULT_SCHEMA", "public")

EMBED_OPS = os.getenv("EMBED_OPS", "l2")
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "mock")
EMBED_DIM = getenv_int("EMBED_DIM", 768)
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "https://api.groq.com/openai/v1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

USE_LLM = getenv_bool("USE_LLM", True)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_TIMEOUT_SEC = getenv_float("LLM_TIMEOUT_SEC", 30.0)
LLM_RETRIES = getenv_int("LLM_RETRIES", 1)
LLM_FAILOPEN = getenv_bool("LLM_FAILOPEN", True)

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
