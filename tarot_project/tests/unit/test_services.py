"""
Unit tests for Tarot services
"""

import pytest
from unittest.mock import patch, Mock
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from freezegun import freeze_time

from tarot_readings.services import RateLimitService, CardService, ReadingService
from tarot_readings.models import Card


@pytest.mark.django_db
class TestRateLimitService:
    """Test rate limiting service"""
    
    def test_can_create_reading_no_history(self):
        """Test that user can create reading with no history"""
        session_key = "test_session_123"
        
        can_create, time_left = RateLimitService.can_create_reading(session_key)
        
        assert can_create is True
        assert time_left is None
        
    def test_can_create_reading_with_promo(self):
        """Test that user can create reading with active promo code"""
        session_key = "test_session_123"
        
        # Apply promo code
        RateLimitService.apply_promo_code(session_key, "tarot25")
        
        can_create, time_left = RateLimitService.can_create_reading(session_key)
        
        assert can_create is True
        assert time_left is None
        
    @freeze_time("2024-01-15 12:00:00")
    def test_can_create_reading_rate_limited(self):
        """Test rate limiting after recent reading"""
        session_key = "test_session_123"
        
        # Record a reading
        RateLimitService.record_reading(session_key)
        
        # Check immediately after
        can_create, time_left = RateLimitService.can_create_reading(session_key)
        
        assert can_create is False
        assert time_left is not None
        assert time_left.total_seconds() > 3500  # Almost 1 hour
        
    @freeze_time("2024-01-15 12:00:00")
    def test_can_create_reading_after_cooldown(self):
        """Test that user can create reading after cooldown period"""
        session_key = "test_session_123"
        
        # Record a reading
        RateLimitService.record_reading(session_key)
        
        # Move time forward by more than 1 hour
        with freeze_time("2024-01-15 13:30:00"):
            can_create, time_left = RateLimitService.can_create_reading(session_key)
            
            assert can_create is True
            assert time_left is None
            
    def test_apply_valid_promo_code(self):
        """Test applying valid promo code"""
        session_key = "test_session_123"
        
        result = RateLimitService.apply_promo_code(session_key, "tarot25")
        
        assert result is True
        assert RateLimitService.is_promo_applied(session_key) is True
        
    def test_apply_invalid_promo_code(self):
        """Test applying invalid promo code"""
        session_key = "test_session_123"
        
        result = RateLimitService.apply_promo_code(session_key, "invalid")
        
        assert result is False
        assert RateLimitService.is_promo_applied(session_key) is False
        
    def test_case_insensitive_promo_code(self):
        """Test that promo code is case insensitive"""
        session_key = "test_session_123"
        
        result = RateLimitService.apply_promo_code(session_key, "TAROT25")
        
        assert result is True
        assert RateLimitService.is_promo_applied(session_key) is True
        
    def test_record_reading_clears_promo(self):
        """Test that recording a reading clears the promo code"""
        session_key = "test_session_123"
        
        # Apply promo code
        RateLimitService.apply_promo_code(session_key, "tarot25")
        assert RateLimitService.is_promo_applied(session_key) is True
        
        # Record reading
        RateLimitService.record_reading(session_key)
        
        # Promo should be cleared
        assert RateLimitService.is_promo_applied(session_key) is False


@pytest.mark.django_db
class TestCardService:
    """Test card service"""
    
    def test_get_all_cards_from_db(self, sample_cards):
        """Test getting all cards from database"""
        # Clear cache first
        cache.clear()
        
        cards = CardService.get_all_cards()
        
        assert len(cards) == len(sample_cards)
        assert all(isinstance(card, Card) for card in cards)
        
    def test_get_all_cards_from_cache(self, sample_cards):
        """Test getting cards from cache"""
        # First call populates cache
        cards1 = CardService.get_all_cards()
        
        # Second call should use cache
        with patch.object(Card.objects, 'all') as mock_queryset:
            cards2 = CardService.get_all_cards()
            
            # Database should not be queried
            mock_queryset.assert_not_called()
            assert len(cards2) == len(sample_cards)
            
    def test_get_cards_by_suit(self, sample_cards):
        """Test getting cards by suit"""
        major_cards = CardService.get_cards_by_suit("major")
        cups_cards = CardService.get_cards_by_suit("cups")
        
        assert len(major_cards) == 2  # The Fool and The Magician
        assert len(cups_cards) == 2   # Ace and Two of Cups
        
        assert all(card.suit == "major" for card in major_cards)
        assert all(card.suit == "cups" for card in cups_cards)
        
    def test_get_cards_by_suit_cached(self, sample_cards):
        """Test that cards by suit are cached"""
        # First call
        cards1 = CardService.get_cards_by_suit("major")
        
        # Second call should use cache
        with patch.object(Card.objects, 'filter') as mock_filter:
            cards2 = CardService.get_cards_by_suit("major")
            
            # Database should not be queried
            mock_filter.assert_not_called()
            assert len(cards2) == len(cards1)


@pytest.mark.django_db
class TestReadingService:
    """Test reading service"""
    
    def test_get_reading_status_no_cache(self, sample_reading):
        """Test getting reading status with no cache entry"""
        status = ReadingService.get_reading_status(sample_reading.id)
        
        assert status == 'completed'  # Has interpretation
        
    def test_get_reading_status_from_cache(self, sample_reading):
        """Test getting reading status from cache"""
        reading_id = sample_reading.id
        
        # Set cache status
        ReadingService.set_reading_status(reading_id, 'processing')
        
        status = ReadingService.get_reading_status(reading_id)
        
        assert status == 'processing'
        
    def test_get_reading_status_nonexistent(self):
        """Test getting status for nonexistent reading"""
        status = ReadingService.get_reading_status(99999)
        
        assert status == 'error'
        
    def test_set_reading_status(self, sample_reading):
        """Test setting reading status in cache"""
        reading_id = sample_reading.id
        
        ReadingService.set_reading_status(reading_id, 'retrying_1')
        
        # Check that it was set
        from django.core.cache import cache
        cached_status = cache.get(f'reading_{reading_id}_status')
        assert cached_status == 'retrying_1'
        
    def test_reading_status_without_interpretation(self, sample_cards):
        """Test status for reading without interpretation"""
        from tarot_readings.models import Reading
        
        reading = Reading.objects.create(
            user_age=25,
            user_gender="female",
            question="Test question",
            interpretation=""  # No interpretation
        )
        
        status = ReadingService.get_reading_status(reading.id)
        
        assert status == 'pending'