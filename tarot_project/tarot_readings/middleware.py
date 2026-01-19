from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add additional security headers to all responses
    """
    def process_response(self, request, response):
        # Only add headers if not in DEBUG mode
        if not settings.DEBUG:
            # Prevent MIME type sniffing
            response['X-Content-Type-Options'] = 'nosniff'
            
            # Enable XSS protection in older browsers
            response['X-XSS-Protection'] = '1; mode=block'
            
            # Clickjacking protection
            if 'X-Frame-Options' not in response:
                response['X-Frame-Options'] = 'DENY'
            
            # Referrer Policy
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Feature Policy / Permissions Policy
            response['Permissions-Policy'] = (
                'accelerometer=(), camera=(), geolocation=(), '
                'gyroscope=(), magnetometer=(), microphone=(), '
                'payment=(), usb=()'
            )
            
            # Content Security Policy (basic, can be customized)
            if 'Content-Security-Policy' not in response:
                csp_directives = [
                    "default-src 'self'",
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com",
                    "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com",
                    "img-src 'self' data: https:",
                    "font-src 'self' data:",
                    "connect-src 'self'",
                    "frame-ancestors 'none'",
                    "base-uri 'self'",
                    "form-action 'self'"
                ]
                response['Content-Security-Policy'] = '; '.join(csp_directives)
        
        return response