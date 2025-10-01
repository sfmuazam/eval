import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import json

# More secure regex patterns to prevent catastrophic backtracking
# Match script tags with bounded repetitions and specific character classes
SCRIPT_PATTERN = re.compile(r'<\s*script[^>]{0,1000}>[^<]{0,10000}<\s*/\s*script\s*>', re.IGNORECASE)
# Additional patterns for common XSS vectors
ONCLICK_PATTERN = re.compile(r'on\w+\s*=\s*["\'][^"\']{0,1000}["\']', re.IGNORECASE)
JAVASCRIPT_PATTERN = re.compile(r'javascript\s*:[^"\'\s]{0,1000}', re.IGNORECASE)

def sanitize_value(value):
    if isinstance(value, str):
        # Remove script tags using secure pattern
        value = re.sub(SCRIPT_PATTERN, '', value)
        # Remove event handlers like onclick, onload, etc.
        value = re.sub(ONCLICK_PATTERN, '', value)
        # Remove javascript: protocol
        value = re.sub(JAVASCRIPT_PATTERN, '', value)
        # Remove remaining angle brackets as a final safety measure
        value = value.replace('<', '&lt;').replace('>', '&gt;')
        return value
    elif isinstance(value, dict):
        return {k: sanitize_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_value(v) for v in value]
    return value

class XSSSanitizerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        query_params = dict(request.query_params)
        sanitized_query = {k: sanitize_value(v) for k, v in query_params.items()}
        request._query_params = sanitized_query

        if request.headers.get('content-type', '').startswith('application/json'):
            body = await request.body()
            try:
                data = json.loads(body)
                sanitized_data = sanitize_value(data)
                request._body = json.dumps(sanitized_data).encode()
            except Exception:
                pass
        response = await call_next(request)
        return response
