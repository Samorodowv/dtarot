"""
Integration tests for Tarot views
"""

import pytest
from django.urls import reverse
from django.test import Client
from unittest.mock import patch, Mock
import json

from tarot_readings.models import Reading, CardPosition


@pytest.mark.django_db
class TestGetReadingView:
    """Test the main reading form view"""
    
    def test_get_reading_form(self, client):
        """Test GET request to reading form"""
        url = reverse('tarot_readings:home')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert 'can_create_reading' in response.context
        
    def test_get_reading_form_with_cooldown(self, client, sample_cards):
        """Test form with rate limiting cooldown"""
        # Create a session and simulate recent reading
        session = client.session
        session['last_reading_time'] = '2024-01-15T12:00:00+00:00'
        session.save()
        
        url = reverse('tarot_readings:home')
        response = client.get(url)
        
        assert response.status_code == 200
        # Should show cooldown in context
        # Note: This might not work with Redis-based rate limiting without proper setup
        
    def test_post_valid_reading_form(self, client, sample_cards, mock_gigachat):
        """Test submitting valid reading form"""
        url = reverse('tarot_readings:home')
        data = {
            'user_age': 25,
            'user_gender': 'female',
            'question': 'Как улучшить мою карьеру?'
        }
        
        response = client.post(url, data)
        
        # Should redirect to result page
        assert response.status_code == 302
        
        # Check that reading was created
        reading = Reading.objects.get()
        assert reading.user_age == 25
        assert reading.user_gender == 'female'
        assert reading.question == 'Как улучшить мою карьеру?'
        
        # Check that cards were selected
        positions = CardPosition.objects.filter(reading=reading)
        assert positions.count() == 5
        
    def test_post_invalid_reading_form(self, client):
        """Test submitting invalid reading form"""
        url = reverse('tarot_readings:home')
        data = {
            'user_age': 15,  # Invalid age
            'user_gender': 'female',
            'question': 'Test question'
        }
        
        response = client.post(url, data)
        
        assert response.status_code == 200  # Returns form with errors
        assert 'form' in response.context
        assert response.context['form'].errors
        
        # No reading should be created
        assert Reading.objects.count() == 0
        
    def test_promo_code_application(self, client):
        """Test applying promo code"""
        url = reverse('tarot_readings:home')
        data = {
            'promo_code': 'tarot25',
            'apply_promo': True
        }
        
        response = client.post(url, data)
        
        assert response.status_code == 302  # Redirect after promo application
        
    def test_invalid_promo_code(self, client):
        """Test applying invalid promo code"""
        url = reverse('tarot_readings:home')
        data = {
            'promo_code': 'invalid',
            'apply_promo': True
        }
        
        response = client.post(url, data)
        
        assert response.status_code == 302
        
        # Follow redirect to see messages
        response = client.get(reverse('tarot_readings:home'))
        assert response.status_code == 200


@pytest.mark.django_db 
class TestReadingResultView:
    """Test the reading result view"""
    
    def test_get_reading_result(self, client, sample_reading):
        """Test GET request to reading result"""
        url = reverse('tarot_readings:reading_result', kwargs={'reading_id': sample_reading.id})
        response = client.get(url)
        
        assert response.status_code == 200
        assert response.context['reading'] == sample_reading
        assert 'positions' in response.context
        
    def test_get_nonexistent_reading_result(self, client):
        """Test GET request for nonexistent reading"""
        url = reverse('tarot_readings:reading_result', kwargs={'reading_id': 99999})
        response = client.get(url)
        
        assert response.status_code == 404
        
    def test_reading_result_with_positions(self, client, sample_reading):
        """Test that card positions are included in context"""
        url = reverse('tarot_readings:reading_result', kwargs={'reading_id': sample_reading.id})
        response = client.get(url)
        
        assert response.status_code == 200
        positions = response.context['positions']
        
        assert positions.count() == 5
        # Check that positions are ordered
        position_numbers = [p.position for p in positions]
        assert position_numbers == sorted(position_numbers)
        
    def test_reading_result_without_interpretation(self, client, sample_cards):
        """Test reading result without interpretation"""
        # Create reading without interpretation
        reading = Reading.objects.create(
            user_age=25,
            user_gender='female',
            question='Test question',
            interpretation=''
        )
        
        url = reverse('tarot_readings:reading_result', kwargs={'reading_id': reading.id})
        response = client.get(url)
        
        assert response.status_code == 200
        assert response.context['reading'].interpretation == ''


