"""
Unit tests for Celery tasks
"""

import pytest
from unittest.mock import patch, Mock
from freezegun import freeze_time

from tarot_readings.tasks import interpret_reading, cleanup_old_readings, cache_card_data
from tarot_readings.models import Reading, Card, CardPosition
from tarot_readings.exceptions import GigaChatAuthException, GigaChatTimeoutException


@pytest.mark.django_db
@pytest.mark.celery
class TestInterpretReadingTask:
    """Test the interpret_reading Celery task"""
    
    def test_interpret_reading_success(self, sample_reading, mock_gigachat):
        """Test successful interpretation"""
        # Clear existing interpretation
        sample_reading.interpretation = ""
        sample_reading.save()
        
        result = interpret_reading(sample_reading.id)
        
        assert result is True
        
        # Reload reading from database
        sample_reading.refresh_from_db()
        assert sample_reading.interpretation == "Тестовая интерпретация расклада Таро."
        
    def test_interpret_reading_nonexistent(self):
        """Test task with nonexistent reading"""
        result = interpret_reading(99999)
        
        assert result is False
        
    def test_interpret_reading_no_positions(self, sample_cards):
        """Test task with reading that has no card positions"""
        reading = Reading.objects.create(
            user_age=25,
            user_gender="female",
            question="Test question",
            interpretation=""
        )
        
        result = interpret_reading(reading.id)
        
        assert result is False
        
        # Should have error message in interpretation
        reading.refresh_from_db()
        assert "карты для расклада не найдены" in reading.interpretation
        
    @patch('tarot_readings.tasks.TarotInterpreter')
    def test_interpret_reading_auth_error(self, mock_interpreter, sample_reading):
        """Test task with GigaChat authentication error"""
        sample_reading.interpretation = ""
        sample_reading.save()
        
        mock_interpreter.return_value.interpret_reading.side_effect = GigaChatAuthException("Auth failed")
        
        result = interpret_reading(sample_reading.id)
        
        assert result is False
        
        # Should have error message in interpretation
        sample_reading.refresh_from_db()
        assert "проблема с аутентификацией" in sample_reading.interpretation
        
    @patch('tarot_readings.tasks.TarotInterpreter')
    def test_interpret_reading_timeout_error(self, mock_interpreter, sample_reading):
        """Test task with GigaChat timeout error"""
        sample_reading.interpretation = ""
        sample_reading.save()
        
        mock_interpreter.return_value.interpret_reading.side_effect = GigaChatTimeoutException("Timeout")
        
        # Mock the task's retry mechanism
        with patch.object(interpret_reading, 'retry') as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")
            
            result = interpret_reading(sample_reading.id)
            
            assert result is False
            
            # Should have timeout message in interpretation
            sample_reading.refresh_from_db()
            assert "временно недоступен" in sample_reading.interpretation
            
    @patch('tarot_readings.tasks.TarotInterpreter')
    def test_interpret_reading_generic_error(self, mock_interpreter, sample_reading):
        """Test task with generic error"""
        sample_reading.interpretation = ""
        sample_reading.save()
        
        mock_interpreter.return_value.interpret_reading.side_effect = Exception("Generic error")
        
        # Mock the task's retry mechanism
        with patch.object(interpret_reading, 'retry') as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")
            
            result = interpret_reading(sample_reading.id)
            
            assert result is False
            
            # Should have error message in interpretation
            sample_reading.refresh_from_db()
            assert "неожиданная ошибка" in sample_reading.interpretation


