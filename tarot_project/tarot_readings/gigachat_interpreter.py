"""
Enhanced GigaChat Tarot Interpreter with improved authentication, model selection,
and error handling based on GigaChat API documentation
"""

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from gigachat.exceptions import ResponseError
import logging
from django.conf import settings
from decouple import config
import time
from typing import Dict, Optional, List

from .exceptions import (
    GigaChatException, GigaChatAuthException, GigaChatAPIException,
    GigaChatTimeoutException, GigaChatPaymentException, GigaChatQuotaException,
    GigaChatModelUnavailableException, GigaChatValidationException
)
from .gigachat_auth import GigaChatAuth
from .model_selector import model_selector

logger = logging.getLogger(__name__)


class TarotInterpreter:
    """Enhanced tarot interpreter with improved GigaChat integration"""

    def __init__(self, use_oauth: bool = None, model_name: str = None):
        """
        Initialize enhanced tarot interpreter

        Args:
            use_oauth: Whether to use OAuth authentication (default from settings)
            model_name: Specific model to use (default from settings)
        """
        self.use_oauth = use_oauth if use_oauth is not None else getattr(settings, 'GIGACHAT_USE_OAUTH', True)
        self.default_model = model_name or getattr(settings, 'GIGACHAT_DEFAULT_MODEL', 'GigaChat-Max')
        self.enable_auto_selection = getattr(settings, 'GIGACHAT_ENABLE_AUTO_MODEL_SELECTION', True)
        self.timeout = getattr(settings, 'GIGACHAT_TIMEOUT', 30)
        self.max_retries = getattr(settings, 'GIGACHAT_MAX_RETRIES', 3)

        # Initialize authentication
        self.auth = None
        self.giga = None

        try:
            self._initialize_client()
            logger.info(f"Enhanced GigaChat initialized successfully (OAuth: {self.use_oauth}, Model: {self.default_model})")
        except Exception as e:
            logger.error(f"Error initializing GigaChat: {str(e)}", exc_info=True)
            raise GigaChatAuthException(f"Failed to initialize GigaChat: {str(e)}")

    def _initialize_client(self):
        """Initialize GigaChat client with enhanced authentication"""
        if self.use_oauth:
            # Use OAuth authentication (recommended)
            self.auth = GigaChatAuth()
            credentials = self.auth.get_token()
            logger.info("Using OAuth authentication")
        else:
            # Fallback to static credentials
            credentials = config('GIGACHAT_API_CREDENTIALS')
            if not credentials:
                raise GigaChatAuthException("GigaChat API credentials not found in environment variables")
            logger.info("Using static credentials authentication")

        self.giga = GigaChat(
            credentials=credentials,
            verify_ssl_certs=False,
            timeout=self.timeout
        )

    def interpret_reading(self, reading, positions, max_retries: int = None, model_override: str = None) -> str:
        """
        Interpret a tarot reading using enhanced GigaChat API with smart model selection

        Args:
            reading: Reading model instance
            positions: List of CardPosition instances
            max_retries: Maximum number of retry attempts (default from settings)
            model_override: Specific model to use (overrides auto-selection)

        Returns:
            str: Interpretation text

        Raises:
            GigaChatException: On API errors
        """
        if not positions:
            raise GigaChatValidationException("No card positions provided for interpretation")

        max_retries = max_retries or self.max_retries

        # System prompt is consistent across model selection
        selected_model = self._select_model_for_reading(reading.question, model_override)
        system_prompt = self._get_system_prompt_for_model(selected_model)

        logger.info(f"Using model: {selected_model} for reading interpretation")

        # Формируем описание расклада
        reading_description = f"Вопрос клиента: {reading.question}\n\nРасклад:\n"

        position_names = {
            0: "В позиции текущей ситуации",
            1: "В позиции препятствия",
            2: "В позиции прошлого",
            3: "В позиции будущего",
            4: "В позиции возможного исхода"
        }

        for pos in positions:
            position_text = position_names.get(pos.position, f"В позиции {pos.position + 1}")
            orientation = "перевёрнутом" if pos.is_reversed else "прямом"
            meaning = pos.card.meaning_reversed if pos.is_reversed else pos.card.meaning_upright
            reading_description += f"{position_text} выпала карта {pos.card.name} в {orientation} положении.\n"
            reading_description += f"Значение: {meaning}\n\n"

        # Enhanced retry logic with improved error handling
        for attempt in range(max_retries):
            try:
                # Refresh token if using OAuth and needed
                if self.use_oauth and self.auth and not self.auth.is_token_valid():
                    logger.info("Refreshing OAuth token")
                    new_token = self.auth.get_token()
                    self.giga = GigaChat(
                        credentials=new_token,
                        verify_ssl_certs=False,
                        timeout=self.timeout
                    )

                logger.info(f"Creating chat payload (attempt {attempt + 1}/{max_retries})")

                # Enhanced payload with configurable parameters
                payload = Chat(
                    messages=[
                        Messages(
                            role=MessagesRole.SYSTEM,
                            content=system_prompt
                        ),
                        Messages(
                            role=MessagesRole.USER,
                            content=reading_description
                        )
                    ],
                    temperature=getattr(settings, 'GIGACHAT_TEMPERATURE', 0.7),
                    max_tokens=getattr(settings, 'GIGACHAT_MAX_TOKENS', 1000),
                    model=selected_model
                )

                logger.info(f"Sending request to GigaChat with model: {selected_model}")
                response = self.giga.chat(payload)

                if not response or not response.choices:
                    raise GigaChatAPIException("Empty response from GigaChat API")

                interpretation = response.choices[0].message.content

                if not interpretation or len(interpretation.strip()) < 10:
                    raise GigaChatAPIException("Received empty or too short interpretation")

                logger.info(f"Generated interpretation of length: {len(interpretation)} using {selected_model}")
                return interpretation

            except ResponseError as e:
                # Enhanced error handling based on documentation
                status_code = getattr(e, 'status_code', None) or (e.args[1] if len(e.args) > 1 else None)

                if status_code == 401:
                    logger.error(f"Authentication error on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        raise GigaChatAuthException("Invalid credentials - please check your API keys", status_code)
                elif status_code == 402:
                    logger.error(f"Payment required on attempt {attempt + 1}")
                    raise GigaChatPaymentException("Payment required - please check your GigaChat balance", status_code)
                elif status_code == 429:
                    logger.warning(f"Rate limit exceeded on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        raise GigaChatQuotaException("API quota exceeded - please try again later", status_code)
                else:
                    logger.error(f"API error {status_code} on attempt {attempt + 1}: {str(e)}")
                    if attempt == max_retries - 1:
                        raise GigaChatAPIException(f"API error: {status_code} - {str(e)}", status_code)

                # Exponential backoff for retryable errors
                time.sleep(2 ** attempt)

            except TimeoutError as e:
                logger.warning(f"Timeout on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise GigaChatTimeoutException("GigaChat API request timed out after multiple attempts")
                time.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Unexpected error in interpret_reading attempt {attempt + 1}: {str(e)}", exc_info=True)
                if attempt == max_retries - 1:
                    raise GigaChatAPIException(f"Failed to get interpretation from GigaChat: {str(e)}")
                time.sleep(2 ** attempt)

    def _select_model_for_reading(self, question: str, model_override: str = None) -> str:
        """Select appropriate model for tarot reading"""
        if model_override:
            logger.info(f"Using model override: {model_override}")
            return model_override

        if not self.enable_auto_selection:
            logger.info(f"Auto-selection disabled, using default: {self.default_model}")
            return self.default_model

        # Use model selector for intelligent selection
        selected = model_selector.select_model(question, {"reading_type": "tarot"})
        logger.debug(f"Auto-selected model: {selected} for question: {question[:50]}...")
        return selected

    def _get_system_prompt_for_model(self, model_name: str) -> str:
        """Get a single system prompt independent of model selection"""
        return (
            "Ты - опытный таролог с глубокими познаниями в эзотерике и психологии. "
            "Твоя задача - интерпретировать расклад Таро, учитывая позиции карт, их "
            "прямое или перевернутое положение, и вопрос клиента. "
            "Дай подробную и содержательную интерпретацию с практическими советами."
        )

    def get_available_models(self) -> List[str]:
        """Get list of available GigaChat models"""
        return getattr(settings, 'GIGACHAT_AVAILABLE_MODELS', ['GigaChat', 'GigaChat-Max', 'GigaChat-Pro'])

    def test_connection(self) -> Dict[str, any]:
        """Test GigaChat connection and return status"""
        try:
            # Simple test query
            payload = Chat(
                messages=[
                    Messages(role=MessagesRole.USER, content="Привет!")
                ],
                temperature=0.1,
                max_tokens=10,
                model=self.default_model
            )

            response = self.giga.chat(payload)

            return {
                "status": "success",
                "model": self.default_model,
                "response_length": len(response.choices[0].message.content) if response.choices else 0,
                "oauth_enabled": self.use_oauth,
                "token_valid": self.auth.is_token_valid() if self.auth else None
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "model": self.default_model,
                "oauth_enabled": self.use_oauth
            }

    def get_model_info(self) -> Dict[str, any]:
        """Get information about current configuration"""
        return {
            "default_model": self.default_model,
            "auto_selection_enabled": self.enable_auto_selection,
            "oauth_enabled": self.use_oauth,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "available_models": self.get_available_models(),
            "token_valid": self.auth.is_token_valid() if self.auth else None
        }
