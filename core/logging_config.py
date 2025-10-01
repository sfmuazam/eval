# logging_config.py
import logging
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict
from settings import TZ
from pytz import timezone

class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter untuk output log yang terstruktur.
    Ideal untuk container environment seperti OpenShift.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log data
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone(TZ)),
            "level": record.levelname,
            "logger_name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
        }
        
        # Add process info
        log_data["process_id"] = record.process
        
        # Add environment info
        environment = os.environ.get("ENVIRONTMENT", "development")
        log_data["environment"] = environment
        
        # Add application info
        log_data["application"] = "be-sercvice"
        log_data["version"] = os.environ.get("APP_VERSION", "1.0.0")
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
            
        if hasattr(record, 'endpoint'):
            log_data["endpoint"] = record.endpoint
            
        if hasattr(record, 'method'):
            log_data["method"] = record.method
            
        if hasattr(record, 'status_code'):
            log_data["status_code"] = record.status_code
            
        if hasattr(record, 'response_time'):
            log_data["response_time_ms"] = record.response_time
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                          'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process', 'getMessage']:
                if not key.startswith('_'):
                    log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class OpenShiftLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter untuk menambahkan context khusus OpenShift.
    """
    
    def process(self, msg, kwargs):
        # Add pod and namespace info if available
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
            
        kwargs['extra']['pod_name'] = os.environ.get('HOSTNAME', 'unknown')
        kwargs['extra']['namespace'] = os.environ.get('POD_NAMESPACE', 'default')
        kwargs['extra']['node_name'] = os.environ.get('NODE_NAME', 'unknown')
        
        return msg, kwargs


def setup_logging():
    """
    Setup logging configuration untuk OpenShift environment.
    """
    # Determine log level from environment
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler untuk stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Use JSON formatter untuk structured logging
    json_formatter = JSONFormatter()
    console_handler.setFormatter(json_formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Disable propagation for third-party loggers to avoid noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    return root_logger


# Initialize logging
setup_logging()

# Create main application logger
logger = OpenShiftLoggerAdapter(logging.getLogger("be-service"), {})

# Create specific loggers for different components
auth_logger = OpenShiftLoggerAdapter(logging.getLogger("be-service.auth"), {})
scheduler_logger = OpenShiftLoggerAdapter(logging.getLogger("be-service.scheduler"), {})

# Tambahkan file handler agar log juga tersimpan ke file
import os
def _ensure_log_dir(log_file):
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

from core.logging_config import JSONFormatter  # avoid circular import if needed
import logging

def add_file_handler(logger_name: str, log_file: str, level: str = None):
    _ensure_log_dir(log_file)
    logger = logging.getLogger(logger_name)
    if not level:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, level, logging.INFO))
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    return logger

# Aktifkan file handler untuk logger utama dan auth
add_file_handler("be-service", "logs/file.log")
add_file_handler("be-service.auth", "logs/auth.log")
add_file_handler("be-service.scheduler", "logs/scheduler.log")


def log_request(request_id: str, method: str, endpoint: str, user_id: str = None):
    """
    Log incoming request dengan context.
    """
    logger.info(
        f"Incoming request: {method} {endpoint}",
        extra={
            "request_id": request_id,
            "method": method,
            "endpoint": endpoint,
            "user_id": user_id,
            "event_type": "request_start"
        }
    )


def log_response(request_id: str, status_code: int, response_time: float, user_id: str = None):
    """
    Log response dengan metrics.
    """
    logger.info(
        f"Request completed with status {status_code}",
        extra={
            "request_id": request_id,
            "status_code": status_code,
            "response_time": response_time,
            "user_id": user_id,
            "event_type": "request_end"
        }
    )


def log_error(request_id: str, error: Exception, user_id: str = None, context: Dict[str, Any] = None):
    """
    Log error dengan detail context.
    """
    extra_data = {
        "request_id": request_id,
        "user_id": user_id,
        "event_type": "error",
        "error_type": type(error).__name__
    }
    
    if context:
        extra_data.update(context)
    
    logger.error(
        f"Error occurred: {str(error)}",
        exc_info=True,
        extra=extra_data
    )


def log_security_event(event_type: str, user_id: str = None, ip_address: str = None, 
                      details: Dict[str, Any] = None):
    """
    Log security events untuk monitoring.
    """
    extra_data = {
        "event_type": "security_event",
        "security_event_type": event_type,
        "user_id": user_id,
        "ip_address": ip_address
    }
    
    if details:
        extra_data.update(details)


def log_business_event(event_type: str, user_id: str = None, details: Dict[str, Any] = None):
    """
    Log business events untuk analytics.
    """
    extra_data = {
        "event_type": "business_event",
        "business_event_type": event_type,
        "user_id": user_id
    }
    
    if details:
        extra_data.update(details)
    
    logger.info(
        f"Business event: {event_type}",
        extra=extra_data
    )