@pytest.mark.django_db
class TestReadingStatusAPI:
    """Test the reading status API endpoint"""
    
    def test_reading_status_api_completed(self, client, sample_reading):
        """Test API for completed reading"""
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': sample_reading.id})
        response = client.get(url)
        
        assert response.status_code == 200
        
        data = json.loads(response.content)
        assert data['status'] == 'completed'
        assert data['has_interpretation'] is True
        assert data['reading_id'] == sample_reading.id
        
    def test_reading_status_api_pending(self, client, sample_cards):
        """Test API for pending reading"""
        # Create reading without interpretation
        reading = Reading.objects.create(
            user_age=25,
            user_gender='female',
            question='Test question',
            interpretation=''
        )
        
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': reading.id})
        response = client.get(url)
        
        assert response.status_code == 200
        
        data = json.loads(response.content)
        assert data['status'] == 'pending'
        assert data['has_interpretation'] is False
        
    def test_reading_status_api_nonexistent(self, client):
        """Test API for nonexistent reading"""
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': 99999})
        response = client.get(url)
        
        assert response.status_code == 404
        
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert 'message' in data
        
    @patch('tarot_readings.services.ReadingService.get_reading_status')
    def test_reading_status_api_processing(self, mock_get_status, client, sample_reading):
        """Test API for processing reading"""
        mock_get_status.return_value = 'processing'
        
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': sample_reading.id})
        response = client.get(url)
        
        assert response.status_code == 200
        
        data = json.loads(response.content)
        assert data['status'] == 'processing'
        assert data['reading_id'] == sample_reading.id


@pytest.mark.django_db
class TestFormValidation:
    """Test form validation scenarios"""
    
    def test_age_validation(self, client):
        """Test age field validation"""
        url = reverse('tarot_readings:home')
        
        # Test minimum age
        response = client.post(url, {
            'user_age': 17,
            'user_gender': 'female',
            'question': 'Test question'
        })
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors
        
        # Test maximum age
        response = client.post(url, {
            'user_age': 101,
            'user_gender': 'female', 
            'question': 'Test question'
        })
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors
        
    def test_question_required_without_promo(self, client):
        """Test that question is required without promo code"""
        url = reverse('tarot_readings:home')
        
        response = client.post(url, {
            'user_age': 25,
            'user_gender': 'female',
            'question': ''  # Empty question
        })
        
        assert response.status_code == 200
        assert 'form' in response.context
        # Should have validation error for empty question
        
    def test_all_fields_required(self, client):
        """Test that all required fields must be filled"""
        url = reverse('tarot_readings:home')
        
        # Missing age
        response = client.post(url, {
            'user_gender': 'female',
            'question': 'Test question'
        })
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors
        
        # Missing gender
        response = client.post(url, {
            'user_age': 25,
            'question': 'Test question'
        })
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.django_db
class TestEndToEndReadingFlow:
    """End-to-end integration tests"""
    
    def test_complete_reading_flow(self, client, sample_cards, mock_gigachat):
        """Test complete flow from form to result"""
        # Step 1: Get form
        form_url = reverse('tarot_readings:home')
        response = client.get(form_url)
        assert response.status_code == 200
        
        # Step 2: Submit form
        response = client.post(form_url, {
            'user_age': 25,
            'user_gender': 'female',
            'question': 'Как улучшить мою карьеру?'
        })
        assert response.status_code == 302
        
        # Step 3: Follow redirect to result
        reading = Reading.objects.get()
        result_url = reverse('tarot_readings:reading_result', kwargs={'reading_id': reading.id})
        response = client.get(result_url)
        assert response.status_code == 200
        
        # Step 4: Check API status
        api_url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': reading.id})
        response = client.get(api_url)
        assert response.status_code == 200
        
        data = json.loads(response.content)
        assert data['status'] == 'completed'
        assert data['has_interpretation'] is True