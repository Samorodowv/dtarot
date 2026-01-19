"""
Monitoring and performance tracking utilities
"""

import time
import logging
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.core.cache import cache
import sentry_sdk

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to monitor request performance and log slow requests
    """
    
    def process_request(self, request):
        """Start timing the request"""
        request._start_time = time.time()
        request._queries_before = len(connection.queries)
        
    def process_response(self, request, response):
        """Log performance metrics after request"""
        if not getattr(settings, 'MONITORING_ENABLED', False):
            return response
            
        if not hasattr(request, '_start_time'):
            return response
            
        # Calculate timing
        duration = time.time() - request._start_time
        queries_count = len(connection.queries) - request._queries_before
        
        # Log slow requests
        slow_threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD', 5.0)
        if duration > slow_threshold:
            logger.warning(
                f"Slow request detected: {request.method} {request.path} "
                f"took {duration:.2f}s with {queries_count} queries"
            )
            
            # Add to Sentry if available
            with sentry_sdk.configure_scope() as scope:
                scope.set_tag("slow_request", True)
                scope.set_extra("request_duration", duration)
                scope.set_extra("query_count", queries_count)
                scope.set_extra("request_path", request.path)
                scope.set_extra("request_method", request.method)
                
        # Log query performance
        slow_query_threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD', 1.0)
        for query in connection.queries[request._queries_before:]:
            query_time = float(query['time'])
            if query_time > slow_query_threshold:
                logger.warning(
                    f"Slow query detected: {query_time:.3f}s - {query['sql'][:100]}..."
                )
                
        # Add performance headers for debugging
        if settings.DEBUG:
            response['X-Response-Time'] = f"{duration:.3f}s"
            response['X-Query-Count'] = str(queries_count)
            
        return response


class MonitoringUtils:
    """
    Utility class for monitoring and metrics collection
    """
    
    @staticmethod
    def track_reading_creation():
        """Track reading creation metrics"""
        try:
            current_count = cache.get('readings_today', 0)
            cache.set('readings_today', current_count + 1, 86400)  # 24 hours
            
            # Track in Sentry
            with sentry_sdk.configure_scope() as scope:
                scope.set_tag("event_type", "reading_created")
                scope.set_extra("daily_count", current_count + 1)
                
        except Exception as e:
            logger.error(f"Error tracking reading creation: {e}")
            
    @staticmethod
    def track_interpretation_time(reading_id, duration):
        """Track interpretation generation time"""
        try:
            logger.info(f"Interpretation for reading {reading_id} took {duration:.2f}s")
            
            # Store average interpretation time
            cache_key = 'avg_interpretation_time'
            current_avg = cache.get(cache_key, 0)
            current_count = cache.get('interpretation_count', 0)
            
            new_count = current_count + 1
            new_avg = ((current_avg * current_count) + duration) / new_count
            
            cache.set(cache_key, new_avg, 3600)  # 1 hour
            cache.set('interpretation_count', new_count, 3600)
            
            # Track in Sentry
            with sentry_sdk.configure_scope() as scope:
                scope.set_tag("event_type", "interpretation_completed")
                scope.set_extra("interpretation_duration", duration)
                scope.set_extra("reading_id", reading_id)
                
        except Exception as e:
            logger.error(f"Error tracking interpretation time: {e}")
            
    @staticmethod
    def track_error(error_type, error_message, context=None):
        """Track application errors"""
        try:
            logger.error(f"{error_type}: {error_message}", extra=context or {})
            
            # Increment error counter
            error_key = f"errors_{error_type}_today"
            current_count = cache.get(error_key, 0)
            cache.set(error_key, current_count + 1, 86400)  # 24 hours
            
            # Track in Sentry
            with sentry_sdk.configure_scope() as scope:
                scope.set_tag("error_type", error_type)
                scope.set_extra("error_message", error_message)
                if context:
                    for key, value in context.items():
                        scope.set_extra(key, value)
                        
            sentry_sdk.capture_message(f"{error_type}: {error_message}", level='error')
            
        except Exception as e:
            logger.error(f"Error tracking error: {e}")
            
    @staticmethod
    def get_daily_stats():
        """Get daily application statistics"""
        try:
            stats = {
                'readings_today': cache.get('readings_today', 0),
                'avg_interpretation_time': cache.get('avg_interpretation_time', 0),
                'interpretation_count': cache.get('interpretation_count', 0),
                'errors_gigachat_today': cache.get('errors_gigachat_today', 0),
                'errors_database_today': cache.get('errors_database_today', 0),
                'errors_timeout_today': cache.get('errors_timeout_today', 0),
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return {}
            
    @staticmethod
    def health_check():
        """Perform application health check"""
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'checks': {}
        }
        
        try:
            # Database check
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                health_status['checks']['database'] = 'ok'
        except Exception as e:
            health_status['checks']['database'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
            
        try:
            # Cache check
            cache.set('health_check', 'ok', 60)
            if cache.get('health_check') == 'ok':
                health_status['checks']['cache'] = 'ok'
            else:
                health_status['checks']['cache'] = 'error: cache not working'
                health_status['status'] = 'unhealthy'
        except Exception as e:
            health_status['checks']['cache'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
            
        try:
            # Celery check (basic)
            from tarot_readings.tasks import cache_card_data
            # Just check if task can be imported
            health_status['checks']['celery'] = 'ok'
        except Exception as e:
            health_status['checks']['celery'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
            
        try:
            # GigaChat credentials check
            from decouple import config
            credentials = config('GIGACHAT_API_CREDENTIALS', default='')
            if credentials:
                health_status['checks']['gigachat'] = 'configured'
            else:
                health_status['checks']['gigachat'] = 'not configured'
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['checks']['gigachat'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
            
        return health_status


class SentryContextProcessor:
    """
    Context processor to add monitoring data to Sentry
    """
    
    @staticmethod
    def add_user_context(request):
        """Add user context to Sentry"""
        if not hasattr(request, 'session'):
            return
            
        try:
            with sentry_sdk.configure_scope() as scope:
                # Add session info (without PII)
                scope.set_user({
                    "session_key": request.session.session_key,
                    "is_authenticated": False,  # No user auth in this app
                })
                
                # Add request context
                scope.set_tag("user_agent", request.META.get('HTTP_USER_AGENT', '')[:100])
                scope.set_tag("request_method", request.method)
                scope.set_extra("request_path", request.path)
                scope.set_extra("request_url", request.build_absolute_uri())
                
                # Add custom app context
                scope.set_tag("app_section", "tarot_readings")
                scope.set_extra("session_exists", bool(request.session.session_key))
                
        except Exception as e:
            logger.error(f"Error adding Sentry context: {e}")


def setup_monitoring():
    """
    Setup monitoring for the application
    """
    if not getattr(settings, 'MONITORING_ENABLED', False):
        return
        
    logger.info("Monitoring setup completed")
    
    # Log application startup
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("event_type", "application_startup")
        scope.set_extra("debug", settings.DEBUG)
        scope.set_extra("environment", getattr(settings, 'ENVIRONMENT', 'unknown'))
        
    sentry_sdk.capture_message("Tarot application started", level='info')