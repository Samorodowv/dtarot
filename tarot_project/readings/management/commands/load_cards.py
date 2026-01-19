from django.core.management.base import BaseCommand
from readings.models import Card

class Command(BaseCommand):
    help = 'Loads initial tarot card data'

    def handle(self, *args, **kwargs):
        # Major Arcana
        major_arcana = [
            ('The Fool', '00', 'New beginnings, innocence, spontaneity', 'Recklessness, risk-taking, foolishness'),
            ('The Magician', '01', 'Manifestation, resourcefulness, power', 'Manipulation, poor planning, untapped talents'),
            # Add more cards...
        ]

        for name, number, upright, reversed in major_arcana:
            Card.objects.get_or_create(
                name=name,
                suit='MA',
                number=number,
                image=f'ar{number}.jpg',
                meaning_upright=upright,
                meaning_reversed=reversed
            )

        # Add other suits (Cups, Pentacles, Swords, Wands)
        suits = {
            'CU': 'cu',
            'PE': 'pe',
            'SW': 'sw',
            'WA': 'wa'
        }

        court_cards = {
            'AC': ('Ace', 'ac'),
            'PA': ('Page', 'pa'),
            'KN': ('Knight', 'kn'),
            'QU': ('Queen', 'qu'),
            'KI': ('King', 'ki')
        }

        for suit_code, prefix in suits.items():
            # Number cards (2-10)
            for num in range(2, 11):
                num_str = f'0{num}' if num < 10 else str(num)
                Card.objects.get_or_create(
                    name=f'{num} of {dict(Card.SUITS)[suit_code]}',
                    suit=suit_code,
                    number=num_str,
                    image=f'{prefix}{num_str}.jpg',
                    meaning_upright='Upright meaning for ' + str(num),
                    meaning_reversed='Reversed meaning for ' + str(num)
                )

            # Court cards
            for code, (name, suffix) in court_cards.items():
                Card.objects.get_or_create(
                    name=f'{name} of {dict(Card.SUITS)[suit_code]}',
                    suit=suit_code,
                    number=code,
                    image=f'{prefix}{suffix}.jpg',
                    meaning_upright=f'Upright meaning for {name}',
                    meaning_reversed=f'Reversed meaning for {name}'
                )

        self.stdout.write(self.style.SUCCESS('Successfully loaded card data')) 