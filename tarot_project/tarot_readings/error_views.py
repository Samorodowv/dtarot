from django.shortcuts import render
from django.http import HttpResponseServerError, HttpResponseNotFound, HttpResponseForbidden, HttpResponseBadRequest
import logging

logger = logging.getLogger(__name__)

def custom_400(request, exception=None):
    """Handle Bad Request errors"""
    logger.warning(f"400 Bad Request: {request.path}", exc_info=exception)
    return HttpResponseBadRequest(render(request, 'tarot_readings/errors/400.html', {
        'error_message': 'Неверный запрос. Пожалуйста, проверьте введенные данные.'
    }))

def custom_403(request, exception=None):
    """Handle Forbidden errors"""
    logger.warning(f"403 Forbidden: {request.path}", exc_info=exception)
    return HttpResponseForbidden(render(request, 'tarot_readings/errors/403.html', {
        'error_message': 'Доступ запрещен. У вас нет прав для просмотра этой страницы.'
    }))

def custom_404(request, exception=None):
    """Handle Not Found errors"""
    logger.info(f"404 Not Found: {request.path}")
    return HttpResponseNotFound(render(request, 'tarot_readings/errors/404.html', {
        'error_message': 'Страница не найдена. Возможно, она была перемещена или удалена.'
    }))

def custom_500(request):
    """Handle Server errors"""
    logger.error(f"500 Server Error: {request.path}", exc_info=True)
    return HttpResponseServerError(render(request, 'tarot_readings/errors/500.html', {
        'error_message': 'Произошла внутренняя ошибка сервера. Мы уже работаем над ее устранением.'
    }))