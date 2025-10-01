"""
Security Headers Middleware for FastAPI
Implements security headers including HSTS and X-Content-Type-Options
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware untuk menambahkan security headers pada setiap response.
    
    Headers yang ditambahkan:
    - Strict-Transport-Security: Memaksa penggunaan HTTPS
    - X-Content-Type-Options: nosniff - Mencegah MIME type sniffing
    - Cookie Security: Secure, HttpOnly, SameSite attributes
    """
    
    def __init__(
        self,
        app,
        hsts_max_age: int = 31536000,  # 1 year in seconds
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = True,
        secure_cookies: bool = True,
        httponly_cookies: bool = True,
        samesite_cookies: str = "Strict"
    ):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.secure_cookies = secure_cookies
        self.httponly_cookies = httponly_cookies
        self.samesite_cookies = samesite_cookies
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request dan menambahkan security headers pada response
        """
        # Process request
        response = await call_next(request)
        
        # Add Strict-Transport-Security header
        hsts_value = f"max-age={self.hsts_max_age}"
        if self.hsts_include_subdomains:
            hsts_value += "; includeSubDomains"
        if self.hsts_preload:
            hsts_value += "; preload"
        
        response.headers["Strict-Transport-Security"] = hsts_value
        
        # Add X-Content-Type-Options header
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Add Cookie Security Headers
        self._secure_cookies(response)
        
        return response
    
    def _secure_cookies(self, response: Response) -> None:
        """
        Apply security attributes to all cookies in the response
        """
        if hasattr(response, 'set_cookie'):
            # For any cookies that might be set via response.set_cookie()
            # This will be handled when cookies are actually set
            pass
        
        # Check if there are cookies in headers and modify them
        if 'set-cookie' in response.headers:
            cookies = response.headers.getlist('set-cookie')
            response.headers.pop('set-cookie')
            
            for cookie in cookies:
                secured_cookie = self._add_security_attributes(cookie)
                response.headers.append('set-cookie', secured_cookie)
    
    def _add_security_attributes(self, cookie_str: str) -> str:
        """
        Add security attributes to cookie string
        """
        cookie_parts = cookie_str.split(';')
        cookie_value = cookie_parts[0].strip()
        
        # Remove existing security attributes to avoid duplicates
        existing_attributes = []
        for part in cookie_parts[1:]:
            part = part.strip().lower()
            if not any(attr in part for attr in ['secure', 'httponly', 'samesite']):
                existing_attributes.append(cookie_parts[cookie_parts.index(part.capitalize())])
        
        # Build new cookie with security attributes
        secured_parts = [cookie_value] + existing_attributes
        
        if self.secure_cookies:
            secured_parts.append('Secure')
        
        if self.httponly_cookies:
            secured_parts.append('HttpOnly')
        
        if self.samesite_cookies:
            secured_parts.append(f'SameSite={self.samesite_cookies}')
        
        return '; '.join(secured_parts)
