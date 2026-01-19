"""
Enhanced GigaChat authentication with OAuth token management
Based on GigaChat API documentation best practices
"""

import requests
import base64
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from django.conf import settings
from decouple import config
from .exceptions import GigaChatAuthException

logger = logging.getLogger(__name__)


class GigaChatAuth:
    """
    Enhanced GigaChat authentication class with automatic token refresh
    and proper OAuth handling based on official documentation
    """

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize GigaChat authentication

        Args:
            client_id: GigaChat client ID (optional, will use env var if not provided)
            client_secret: GigaChat client secret (optional, will use env var if not provided)
        """
        # Use provided credentials or fall back to environment variables
        self.client_id = client_id or config('GIGACHAT_CLIENT_ID', default='')
        self.client_secret = client_secret or config('GIGACHAT_CLIENT_SECRET', default='')

        # API endpoints from documentation
        self.token_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        self.scope = "GIGACHAT_API_PERS"

        # Token management
        self.access_token = None
        self.token_expires_at = None

        # Validate credentials
        if not self.client_id or not self.client_secret:
            raise GigaChatAuthException(
                "GigaChat credentials not configured. Please set GIGACHAT_CLIENT_ID and GIGACHAT_CLIENT_SECRET environment variables"
            )

    def get_token(self) -> str:
        """
        Get OAuth token with automatic refresh

        Returns:
            str: Valid access token

        Raises:
            GigaChatAuthException: If token acquisition fails
        """
        # Check if current token is still valid (with 1-minute buffer)
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                logger.debug("Using existing valid token")
                return self.access_token

        logger.info("Requesting new OAuth token from GigaChat")
        return self._request_new_token()

    def _request_new_token(self) -> str:
        """
        Request a new OAuth token from GigaChat API

        Returns:
            str: New access token

        Raises:
            GigaChatAuthException: If token request fails
        """
        try:
            # Create base64 encoded credentials
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            # Prepare request headers (following documentation format)
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'RqUID': f'{int(time.time())}',  # Request unique identifier
                'Authorization': f'Basic {encoded_credentials}'
            }

            # Request data
            data = {'scope': self.scope}

            # Make token request
            response = requests.post(
                self.token_url,
                headers=headers,
                data=data,
                verify=False,  # GigaChat uses self-signed certificates
                timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')

                if not self.access_token:
                    raise GigaChatAuthException("Token not found in response")

                # Calculate token expiration (with safety buffer)
                expires_in = token_data.get('expires_in', 1800)  # Default 30 minutes
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)

                logger.info(f"Successfully obtained new token, expires at {self.token_expires_at}")
                return self.access_token

            elif response.status_code == 401:
                raise GigaChatAuthException("Invalid GigaChat credentials - check your client ID and secret")
            elif response.status_code == 402:
                raise GigaChatAuthException("Payment required - please check your GigaChat account balance")
            else:
                raise GigaChatAuthException(f"Token request failed: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            logger.error(f"Network error during token request: {str(e)}")
            raise GigaChatAuthException(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token request: {str(e)}", exc_info=True)
            raise GigaChatAuthException(f"Authentication failed: {str(e)}")

    def get_base64_credentials(self) -> str:
        """
        Get base64 encoded credentials for direct authentication
        This method maintains compatibility with existing simple auth approach

        Returns:
            str: Base64 encoded credentials
        """
        credentials = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(credentials.encode()).decode()

    def is_token_valid(self) -> bool:
        """
        Check if current token is valid

        Returns:
            bool: True if token exists and hasn't expired
        """
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now() < self.token_expires_at

    def clear_token(self):
        """Clear stored token and force re-authentication on next request"""
        self.access_token = None
        self.token_expires_at = None
        logger.info("Cleared stored token")


def test_gigachat_credentials(client_id: str, client_secret: str) -> bool:
    """
    Test GigaChat credentials by attempting to get a token
    Utility function for credential validation

    Args:
        client_id: GigaChat client ID
        client_secret: GigaChat client secret

    Returns:
        bool: True if credentials are valid
    """
    try:
        auth = GigaChatAuth(client_id, client_secret)
        token = auth.get_token()

        # Test API access with the token
        api_headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        models_response = requests.get(
            "https://gigachat.devices.sberbank.ru/api/v1/models",
            headers=api_headers,
            verify=False,
            timeout=10
        )

        if models_response.status_code == 200:
            models = models_response.json()
            logger.info(f"✅ Credentials valid. Available models: {len(models.get('data', []))}")
            return True
        else:
            logger.error(f"❌ API test failed: {models_response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ Credential test failed: {str(e)}")
        return False