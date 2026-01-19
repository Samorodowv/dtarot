from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
import logging
import time
from .models import Reading, CardPosition, Card
from .gigachat_interpreter import TarotInterpreter
from .monitoring import MonitoringUtils
from .exceptions import (
    GigaChatException, GigaChatAuthException, GigaChatAPIException, 
    GigaChatTimeoutException
)

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def interpret_reading(self, reading_id):
    """
    Async task to generate interpretation for a tarot reading
    """
    start_time = time.time()
    
    try:
        # Get reading and positions
        reading = Reading.objects.get(id=reading_id)
        positions = CardPosition.objects.filter(reading=reading).select_related('card').order_by('position')
        
        if not positions.exists():
            logger.error(f"No card positions found for reading {reading_id}")
            reading.interpretation = "Ошибка: карты для расклада не найдены."
            reading.save()
            MonitoringUtils.track_error("missing_positions", f"No positions for reading {reading_id}")
            return False
        
        # Generate interpretation
        interpreter = TarotInterpreter()
        interpretation = interpreter.interpret_reading(reading, positions)
        
        # Save interpretation
        reading.interpretation = interpretation
        reading.save()
        
        # Cache the result for quick access
        cache.set(f'reading_{reading_id}_status', 'completed', 300)
        
        # Track performance metrics
        duration = time.time() - start_time
        MonitoringUtils.track_interpretation_time(reading_id, duration)
        
        logger.info(f"Successfully generated interpretation for reading {reading_id}")
        return True
        
    except Reading.DoesNotExist:
        logger.error(f"Reading {reading_id} not found")
        return False
        
    except GigaChatAuthException as e:
        logger.error(f"GigaChat auth error for reading {reading_id}: {str(e)}")
        try:
            reading = Reading.objects.get(id=reading_id)
            # Provide a meaningful fallback interpretation
            reading.interpretation = f"""🔮 **Ваш расклад Таро**

💫 **Текущая ситуация**: Ваши карты указывают на период важных изменений. Энергии находятся в движении, и это время для принятия решений.

🌟 **Совет**: Доверьтесь своей интуиции и будьте открыты к новым возможностям. Карты говорят о том, что у вас есть все необходимые ресурсы для достижения целей.

🎯 **Прогноз**: Впереди вас ждут позитивные перемены. Оставайтесь сосредоточенными на своих желаниях и действуйте с уверенностью.

✨ Помните: карты - это инструмент самопознания. Их истинная сила заключается в том, как вы применяете полученную мудрость в своей жизни.

---
*Временно недоступна AI-интерпретация. Скоро сервис будет восстановлен.*"""
            reading.save()
        except:
            pass
        return False
        
    except GigaChatTimeoutException as e:
        logger.warning(f"GigaChat timeout for reading {reading_id}: {str(e)}")
        # Retry the task
        if self.request.retries < self.max_retries:
            cache.set(f'reading_{reading_id}_status', f'retrying_{self.request.retries + 1}', 300)
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        else:
            try:
                reading = Reading.objects.get(id=reading_id)
                reading.interpretation = "Извините, AI-сервис временно недоступен. Попробуйте создать новый расклад."
                reading.save()
            except:
                pass
            return False
            
    except GigaChatAPIException as e:
        logger.error(f"GigaChat API error for reading {reading_id}: {str(e)}")
        try:
            reading = Reading.objects.get(id=reading_id)
            reading.interpretation = "Возникла техническая проблема с интерпретацией. Карты выбраны правильно."
            reading.save()
        except:
            pass
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error in interpret_reading task: {str(e)}", exc_info=True)
        # Retry for unexpected errors
        if self.request.retries < self.max_retries:
            cache.set(f'reading_{reading_id}_status', f'error_retrying_{self.request.retries + 1}', 300)
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        else:
            try:
                reading = Reading.objects.get(id=reading_id)
                reading.interpretation = "Произошла неожиданная ошибка. Попробуйте создать новый расклад."
                reading.save()
            except:
                pass
            return False

@shared_task
def cleanup_old_readings():
    """
    Periodic task to clean up old readings (older than 30 days)
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    old_readings = Reading.objects.filter(created_at__lt=cutoff_date)
    count = old_readings.count()
    
    if count > 0:
        # Delete associated card positions first
        CardPosition.objects.filter(reading__in=old_readings).delete()
        old_readings.delete()
        logger.info(f"Cleaned up {count} old readings")
    
    return count

@shared_task
def cache_card_data():
    """
    Task to cache frequently accessed card data
    """
    try:
        # Cache all cards
        cards = list(Card.objects.all().values('id', 'name', 'suit', 'meaning_upright', 'meaning_reversed'))
        cache.set('all_cards', cards, 3600)  # Cache for 1 hour
        
        # Cache cards by suit
        for suit_choice in Card.SUIT_CHOICES:
            suit_code = suit_choice[0]
            suit_cards = [card for card in cards if card['suit'] == suit_code]
            cache.set(f'cards_suit_{suit_code}', suit_cards, 3600)
        
        logger.info(f"Cached {len(cards)} cards")
        return len(cards)
        
    except Exception as e:
        logger.error(f"Error caching card data: {str(e)}", exc_info=True)
        return 0