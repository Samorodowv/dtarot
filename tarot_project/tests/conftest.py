"""
Pytest configuration and fixtures
"""

import pytest
from django.test import Client
from django.core.cache import cache
from django.contrib.sessions.models import Session
from unittest.mock import Mock, patch
import factory
from freezegun import freeze_time

from tarot_readings.models import Card, Reading, CardPosition


@pytest.fixture
def client():
    """Django test client"""
    return Client()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test"""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear sessions before each test"""
    Session.objects.all().delete()
    yield
    Session.objects.all().delete()


@pytest.fixture
def mock_gigachat():
    """Mock GigaChat API responses"""
    with patch('tarot_readings.gigachat_interpreter.GigaChat') as mock:
        mock_instance = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Тестовая интерпретация расклада Таро."
        mock_instance.chat.return_value = mock_response
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_cards():
    """Create sample tarot cards for testing"""
    cards = []
    
    # Major Arcana
    cards.append(Card.objects.create(
        name="Шут",
        english_name="The Fool",
        suit="major",
        number=0,
        meaning_upright="Новые начинания, спонтанность, невинность",
        meaning_reversed="Безрассудство, неосторожность, глупость",
        image="ar00.jpg"
    ))
    
    cards.append(Card.objects.create(
        name="Маг",
        english_name="The Magician", 
        suit="major",
        number=1,
        meaning_upright="Сила воли, желание, творение, проявление",
        meaning_reversed="Манипуляции, слабая воля, иллюзии",
        image="ar01.jpg"
    ))
    
    # Minor Arcana - Cups
    cards.append(Card.objects.create(
        name="Туз Кубков",
        english_name="Ace of Cups",
        suit="cups",
        number=1,
        meaning_upright="Новая любовь, эмоциональное пробуждение, интуиция",
        meaning_reversed="Эмоциональная блокировка, пустота, отрицание чувств",
        image="cuac.jpg"
    ))
    
    cards.append(Card.objects.create(
        name="Двойка Кубков",
        english_name="Two of Cups",
        suit="cups", 
        number=2,
        meaning_upright="Партнерство, единство, взаимная привлекательность",
        meaning_reversed="Разрыв, дисбаланс, недопонимание",
        image="cu02.jpg"
    ))
    
    # Minor Arcana - Swords
    cards.append(Card.objects.create(
        name="Туз Мечей",
        english_name="Ace of Swords",
        suit="swords",
        number=1,
        meaning_upright="Новые идеи, ментальная ясность, прорыв",
        meaning_reversed="Умственная путаница, плохая концентрация",
        image="swac.jpg"
    ))
    
    return cards


@pytest.fixture
def sample_reading(sample_cards):
    """Create a sample reading with cards"""
    reading = Reading.objects.create(
        user_age=25,
        user_gender="female",
        question="Как улучшить мою карьеру?",
        interpretation="Тестовая интерпретация расклада."
    )
    
    # Add card positions
    positions = []
    for i, card in enumerate(sample_cards):
        position = CardPosition.objects.create(
            reading=reading,
            card=card,
            position=i,
            is_reversed=(i % 2 == 0)  # Alternate reversed/upright
        )
        positions.append(position)
    
    return reading


@pytest.fixture
def frozen_time():
    """Freeze time for consistent testing"""
    with freeze_time("2024-01-15 12:00:00"):
        yield


class CardFactory(factory.django.DjangoModelFactory):
    """Factory for creating Card instances"""
    class Meta:
        model = Card
    
    name = factory.Sequence(lambda n: f"Карта {n}")
    english_name = factory.Sequence(lambda n: f"Card {n}")
    suit = factory.Iterator(["major", "cups", "swords", "wands", "pentacles"])
    number = factory.Sequence(lambda n: n % 22)
    meaning_upright = factory.Faker('sentence', nb_words=6)
    meaning_reversed = factory.Faker('sentence', nb_words=6)
    image = factory.Sequence(lambda n: f"card{n}.jpg")


class ReadingFactory(factory.django.DjangoModelFactory):
    """Factory for creating Reading instances"""
    class Meta:
        model = Reading
    
    user_age = factory.Faker('random_int', min=18, max=80)
    user_gender = factory.Iterator(["male", "female", "other"])
    question = factory.Faker('sentence', nb_words=8)
    interpretation = factory.Faker('text', max_nb_chars=500)


class CardPositionFactory(factory.django.DjangoModelFactory):
    """Factory for creating CardPosition instances"""
    class Meta:
        model = CardPosition
    
    reading = factory.SubFactory(ReadingFactory)
    card = factory.SubFactory(CardFactory)
    position = factory.Sequence(lambda n: n % 5)
    is_reversed = factory.Faker('boolean')


@pytest.fixture
def card_factory():
    """Card factory fixture"""
    return CardFactory


@pytest.fixture
def reading_factory():
    """Reading factory fixture"""
    return ReadingFactory


@pytest.fixture
def card_position_factory():
    """CardPosition factory fixture"""
    return CardPositionFactory