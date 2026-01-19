from django.core.management.base import BaseCommand
from tarot_readings.models import Card

class Command(BaseCommand):
    help = 'Updates English names for all Tarot cards'

    def handle(self, *args, **options):
        # Major Arcana translations
        major_arcana = {
            'The Fool': 'Шут',
            'The Magician': 'Маг',
            'The High Priestess': 'Верховная Жрица',
            'The Empress': 'Императрица',
            'The Emperor': 'Император',
            'The Hierophant': 'Иерофант',
            'The Lovers': 'Влюбленные',
            'The Chariot': 'Колесница',
            'Strength': 'Сила',
            'The Hermit': 'Отшельник',
            'Wheel of Fortune': 'Колесо Фортуны',
            'Justice': 'Справедливость',
            'The Hanged Man': 'Повешенный',
            'Death': 'Смерть',
            'Temperance': 'Умеренность',
            'The Devil': 'Дьявол',
            'The Tower': 'Башня',
            'The Star': 'Звезда',
            'The Moon': 'Луна',
            'The Sun': 'Солнце',
            'Judgement': 'Суд',
            'The World': 'Мир'
        }

        # Minor Arcana translations
        minor_arcana = {
            'Ace of Cups': 'Туз Кубков',
            'Ace of Pentacles': 'Туз Пентаклей',
            'Ace of Swords': 'Туз Мечей',
            'Ace of Wands': 'Туз Жезлов',
        }

        # Add numbered cards
        for num in range(2, 11):
            for suit_en, suit_ru in {'Cups': 'Кубков', 'Pentacles': 'Пентаклей', 
                                   'Swords': 'Мечей', 'Wands': 'Жезлов'}.items():
                en_name = f'{num} of {suit_en}'
                ru_name = f'{num} {suit_ru}'
                minor_arcana[en_name] = ru_name

        # Add court cards
        for court_en, court_ru in {'Page': 'Паж', 'Knight': 'Рыцарь', 
                                 'Queen': 'Королева', 'King': 'Король'}.items():
            for suit_en, suit_ru in {'Cups': 'Кубков', 'Pentacles': 'Пентаклей', 
                                   'Swords': 'Мечей', 'Wands': 'Жезлов'}.items():
                en_name = f'{court_en} of {suit_en}'
                ru_name = f'{court_ru} {suit_ru}'
                minor_arcana[en_name] = ru_name

        # Combine all translations
        all_cards = {**major_arcana, **minor_arcana}

        # Update all cards
        for english, russian in all_cards.items():
            try:
                card = Card.objects.get(name=english)
                # Store current English name as Russian name
                card.name = russian
                # Set proper English name
                card.english_name = english
                card.save()
                self.stdout.write(self.style.SUCCESS(f'Updated {english} -> {russian}'))
            except Card.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Card not found: {english}')) 