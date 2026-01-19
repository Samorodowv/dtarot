"""
Unit tests for Tarot models
"""

import pytest
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from freezegun import freeze_time

from tarot_readings.models import Card, Reading, CardPosition


@pytest.mark.django_db
class TestCardModel:
    """Test Card model functionality"""
    
    def test_card_creation(self):
        """Test basic card creation"""
        card = Card.objects.create(
            name="Шут",
            english_name="The Fool",
            suit="major",
            number=0,
            meaning_upright="Новые начинания",
            meaning_reversed="Безрассудство",
            image="ar00.jpg"
        )
        
        assert card.name == "Шут"
        assert card.english_name == "The Fool"
        assert card.suit == "major"
        assert card.number == 0
        assert card.image == "ar00.jpg"
        
    def test_card_str_representation(self):
        """Test card string representation"""
        card = Card.objects.create(
            name="Маг",
            english_name="The Magician",
            suit="major",
            number=1,
            meaning_upright="Сила воли",
            meaning_reversed="Манипуляции",
            image="ar01.jpg"
        )
        
        assert str(card) == "The Magician (Маг)"
        
    def test_card_suit_choices(self):
        """Test valid suit choices"""
        valid_suits = ["major", "cups", "swords", "wands", "pentacles"]
        
        for suit in valid_suits:
            card = Card(
                name=f"Тест {suit}",
                english_name=f"Test {suit}",
                suit=suit,
                number=1,
                meaning_upright="Test meaning",
                meaning_reversed="Test reversed",
                image="test.jpg"
            )
            card.full_clean()  # Should not raise ValidationError
            
    def test_card_unique_constraint(self):
        """Test that cards with same suit and number are unique"""
        Card.objects.create(
            name="Туз Кубков",
            english_name="Ace of Cups",
            suit="cups",
            number=1,
            meaning_upright="Новая любовь",
            meaning_reversed="Эмоциональная блокировка",
            image="cuac.jpg"
        )
        
        # Attempting to create another card with same suit and number should fail
        with pytest.raises(IntegrityError):
            Card.objects.create(
                name="Другой Туз Кубков",
                english_name="Another Ace of Cups",
                suit="cups",
                number=1,
                meaning_upright="Другое значение",
                meaning_reversed="Другое обращенное значение",
                image="cuac2.jpg"
            )


@pytest.mark.django_db
class TestReadingModel:
    """Test Reading model functionality"""
    
    def test_reading_creation(self):
        """Test basic reading creation"""
        reading = Reading.objects.create(
            user_age=25,
            user_gender="female",
            question="Как улучшить мою карьеру?",
            interpretation="Ваши карты указывают на позитивные изменения."
        )
        
        assert reading.user_age == 25
        assert reading.user_gender == "female"
        assert reading.question == "Как улучшить мою карьеру?"
        assert reading.interpretation == "Ваши карты указывают на позитивные изменения."
        assert reading.created_at is not None
        
    def test_reading_str_representation(self):
        """Test reading string representation"""
        reading = Reading.objects.create(
            user_age=30,
            user_gender="male",
            question="Что меня ждет в любви?",
            interpretation="Тестовая интерпретация"
        )
        
        expected = f"Reading {reading.id}: Что меня ждет в любви?"
        assert str(reading) == expected
        
    def test_reading_gender_choices(self):
        """Test valid gender choices"""
        valid_genders = ["male", "female", "other"]
        
        for gender in valid_genders:
            reading = Reading(
                user_age=25,
                user_gender=gender,
                question="Тестовый вопрос",
                interpretation="Тестовая интерпретация"
            )
            reading.full_clean()  # Should not raise ValidationError
            
    def test_reading_age_validation(self):
        """Test age validation"""
        # Valid age
        reading = Reading(
            user_age=25,
            user_gender="female",
            question="Тестовый вопрос",
            interpretation="Тестовая интерпретация"
        )
        reading.full_clean()  # Should not raise
        
    @freeze_time("2024-01-15 12:00:00")
    def test_reading_created_at_auto_now(self):
        """Test that created_at is automatically set"""
        reading = Reading.objects.create(
            user_age=25,
            user_gender="female",
            question="Тестовый вопрос"
        )
        
        from django.utils import timezone
        expected_time = timezone.now()
        assert reading.created_at == expected_time


@pytest.mark.django_db
class TestCardPositionModel:
    """Test CardPosition model functionality"""
    
    def test_card_position_creation(self, sample_cards, sample_reading):
        """Test basic card position creation"""
        card = sample_cards[0]
        reading = sample_reading
        
        position = CardPosition.objects.create(
            reading=reading,
            card=card,
            position=0,
            is_reversed=True
        )
        
        assert position.reading == reading
        assert position.card == card
        assert position.position == 0
        assert position.is_reversed is True
        
    def test_card_position_str_representation(self, sample_cards, sample_reading):
        """Test card position string representation"""
        card = sample_cards[0]
        reading = sample_reading
        
        position = CardPosition.objects.create(
            reading=reading,
            card=card,
            position=2,
            is_reversed=False
        )
        
        expected = f"Position 2: {card.english_name} (upright)"
        assert str(position) == expected
        
        position.is_reversed = True
        position.save()
        expected = f"Position 2: {card.english_name} (reversed)"
        assert str(position) == expected
        
    def test_card_position_unique_constraint(self, sample_cards, sample_reading):
        """Test that positions within a reading are unique"""
        card1 = sample_cards[0]
        card2 = sample_cards[1] 
        reading = sample_reading
        
        CardPosition.objects.create(
            reading=reading,
            card=card1,
            position=0,
            is_reversed=False
        )
        
        # Same position in same reading should fail
        with pytest.raises(IntegrityError):
            CardPosition.objects.create(
                reading=reading,
                card=card2,
                position=0,
                is_reversed=True
            )
            
    def test_card_position_ordering(self, sample_cards, sample_reading):
        """Test that card positions are ordered correctly"""
        reading = sample_reading
        
        # Create positions out of order
        CardPosition.objects.create(
            reading=reading,
            card=sample_cards[2],
            position=2,
            is_reversed=False
        )
        CardPosition.objects.create(
            reading=reading,
            card=sample_cards[0],
            position=0,
            is_reversed=True
        )
        CardPosition.objects.create(
            reading=reading,
            card=sample_cards[1],
            position=1,
            is_reversed=False
        )
        
        # Retrieve positions ordered by position
        positions = CardPosition.objects.filter(reading=reading).order_by('position')
        
        assert list(positions.values_list('position', flat=True)) == [0, 1, 2]
        assert positions[0].card == sample_cards[0]
        assert positions[1].card == sample_cards[1] 
        assert positions[2].card == sample_cards[2]