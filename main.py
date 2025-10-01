from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.xss_sanitizer import XSSSanitizerMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from models import create_all, ensure_schema_and_extensions
import sentry_sdk
from core.myworker import run_scheduled_task
from contextlib import asynccontextmanager
from fastapi_utilities import repeat_at
from settings import (
    CORS_ALLOWED_ORIGINS,
    ENVIRONTMENT,
    TZ
)
from pytz import timezone
from core.logging_config import logger, log_security_event, scheduler_logger
from core.logging_middleware import LoggingMiddleware, log_background_task, log_health_check
from core.security_headers import SecurityHeadersMiddleware
from routes.router import router as api_router

from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request
import os
import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    logger.info("Application startup initiated", extra={"event_type": "app_startup"})
    
    try:
        log_health_check("application", "starting")
        
        # shceduler
        await ensure_schema_and_extensions()
        await create_all()


        logger.info("Application startup completed successfully", extra={"event_type": "app_startup_complete"})
        log_health_check("application", "healthy")
        
    except Exception as e:
        logger.error("Application startup failed", exc_info=True, extra={"event_type": "app_startup_error"})
        log_health_check("application", "unhealthy", {"error": str(e)})
        raise
    
    yield
    
    logger.info("Application shutdown initiated", extra={"event_type": "app_shutdown"})
    try:
        logger.info("Application shutdown completed", extra={"event_type": "app_shutdown_complete"})
    except Exception as e:
        logger.error("Application shutdown error", exc_info=True, extra={"event_type": "app_shutdown_error"})


fastapi_kwargs = {
    "title": "Backend Service",
    "swagger_ui_oauth2_redirect_url": "/docs/oauth2-redirect",
    "swagger_ui_init_oauth": {
        "clientId": "your-client-id",
        "authorizationUrl": "/auth/token",
        "tokenUrl": "/auth/token",
    },
    "lifespan": lifespan,  # Add the lifesapan handler
}
if ENVIRONTMENT == 'dev':
    fastapi_kwargs.update({
        "docs_url": "/docs",
        "redoc_url": None,
        "openapi_url": "/openapi.json",
    })
elif ENVIRONTMENT == 'prod':
    fastapi_kwargs.update({
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    })
app = FastAPI(**fastapi_kwargs)

app.add_middleware(LoggingMiddleware)

app.add_middleware(XSSSanitizerMiddleware)

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Data yang Anda masukkan tidak valid."},
    )

app.add_middleware(
    SecurityHeadersMiddleware,
    hsts_max_age=31536000,  # 1 year
    hsts_include_subdomains=True,
    hsts_preload=True,
    secure_cookies=True,
    httponly_cookies=True,
    samesite_cookies="Strict"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix="")



@app.get("/")
async def root():
    logger.info("Root endpoint accessed", extra={"event_type": "endpoint_access", "endpoint": "/"})
    return {"message": "Hi"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint untuk monitoring OpenShift.
    """
    try:
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone(TZ)),
            "version": os.environ.get("APP_VERSION", "1.0.0"),
            "environment": ENVIRONTMENT,
            "checks": {
                "application": "healthy",
                # "database": db_status,
                # "redis": redis_status
            }
        }
        
        log_health_check("application", "healthy")
        logger.info("Health check completed", extra={"event_type": "health_check", "status": "healthy"})
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", exc_info=True, extra={"event_type": "health_check_error"})
        log_health_check("application", "unhealthy", {"error": str(e)})
        
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone(TZ)),
                "error": str(e)
            }
        )

@app.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint untuk OpenShift.
    """
    try:
        
        logger.info("Readiness check completed", extra={"event_type": "readiness_check", "status": "ready"})
        
        return {
            "status": "ready",
            "timestamp": datetime.now(timezone(TZ)),
        }
        
    except Exception as e:
        logger.error("Readiness check failed", exc_info=True, extra={"event_type": "readiness_check_error"})
        
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "timestamp": datetime.now(timezone(TZ)),
                "error": str(e)
            }
        )

# 404 Handler untuk halaman yang tidak ditemukan
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    log_security_event(
        "page_not_found",
        ip_address=request.client.host if request.client else "unknown",
        details={
            "endpoint": request.url.path,
            "method": request.method,
            "request_id": request_id
        }
    )
    
    return JSONResponse(
        status_code=404,
        content={
            "error": "Page Not Found",
            "message": f"Halaman tidak ditemukan",
            "status_code": 404,
            "detail": "Endpoint yang Anda cari tidak tersedia. Silakan periksa kembali URL atau dokumentasi API.",
            "request_id": request_id
        }
    )

# Handler untuk method yang tidak diizinkan (405)
@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    log_security_event(
        "method_not_allowed",
        ip_address=request.client.host if request.client else "unknown",
        details={
            "endpoint": request.url.path,
            "method": request.method,
            "request_id": request_id
        }
    )
    
    return JSONResponse(
        status_code=405,
        content={
            "error": "Method Not Allowed",
            "message": f"Method tidak diizinkan untuk endpoint",
            "status_code": 405,
            "detail": "Method HTTP yang Anda gunakan tidak didukung untuk endpoint ini.",
            "request_id": request_id
        }
    )

DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('DB_PASS')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_NAME = os.environ.get('DB_NAME')