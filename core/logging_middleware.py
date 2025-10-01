# logging_middleware.py
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
import json

from core.logging_config import log_request, log_response, log_error, logger


class LoggingMiddleware:
    """
    Middleware untuk logging semua request dan response.
    Cocok untuk monitoring di OpenShift environment.
    """
    
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Extract request info
        method = request.method
        url = str(request.url)
        endpoint = request.url.path
        user_agent = request.headers.get("user-agent", "")
        ip_address = self._get_client_ip(request)
        
        # Extract user ID if available (from JWT token or session)
        user_id = await self._extract_user_id(request)
        
        # Log incoming request
        log_request(
            request_id=request_id,
            method=method,
            endpoint=endpoint,
            user_id=user_id
        )
        
        # Log additional request details
        logger.info(
            "Request details",
            extra={
                "request_id": request_id,
                "url": url,
                "user_agent": user_agent,
                "ip_address": ip_address,
                "content_type": request.headers.get("content-type"),
                "content_length": request.headers.get("content-length"),
                "event_type": "request_details"
            }
        )

        # Process request
        response_body = b""
        status_code = 500
        
        async def send_wrapper(message):
            nonlocal response_body, status_code
            
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                response_body += message.get("body", b"")
            
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Log error
            log_error(
                request_id=request_id,
                error=e,
                user_id=user_id,
                context={
                    "endpoint": endpoint,
                    "method": method,
                    "ip_address": ip_address
                }
            )
            raise
        finally:
            # Calculate response time
            process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log response
            log_response(
                request_id=request_id,
                status_code=status_code,
                response_time=process_time,
                user_id=user_id
            )
            
            # Log response details
            logger.info(
                "Response details",
                extra={
                    "request_id": request_id,
                    "status_code": status_code,
                    "response_time": process_time,
                    "response_size": len(response_body),
                    "event_type": "response_details"
                }
            )

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request headers.
        Handles X-Forwarded-For header dari load balancer/proxy.
        """
        # Check for forwarded IP first (common in container environments)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request.client, 'host'):
            return request.client.host
            
        return "unknown"

    async def _extract_user_id(self, request: Request) -> str:
        """
        Extract user ID from JWT token atau session.
        """
        try:
            # Check Authorization header
            authorization = request.headers.get("authorization")
            if authorization and authorization.startswith("Bearer "):
                # Here you would decode the JWT token
                # For now, we'll return None
                # token = authorization.split(" ")[1]
                # decoded = decode_jwt_token(token)  # Implement this function
                # return decoded.get("user_id")
                pass
            
            # Check session or cookies
            # session_id = request.cookies.get("session_id")
            # if session_id:
            #     user_id = get_user_from_session(session_id)  # Implement this function
            #     return user_id
            
            return None
        except Exception as e:
            logger.warning(
                f"Failed to extract user ID: {str(e)}",
                extra={
                    "event_type": "auth_extraction_error",
                    "request_id": getattr(request.state, 'request_id', 'unknown')
                }
            )
            return None


# Health check logging
def log_health_check(component: str, status: str, details: dict = None):
    """
    Log health check results.
    """
    extra_data = {
        "event_type": "health_check",
        "component": component,
        "status": status
    }
    
    if details:
        extra_data.update(details)
    
    if status == "healthy":
        logger.info(f"Health check passed for {component}", extra=extra_data)
    else:
        logger.warning(f"Health check failed for {component}", extra=extra_data)


# Database operation logging
def log_db_operation(operation: str, table: str, duration: float, user_id: str = None, 
                    record_count: int = None, error: Exception = None):
    """
    Log database operations untuk monitoring performance.
    """
    extra_data = {
        "event_type": "database_operation",
        "operation": operation,
        "table": table,
        "duration_ms": duration,
        "user_id": user_id
    }
    
    if record_count is not None:
        extra_data["record_count"] = record_count
    
    if error:
        extra_data["error"] = str(error)
        logger.error(f"Database operation failed: {operation} on {table}", extra=extra_data)
    else:
        logger.info(f"Database operation completed: {operation} on {table}", extra=extra_data)


# Background task logging
def log_background_task(task_name: str, status: str, duration: float = None, 
                       error: Exception = None, details: dict = None):
    """
    Log background task execution.
    """
    extra_data = {
        "event_type": "background_task",
        "task_name": task_name,
        "status": status
    }
    
    if duration is not None:
        extra_data["duration_ms"] = duration
        
    if details:
        extra_data.update(details)
    
    if error:
        extra_data["error"] = str(error)
        logger.error(f"Background task failed: {task_name}", extra=extra_data, exc_info=True)
    elif status == "completed":
        logger.info(f"Background task completed: {task_name}", extra=extra_data)
    elif status == "started":
        logger.info(f"Background task started: {task_name}", extra=extra_data)
