from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class RateLimitService:
    """
    Redis-based rate limiting service for tarot readings
    """
    
    READING_COOLDOWN_HOURS = 1
    PROMO_CODE = 'tarot25'
    
    @classmethod
    def get_rate_limit_key(cls, session_key):
        """Generate cache key for rate limiting"""
        return f'rate_limit_{session_key}'
    
    @classmethod
    def get_promo_key(cls, session_key):
        """Generate cache key for promo code usage"""
        return f'promo_used_{session_key}'
    
    @classmethod
    def can_create_reading(cls, session_key):
        """
        Check if user can create a new reading
        
        Returns:
            tuple: (can_create: bool, time_left: timedelta or None)
        """
        try:
            # Check if promo code was used
            promo_used = cache.get(cls.get_promo_key(session_key), False)
            if promo_used:
                return True, None
            
            # Check last reading time
            rate_limit_key = cls.get_rate_limit_key(session_key)
            last_reading_time = cache.get(rate_limit_key)
            
            if not last_reading_time:
                return True, None
            
            # Calculate time difference
            if isinstance(last_reading_time, str):
                last_reading_time = timezone.datetime.fromisoformat(last_reading_time)
            
            next_available = last_reading_time + timedelta(hours=cls.READING_COOLDOWN_HOURS)
            now = timezone.now()
            
            if now >= next_available:
                return True, None
            else:
                time_left = next_available - now
                return False, time_left
                
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}", exc_info=True)
            # On error, allow the reading (fail open)
            return True, None
    
    @classmethod
    def record_reading(cls, session_key):
        """Record that a reading was created"""
        try:
            rate_limit_key = cls.get_rate_limit_key(session_key)
            cache.set(rate_limit_key, timezone.now(), 3600)  # 1 hour
            
            # Clear promo usage
            promo_key = cls.get_promo_key(session_key)
            cache.delete(promo_key)
            
        except Exception as e:
            logger.error(f"Error recording reading: {str(e)}", exc_info=True)
    
    @classmethod
    def apply_promo_code(cls, session_key, promo_code):
        """
        Apply promo code to bypass rate limiting
        
        Returns:
            bool: True if promo code is valid and applied
        """
        try:
            if promo_code.strip().lower() == cls.PROMO_CODE.lower():
                promo_key = cls.get_promo_key(session_key)
                cache.set(promo_key, True, 3600)  # Valid for 1 hour
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error applying promo code: {str(e)}", exc_info=True)
            return False
    
    @classmethod
    def is_promo_applied(cls, session_key):
        """Check if promo code is currently applied"""
        try:
            promo_key = cls.get_promo_key(session_key)
            return cache.get(promo_key, False)
        except Exception as e:
            logger.error(f"Error checking promo status: {str(e)}", exc_info=True)
            return False

class CardService:
    """
    Service for card-related operations with caching
    """
    
    @classmethod
    def get_all_cards(cls):
        """Get all cards with caching"""
        try:
            cards = cache.get('all_cards')
            if cards is None:
                from .models import Card
                cards = list(Card.objects.all())
                cache.set('all_cards', cards, 3600)  # Cache for 1 hour
            return cards
        except Exception as e:
            logger.error(f"Error getting cards: {str(e)}", exc_info=True)
            from .models import Card
            return list(Card.objects.all())
    
    @classmethod
    def get_cards_by_suit(cls, suit):
        """Get cards by suit with caching"""
        try:
            cache_key = f'cards_suit_{suit}'
            cards = cache.get(cache_key)
            if cards is None:
                from .models import Card
                cards = list(Card.objects.filter(suit=suit))
                cache.set(cache_key, cards, 3600)
            return cards
        except Exception as e:
            logger.error(f"Error getting cards by suit: {str(e)}", exc_info=True)
            from .models import Card
            return list(Card.objects.filter(suit=suit))

class ReadingService:
    """
    Service for reading-related operations
    """
    
    @classmethod
    def get_reading_status(cls, reading_id):
        """
        Get the status of an async reading interpretation
        
        Returns:
            str: 'pending', 'processing', 'completed', 'error', 'retrying_X'
        """
        try:
            status = cache.get(f'reading_{reading_id}_status')
            if status:
                return status
            
            # Check if reading exists and has interpretation
            from .models import Reading
            try:
                reading = Reading.objects.get(id=reading_id)
                if reading.interpretation:
                    return 'completed'
                else:
                    return 'pending'
            except Reading.DoesNotExist:
                return 'error'
                
        except Exception as e:
            logger.error(f"Error getting reading status: {str(e)}", exc_info=True)
            return 'error'
    
    @classmethod
    def set_reading_status(cls, reading_id, status):
        """Set reading status in cache"""
        try:
            cache.set(f'reading_{reading_id}_status', status, 300)  # 5 minutes
        except Exception as e:
            logger.error(f"Error setting reading status: {str(e)}", exc_info=True)