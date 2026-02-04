from django.shortcuts import render, redirect
from django.views.generic import CreateView, DetailView
from django.http import HttpResponse, Http404, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from .models import Card, Reading, CardPosition
from .forms import ReadingForm, PromoCodeForm
from .services import RateLimitService, CardService, ReadingService
from .tasks import interpret_reading
from .exceptions import InsufficientCardsException
from .monitoring import MonitoringUtils
from .interaction_logging import log_interaction
import random
import logging
from django.contrib import messages
from django.db import transaction

logger = logging.getLogger(__name__)

class GetReadingView(CreateView):
    model = Reading
    form_class = ReadingForm
    template_name = 'tarot_readings/reading.html'

    def get_initial(self):
        """Подставляем сохраненные значения из сессии"""
        initial = super().get_initial()
        if self.request.session.get('user_age'):
            initial['user_age'] = self.request.session['user_age']
        if self.request.session.get('user_gender'):
            initial['user_gender'] = self.request.session['user_gender']
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        session_key = self.request.session.session_key or self.request.session.create()
        kwargs['promo_applied'] = RateLimitService.is_promo_applied(session_key)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_key = self.request.session.session_key or self.request.session.create()
        
        # Check rate limiting with Redis
        can_create, time_left = RateLimitService.can_create_reading(session_key)
        promo_applied = RateLimitService.is_promo_applied(session_key)
        
        context['promo_applied'] = promo_applied
        context['can_create_reading'] = can_create
        
        if not can_create and time_left:
            minutes = int(time_left.total_seconds() // 60)
            seconds = int(time_left.total_seconds() % 60)
            context['cooldown'] = {
                'minutes': minutes,
                'seconds': seconds
            }
            context['promo_form'] = PromoCodeForm()
        
        return context

    def post(self, request, *args, **kwargs):
        session_key = request.session.session_key or request.session.create()
        
        # Проверяем, является ли это отправкой промокода
        if 'apply_promo' in request.POST:
            promo_form = PromoCodeForm(request.POST)
            if promo_form.is_valid():
                promo_code = promo_form.cleaned_data['promo_code']
                log_interaction(
                    source="web",
                    direction="in",
                    event_type="promo_apply",
                    user_identifier=str(session_key),
                    content=promo_code,
                )
                if RateLimitService.apply_promo_code(session_key, promo_code):
                    messages.success(request, 'Промокод успешно применен! Вы можете сделать расклад немедленно.')
                    log_interaction(
                        source="web",
                        direction="out",
                        event_type="promo_result",
                        user_identifier=str(session_key),
                        content="Промокод применен",
                    )
                else:
                    messages.error(request, 'Неверный промокод.')
                    log_interaction(
                        source="web",
                        direction="out",
                        event_type="promo_result",
                        user_identifier=str(session_key),
                        content="Неверный промокод",
                    )
            return redirect('tarot_readings:home')
        
        # Если это не промокод, обрабатываем основную форму
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        session_key = self.request.session.session_key or self.request.session.create()
        
        # Check rate limiting with Redis
        can_create, time_left = RateLimitService.can_create_reading(session_key)
        if not can_create:
            form.add_error(None, 'Вы можете сделать следующий расклад через час после предыдущего или используйте промокод.')
            return self.form_invalid(form)

        # Use database transaction for data consistency
        try:
            with transaction.atomic():
                # Save user data to session for convenience
                self.request.session['user_age'] = form.cleaned_data['user_age']
                self.request.session['user_gender'] = form.cleaned_data['user_gender']
                
                # Save reading
                reading = form.save(commit=False)
                
                # Set default question if empty
                if not reading.question.strip():
                    reading.question = "Общий расклад на ближайшее будущее"
                
                reading.save()

                log_interaction(
                    source="web",
                    direction="in",
                    event_type="reading_request",
                    interaction_id=f"reading:{reading.id}",
                    user_identifier=str(session_key),
                    content=reading.question,
                    reading=reading,
                    metadata={
                        "user_age": reading.user_age,
                        "user_gender": reading.user_gender,
                        "reading_id": reading.id,
                    },
                )
                
                # Track reading creation
                MonitoringUtils.track_reading_creation()
                
                # Check sufficient cards in database
                cards = CardService.get_all_cards()
                if len(cards) < 5:
                    raise InsufficientCardsException(f"Insufficient cards in database: {len(cards)} available, 5 required")
                
                # Select cards
                selected_cards = random.sample(cards, 5)
                
                # Create card positions
                positions = []
                for position, card in enumerate(selected_cards):
                    card_position = CardPosition.objects.create(
                        reading=reading,
                        card=card,
                        position=position,
                        is_reversed=random.choice([True, False])
                    )
                    positions.append(card_position)
                
                # Record the reading for rate limiting
                RateLimitService.record_reading(session_key)
                
                # Start async interpretation task
                ReadingService.set_reading_status(reading.id, 'processing')
                interpret_reading.delay(reading.id)
                
                logger.info(f"Created reading {reading.id} and started async interpretation")
                
                # Redirect to result page
                return redirect('tarot_readings:reading_result', reading_id=reading.id)
                
        except InsufficientCardsException as e:
            logger.error(f"Insufficient cards error: {str(e)}")
            form.add_error(None, 'В базе данных недостаточно карт для создания расклада. Обратитесь к администратору.')
            return self.form_invalid(form)
            
        except Exception as e:
            logger.error(f"Unexpected error in form processing: {str(e)}", exc_info=True)
            form.add_error(None, 'Произошла неожиданная ошибка при создании расклада. Пожалуйста, попробуйте снова.')
            return self.form_invalid(form)

class ReadingResultView(DetailView):
    model = Reading
    template_name = 'tarot_readings/reading_result.html'
    context_object_name = 'reading'
    pk_url_kwarg = 'reading_id'
    
    def get_object(self, queryset=None):
        """
        Get the reading object with improved error handling
        """
        try:
            obj = super().get_object(queryset)
            logger.info(f"Successfully retrieved reading {obj.id}")
            return obj
        except Http404:
            logger.warning(f"Reading with id {self.kwargs.get('reading_id')} not found")
            raise
        except Exception as e:
            logger.error(f"Error retrieving reading: {str(e)}", exc_info=True)
            raise Http404("Reading not accessible")
    
    def get_context_data(self, **kwargs):
        """
        Add additional context with error handling
        """
        try:
            context = super().get_context_data(**kwargs)
            reading = context['reading']
            
            # Get card positions with error handling
            positions = CardPosition.objects.filter(reading=reading).select_related('card').order_by('position')
            
            if not positions.exists():
                logger.warning(f"No card positions found for reading {reading.id}")
                context['error'] = "Карты для этого расклада не найдены."
            else:
                context['positions'] = positions
                logger.info(f"Retrieved {positions.count()} card positions for reading {reading.id}")
            
            return context
            
        except Exception as e:
            logger.error(f"Error building context for reading result: {str(e)}", exc_info=True)
            # Return minimal context to prevent complete page failure
            return {'reading': self.get_object(), 'error': 'Произошла ошибка при загрузке данных расклада.'}

def reading_status_api(request, reading_id):
    """
    API endpoint to check reading interpretation status
    """
    try:
        status = ReadingService.get_reading_status(reading_id)
        
        # Get reading to check if interpretation is complete
        try:
            reading = Reading.objects.get(id=reading_id)
            has_interpretation = bool(reading.interpretation and reading.interpretation.strip())
        except Reading.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Reading not found'}, status=404)
        
        response_data = {
            'status': status,
            'has_interpretation': has_interpretation,
            'reading_id': reading_id
        }
        
        if has_interpretation:
            response_data['status'] = 'completed'
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error checking reading status: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Internal error'}, status=500)


def health_check(request):
    """
    Health check endpoint for monitoring
    """
    try:
        health_status = MonitoringUtils.health_check()
        
        status_code = 200
        if health_status['status'] == 'unhealthy':
            status_code = 503  # Service Unavailable
        elif health_status['status'] == 'degraded':
            status_code = 200  # Still serving requests
            
        return JsonResponse(health_status, status=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'Health check failed',
            'timestamp': timezone.now().timestamp()
        }, status=500)


def metrics_api(request):
    """
    Metrics endpoint for monitoring dashboard
    """
    try:
        stats = MonitoringUtils.get_daily_stats()
        
        return JsonResponse({
            'metrics': stats,
            'timestamp': timezone.now().timestamp()
        })
        
    except Exception as e:
        logger.error(f"Metrics API failed: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': 'Metrics unavailable',
            'timestamp': timezone.now().timestamp()
        }, status=500)
