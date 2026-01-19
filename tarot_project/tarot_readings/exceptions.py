class GigaChatException(Exception):
    """Base exception for GigaChat API errors"""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class GigaChatAuthException(GigaChatException):
    """Raised when authentication with GigaChat fails (401 Unauthorized)"""

    def __init__(self, message: str = "Authentication failed with GigaChat API", status_code: int = 401, response_data: dict = None):
        super().__init__(message, status_code, response_data)


class GigaChatPaymentException(GigaChatException):
    """Raised when payment is required for GigaChat API (402 Payment Required)"""

    def __init__(self, message: str = "Payment required - please check your GigaChat account balance", status_code: int = 402, response_data: dict = None):
        super().__init__(message, status_code, response_data)


class GigaChatQuotaException(GigaChatException):
    """Raised when API quota is exceeded (429 Too Many Requests)"""

    def __init__(self, message: str = "API quota exceeded - please try again later", status_code: int = 429, response_data: dict = None):
        super().__init__(message, status_code, response_data)


class GigaChatAPIException(GigaChatException):
    """Raised when GigaChat API returns an error"""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message, status_code, response_data)


class GigaChatTimeoutException(GigaChatException):
    """Raised when GigaChat API request times out"""

    def __init__(self, message: str = "Request to GigaChat API timed out", status_code: int = None, response_data: dict = None):
        super().__init__(message, status_code, response_data)


class GigaChatModelUnavailableException(GigaChatException):
    """Raised when requested model is not available"""

    def __init__(self, model_name: str, message: str = None, status_code: int = None):
        if not message:
            message = f"Model '{model_name}' is not available"
        super().__init__(message, status_code)
        self.model_name = model_name


class GigaChatValidationException(GigaChatException):
    """Raised when request validation fails"""

    def __init__(self, message: str = "Request validation failed", status_code: int = 400, response_data: dict = None):
        super().__init__(message, status_code, response_data)

class TarotReadingException(Exception):
    """Base exception for tarot reading errors"""
    pass

class InsufficientCardsException(TarotReadingException):
    """Raised when there aren't enough cards in the database"""
    pass

class InvalidPromoCodeException(Exception):
    """Raised when an invalid promo code is used"""
    pass