@pytest.mark.django_db
@pytest.mark.celery
class TestCleanupOldReadingsTask:
    """Test the cleanup_old_readings Celery task"""
    
    @freeze_time("2024-01-15 12:00:00")
    def test_cleanup_old_readings(self, sample_cards):
        """Test cleanup of old readings"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Create old reading (35 days ago)
        old_time = timezone.now() - timedelta(days=35)
        with freeze_time(old_time):
            old_reading = Reading.objects.create(
                user_age=25,
                user_gender="female",
                question="Old question",
                interpretation="Old interpretation"
            )
            
        # Create recent reading (5 days ago)
        recent_time = timezone.now() - timedelta(days=5)
        with freeze_time(recent_time):
            recent_reading = Reading.objects.create(
                user_age=30,
                user_gender="male", 
                question="Recent question",
                interpretation="Recent interpretation"
            )
            
        # Create positions for old reading
        CardPosition.objects.create(
            reading=old_reading,
            card=sample_cards[0],
            position=0,
            is_reversed=False
        )
        
        # Run cleanup task
        count = cleanup_old_readings()
        
        assert count == 1  # One reading was cleaned up
        
        # Old reading should be gone
        assert not Reading.objects.filter(id=old_reading.id).exists()
        
        # Recent reading should remain
        assert Reading.objects.filter(id=recent_reading.id).exists()
        
        # Card positions should also be cleaned up
        assert not CardPosition.objects.filter(reading_id=old_reading.id).exists()
        
    def test_cleanup_no_old_readings(self):
        """Test cleanup when there are no old readings"""
        # Create only recent reading
        Reading.objects.create(
            user_age=25,
            user_gender="female",
            question="Recent question",
            interpretation="Recent interpretation"
        )
        
        count = cleanup_old_readings()
        
        assert count == 0
        assert Reading.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.celery
class TestCacheCardDataTask:
    """Test the cache_card_data Celery task"""
    
    def test_cache_card_data_success(self, sample_cards):
        """Test successful card data caching"""
        from django.core.cache import cache
        
        # Clear cache first
        cache.clear()
        
        count = cache_card_data()
        
        assert count == len(sample_cards)
        
        # Check that cards were cached
        cached_cards = cache.get('all_cards')
        assert cached_cards is not None
        assert len(cached_cards) == len(sample_cards)
        
        # Check that cards by suit were cached
        for suit_choice in Card.SUIT_CHOICES:
            suit_code = suit_choice[0]
            cached_suit_cards = cache.get(f'cards_suit_{suit_code}')
            assert cached_suit_cards is not None
            
    def test_cache_card_data_no_cards(self):
        """Test caching when there are no cards"""
        from django.core.cache import cache
        
        # Clear cache first
        cache.clear()
        
        count = cache_card_data()
        
        assert count == 0
        
        # Should still cache empty list
        cached_cards = cache.get('all_cards')
        assert cached_cards == []
        
    @patch('tarot_readings.tasks.cache.set')
    def test_cache_card_data_error(self, mock_cache_set, sample_cards):
        """Test caching with cache error"""
        mock_cache_set.side_effect = Exception("Cache error")
        
        count = cache_card_data()
        
        assert count == 0  # Should return 0 on error


@pytest.mark.celery
class TestTaskRetryMechanisms:
    """Test task retry mechanisms"""
    
    @patch('tarot_readings.tasks.TarotInterpreter')
    def test_interpret_reading_retry_on_timeout(self, mock_interpreter, sample_reading):
        """Test that task retries on timeout"""
        sample_reading.interpretation = ""
        sample_reading.save()
        
        mock_interpreter.return_value.interpret_reading.side_effect = GigaChatTimeoutException("Timeout")
        
        # Mock the task to check retry behavior
        with patch.object(interpret_reading, 'retry') as mock_retry:
            # First call should trigger retry
            interpret_reading(sample_reading.id)
            
            mock_retry.assert_called_once()
            
    @patch('tarot_readings.tasks.TarotInterpreter')
    def test_interpret_reading_max_retries(self, mock_interpreter, sample_reading):
        """Test task behavior when max retries exceeded"""
        sample_reading.interpretation = ""
        sample_reading.save()
        
        mock_interpreter.return_value.interpret_reading.side_effect = Exception("Persistent error")
        
        # Simulate max retries exceeded
        with patch.object(interpret_reading, 'retry') as mock_retry:
            mock_retry.side_effect = Exception("Max retries exceeded")
            
            result = interpret_reading(sample_reading.id)
            
            assert result is False
            
            # Should save error message
            sample_reading.refresh_from_db()
            assert "неожиданная ошибка" in sample_reading.interpretation


@pytest.mark.celery
@pytest.mark.integration
class TestTaskIntegration:
    """Integration tests for tasks"""
    
    @pytest.mark.django_db
    def test_task_logging(self, sample_reading, caplog, mock_gigachat):
        """Test that tasks log appropriately"""
        sample_reading.interpretation = ""
        sample_reading.save()
        
        with caplog.at_level('INFO'):
            interpret_reading(sample_reading.id)
            
        # Should have logged success
        assert any("Successfully generated interpretation" in record.message for record in caplog.records)
        
    @pytest.mark.django_db
    def test_task_cache_interaction(self, sample_reading, mock_gigachat):
        """Test task interaction with cache"""
        from django.core.cache import cache
        from tarot_readings.services import ReadingService
        
        sample_reading.interpretation = ""
        sample_reading.save()
        
        # Set initial status
        ReadingService.set_reading_status(sample_reading.id, 'processing')
        
        # Run task
        interpret_reading(sample_reading.id)
        
        # Status should be updated
        status = cache.get(f'reading_{sample_reading.id}_status')
        assert status == 'completed'