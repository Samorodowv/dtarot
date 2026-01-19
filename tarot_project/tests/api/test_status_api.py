"""
API tests for reading status endpoints
"""

import pytest
import json
from django.urls import reverse
from unittest.mock import patch

from tarot_readings.models import Reading


@pytest.mark.django_db
class TestReadingStatusAPI:
    """Test reading status API functionality"""
    
    def test_api_returns_json(self, client, sample_reading):
        """Test that API returns JSON response"""
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': sample_reading.id})
        response = client.get(url)
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
        
        # Should be valid JSON
        data = json.loads(response.content)
        assert isinstance(data, dict)
        
    def test_api_response_structure(self, client, sample_reading):
        """Test API response structure"""
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': sample_reading.id})
        response = client.get(url)
        
        data = json.loads(response.content)
        
        # Required fields
        assert 'status' in data
        assert 'has_interpretation' in data
        assert 'reading_id' in data
        
        # Correct types
        assert isinstance(data['status'], str)
        assert isinstance(data['has_interpretation'], bool)
        assert isinstance(data['reading_id'], int)
        
    def test_api_completed_reading(self, client, sample_reading):
        """Test API response for completed reading"""
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': sample_reading.id})
        response = client.get(url)
        
        data = json.loads(response.content)
        
        assert data['status'] == 'completed'
        assert data['has_interpretation'] is True
        assert data['reading_id'] == sample_reading.id
        
    def test_api_pending_reading(self, client, sample_cards):
        """Test API response for pending reading"""
        # Create reading without interpretation
        reading = Reading.objects.create(
            user_age=25,
            user_gender='female',
            question='Test question',
            interpretation=''
        )
        
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': reading.id})
        response = client.get(url)
        
        data = json.loads(response.content)
        
        assert data['status'] == 'pending'
        assert data['has_interpretation'] is False
        assert data['reading_id'] == reading.id
        
    def test_api_nonexistent_reading(self, client):
        """Test API response for nonexistent reading"""
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': 99999})
        response = client.get(url)
        
        assert response.status_code == 404
        
        data = json.loads(response.content)
        assert data['status'] == 'error'
        assert 'message' in data
        assert 'not found' in data['message'].lower()
        
    @patch('tarot_readings.services.ReadingService.get_reading_status')
    def test_api_cached_status(self, mock_get_status, client, sample_reading):
        """Test API uses cached status when available"""
        mock_get_status.return_value = 'processing'
        
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': sample_reading.id})
        response = client.get(url)
        
        data = json.loads(response.content)
        
        # Should use cached status instead of DB status
        assert data['status'] == 'processing'
        mock_get_status.assert_called_once_with(sample_reading.id)
        
    @patch('tarot_readings.services.ReadingService.get_reading_status')
    def test_api_retrying_status(self, mock_get_status, client, sample_reading):
        """Test API response for retrying status"""
        mock_get_status.return_value = 'retrying_2'
        
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': sample_reading.id})
        response = client.get(url)
        
        data = json.loads(response.content)
        
        assert data['status'] == 'retrying_2'
        assert data['reading_id'] == sample_reading.id
        
    @patch('tarot_readings.services.ReadingService.get_reading_status')
    def test_api_error_status(self, mock_get_status, client, sample_reading):
        """Test API response for error status"""
        mock_get_status.return_value = 'error'
        
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': sample_reading.id})
        response = client.get(url)
        
        data = json.loads(response.content)
        
        assert data['status'] == 'error'
        assert data['reading_id'] == sample_reading.id
        
    def test_api_only_get_method(self, client, sample_reading):
        """Test that API only accepts GET requests"""
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': sample_reading.id})
        
        # POST should not be allowed
        response = client.post(url, {})
        assert response.status_code == 405  # Method Not Allowed
        
        # PUT should not be allowed
        response = client.put(url, {})
        assert response.status_code == 405
        
        # DELETE should not be allowed  
        response = client.delete(url)
        assert response.status_code == 405
        
    def test_api_handles_exceptions(self, client):
        """Test that API handles unexpected exceptions gracefully"""
        with patch('tarot_readings.views.ReadingService.get_reading_status') as mock_service:
            mock_service.side_effect = Exception("Unexpected error")
            
            url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': 1})
            response = client.get(url)
            
            assert response.status_code == 500
            
            data = json.loads(response.content)
            assert data['status'] == 'error'
            assert 'message' in data
            
    def test_api_reading_id_validation(self, client):
        """Test API validation of reading ID parameter"""
        # Invalid reading ID format should be handled by URL routing
        # But we can test with valid integers that don't exist
        
        for invalid_id in [0, -1, -999]:
            url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': invalid_id})
            response = client.get(url)
            
            assert response.status_code == 404
            
            data = json.loads(response.content)
            assert data['status'] == 'error'


@pytest.mark.api
class TestAPIRateLimit:
    """Test API rate limiting (if implemented)"""
    
    @pytest.mark.skip(reason="Rate limiting not implemented for API yet")
    def test_api_rate_limiting(self, client, sample_reading):
        """Test that API has rate limiting"""
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': sample_reading.id})
        
        # Make many requests quickly
        for _ in range(100):
            response = client.get(url)
            if response.status_code == 429:  # Too Many Requests
                break
        else:
            pytest.fail("Rate limiting not triggered after 100 requests")


@pytest.mark.api
class TestAPICORS:
    """Test API CORS headers (if implemented)"""
    
    @pytest.mark.skip(reason="CORS not configured yet")
    def test_api_cors_headers(self, client, sample_reading):
        """Test that API includes proper CORS headers"""
        url = reverse('tarot_readings:reading_status_api', kwargs={'reading_id': sample_reading.id})
        response = client.get(url)
        
        assert 'Access-Control-Allow-Origin' in response
        assert 'Access-Control-Allow-Methods' in response