"""
Smart model selection for GigaChat based on query complexity
Based on GigaChat API documentation and tarot reading requirements
"""

import re
import logging
from typing import Dict, List
from decouple import config

logger = logging.getLogger(__name__)


class GigaChatModelSelector:
    """
    Intelligent model selection for GigaChat API based on query complexity,
    tarot reading requirements, and available models
    """

    def __init__(self):
        """Initialize model selector with available models and selection criteria"""

        # Available models from documentation with their characteristics
        self.models = {
            "basic": {
                "name": "GigaChat",
                "description": "Basic model for simple tasks",
                "best_for": ["simple conversations", "basic questions", "quick responses"],
                "token_limit": "lower",
                "cost": "lowest",
                "recommended_for": ["greeting", "simple_question", "short_response"]
            },
            "advanced": {
                "name": "GigaChat-Max",
                "description": "Advanced model for complex tasks",
                "best_for": ["complex reasoning", "detailed analysis", "tarot interpretation"],
                "token_limit": "higher",
                "cost": "medium",
                "recommended_for": ["tarot_reading", "complex_analysis", "detailed_explanation"]
            },
            "professional": {
                "name": "GigaChat-Pro",
                "description": "Professional model for specialized tasks",
                "best_for": ["specialized tasks", "maximum quality", "premium interpretations"],
                "token_limit": "highest",
                "cost": "highest",
                "recommended_for": ["premium_reading", "specialized_analysis", "professional_consultation"]
            }
        }

        # Default model from environment or fallback to advanced for tarot readings
        self.default_model = config('GIGACHAT_DEFAULT_MODEL', default='GigaChat-Max')

        # Keywords for different complexity levels (Russian language focused)
        self.complexity_keywords = {
            "simple": [
                "привет", "здравствуй", "как дела", "что такое", "кто это",
                "спасибо", "пока", "до свидания", "да", "нет"
            ],
            "complex": [
                "анализ", "объясни", "интерпретация", "толкование", "значение",
                "расклад", "карта", "таро", "предсказание", "совет",
                "будущее", "прошлое", "отношения", "работа", "любовь"
            ],
            "specialized": [
                "глубокий анализ", "детальное толкование", "профессиональная консультация",
                "эзотерический смысл", "кармическое значение", "духовное развитие",
                "архетипическое значение", "психологический портрет"
            ]
        }

        # Tarot-specific patterns that require advanced interpretation
        self.tarot_patterns = [
            r"карт[ауыеи]",  # карта, карты, карте, etc.
            r"расклад",
            r"таро",
            r"значение.*карт",
            r"толкование.*карт",
            r"интерпретац",
            r"предсказан",
            r"гадан"
        ]

    def select_model(self, query: str, context: Dict = None) -> str:
        """
        Select the most appropriate GigaChat model based on query complexity
        and tarot reading context

        Args:
            query (str): User query or tarot question
            context (Dict, optional): Additional context (reading type, user preferences, etc.)

        Returns:
            str: Selected model name
        """
        try:
            # Normalize query for analysis
            query_lower = query.lower().strip()

            # Context-based selection
            if context:
                # Check if premium/professional reading is requested
                if context.get('premium_reading', False):
                    logger.info("Premium reading requested - using GigaChat-Pro")
                    return self.models["professional"]["name"]

                # Check reading complexity preference
                complexity_preference = context.get('complexity', 'auto')
                if complexity_preference == 'simple':
                    return self.models["basic"]["name"]
                elif complexity_preference == 'professional':
                    return self.models["professional"]["name"]

            # Rule-based model selection
            selected_model = self._analyze_query_complexity(query_lower)

            # Validate model availability (fallback to default if needed)
            if not self._is_model_available(selected_model):
                logger.warning(f"Model {selected_model} not available, falling back to {self.default_model}")
                selected_model = self.default_model

            logger.info(f"Selected model: {selected_model} for query length: {len(query)}")
            return selected_model

        except Exception as e:
            logger.error(f"Error in model selection: {str(e)}", exc_info=True)
            return self.default_model

    def _analyze_query_complexity(self, query: str) -> str:
        """
        Analyze query complexity using multiple heuristics

        Args:
            query (str): Normalized query string

        Returns:
            str: Selected model name
        """
        # Check for tarot-specific patterns (high priority)
        for pattern in self.tarot_patterns:
            if re.search(pattern, query):
                logger.debug(f"Tarot pattern found: {pattern}")
                return self.models["advanced"]["name"]

        # Check for specialized/professional keywords
        specialized_count = sum(1 for keyword in self.complexity_keywords["specialized"]
                               if keyword in query)
        if specialized_count > 0:
            logger.debug(f"Specialized keywords found: {specialized_count}")
            return self.models["professional"]["name"]

        # Check for complex keywords
        complex_count = sum(1 for keyword in self.complexity_keywords["complex"]
                           if keyword in query)
        if complex_count >= 2:  # Multiple complex keywords
            logger.debug(f"Multiple complex keywords found: {complex_count}")
            return self.models["advanced"]["name"]
        elif complex_count >= 1:
            logger.debug(f"Complex keywords found: {complex_count}")
            return self.models["advanced"]["name"]

        # Check for simple keywords
        simple_count = sum(1 for keyword in self.complexity_keywords["simple"]
                          if keyword in query)
        if simple_count > 0 and len(query) < 50:
            logger.debug(f"Simple keywords found: {simple_count}")
            return self.models["basic"]["name"]

        # Length-based heuristics
        if len(query) < 20:
            return self.models["basic"]["name"]
        elif len(query) > 200:
            return self.models["advanced"]["name"]

        # Default to advanced model for tarot application
        return self.models["advanced"]["name"]

    def _is_model_available(self, model_name: str) -> bool:
        """
        Check if the selected model is available

        Args:
            model_name (str): Model name to check

        Returns:
            bool: True if model is available
        """
        available_models = [model_info["name"] for model_info in self.models.values()]
        return model_name in available_models

    def get_model_info(self, model_name: str) -> Dict:
        """
        Get information about a specific model

        Args:
            model_name (str): Model name

        Returns:
            Dict: Model information or empty dict if not found
        """
        for model_type, model_info in self.models.items():
            if model_info["name"] == model_name:
                return {
                    "type": model_type,
                    "name": model_name,
                    "description": model_info["description"],
                    "best_for": model_info["best_for"],
                    "cost": model_info["cost"]
                }
        return {}

    def get_recommended_model_for_tarot(self, reading_type: str = "standard") -> str:
        """
        Get recommended model specifically for tarot readings

        Args:
            reading_type (str): Type of tarot reading (standard, detailed, premium)

        Returns:
            str: Recommended model name
        """
        if reading_type == "premium":
            return self.models["professional"]["name"]
        elif reading_type == "detailed":
            return self.models["advanced"]["name"]
        else:  # standard
            return self.models["advanced"]["name"]

    def explain_selection(self, query: str, selected_model: str) -> str:
        """
        Provide explanation for model selection (useful for debugging/logging)

        Args:
            query (str): Original query
            selected_model (str): Selected model name

        Returns:
            str: Explanation of selection
        """
        model_info = self.get_model_info(selected_model)
        if not model_info:
            return f"Unknown model: {selected_model}"

        return (f"Selected {model_info['name']} ({model_info['type']}) "
                f"for query of length {len(query)}. "
                f"Best for: {', '.join(model_info['best_for'][:2])}")


# Global instance for easy import
model_selector = GigaChatModelSelector()


def select_model_for_query(query: str, context: Dict = None) -> str:
    """
    Convenience function for model selection

    Args:
        query (str): User query
        context (Dict, optional): Additional context

    Returns:
        str: Selected model name
    """
    return model_selector.select_model(query, context)