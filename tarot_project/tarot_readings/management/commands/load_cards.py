from django.core.management.base import BaseCommand
from tarot_readings.models import Card

class Command(BaseCommand):
    help = 'Loads initial tarot card data'

    def handle(self, *args, **kwargs):
        # Major Arcana
        major_arcana = [
            ('The Fool', '00', 'New beginnings, innocence, spontaneity, free spirit', 'Recklessness, risk-taking, foolish decisions'),
            ('The Magician', '01', 'Manifestation, resourcefulness, power, inspired action', 'Manipulation, poor planning, untapped talents'),
            ('The High Priestess', '02', 'Intuition, sacred knowledge, divine feminine, the subconscious mind', 'Secrets, disconnected from intuition, withdrawal and silence'),
            ('The Empress', '03', 'Femininity, beauty, nature, nurturing, abundance', 'Creative block, dependence on others, empty nurturing'),
            ('The Emperor', '04', 'Authority, establishment, structure, a father figure', 'Domination, excessive control, lack of discipline, inflexibility'),
            ('The Hierophant', '05', 'Spiritual wisdom, religious beliefs, conformity, tradition', 'Challenge to the status quo, personal beliefs, freedom'),
            ('The Lovers', '06', 'Love, harmony, relationships, values alignment, choices', 'Self-love, disharmony, imbalance, misalignment of values'),
            ('The Chariot', '07', 'Control, willpower, success, ambition, determination', 'Self-discipline, opposition, lack of direction'),
            ('Strength', '08', 'Strength, courage, persuasion, influence, compassion', 'Inner strength, self-doubt, low energy, raw emotion'),
            ('The Hermit', '09', 'Soul-searching, introspection, being alone, inner guidance', 'Isolation, loneliness, withdrawal'),
            ('Wheel of Fortune', '10', 'Good luck, karma, life cycles, destiny, a turning point', 'Bad luck, resistance to change, breaking cycles'),
            ('Justice', '11', 'Justice, fairness, truth, cause and effect, law', 'Unfairness, lack of accountability, dishonesty'),
            ('The Hanged Man', '12', 'Pause, surrender, letting go, new perspectives', 'Delays, resistance, stalling, indecision'),
            ('Death', '13', 'Endings, change, transformation, transition', 'Resistance to change, inability to move on, repeating negative patterns'),
            ('Temperance', '14', 'Balance, moderation, patience, purpose', 'Imbalance, excess, lack of long-term vision'),
            ('The Devil', '15', 'Shadow self, attachment, addiction, restriction', 'Releasing limiting beliefs, exploring dark thoughts, detachment'),
            ('The Tower', '16', 'Sudden change, upheaval, chaos, revelation, awakening', 'Disaster avoided, fear of change, delaying the inevitable'),
            ('The Star', '17', 'Hope, faith, purpose, renewal, spirituality', 'Lack of faith, despair, disconnection from self'),
            ('The Moon', '18', 'Illusion, fear, anxiety, subconscious, intuition', 'Release of fear, repressed emotion, inner confusion'),
            ('The Sun', '19', 'Positivity, fun, warmth, success, vitality', 'Inner child, feeling down, overly optimistic'),
            ('Judgement', '20', 'Judgement, rebirth, inner calling, absolution', 'Self-doubt, inner critic, ignoring the call'),
            ('The World', '21', 'Completion, integration, accomplishment, travel', 'Seeking closure, short-cuts, delays'),
        ]

        # Create Major Arcana cards
        for name, number, upright, reversed in major_arcana:
            Card.objects.get_or_create(
                name=name,
                suit='MA',
                number=number,
                image=f'ar{number}.jpg',
                meaning_upright=upright,
                meaning_reversed=reversed
            )

        # Minor Arcana suits
        suits = {
            'CU': ('Cups', 'cu', 'emotions, intuition, relationships'),
            'PE': ('Pentacles', 'pe', 'material aspects, work, finances'),
            'SW': ('Swords', 'sw', 'intellect, thoughts, challenges'),
            'WA': ('Wands', 'wa', 'passion, energy, spirituality')
        }

        # Court cards with meanings
        court_cards = {
            'AC': ('Ace', 'ac', 'New beginnings', 'Missed opportunities'),
            'PA': ('Page', 'pa', 'New ideas, learning', 'Procrastination, immaturity'),
            'KN': ('Knight', 'kn', 'Action, adventure', 'Recklessness, inconsistency'),
            'QU': ('Queen', 'qu', 'Nurturing, expression', 'Repressed feelings, moodiness'),
            'KI': ('King', 'ki', 'Mastery, control', 'Abuse of power, manipulation')
        }

        # Create Minor Arcana cards
        for suit_code, (suit_name, prefix, suit_theme) in suits.items():
            # Number cards (2-10)
            for num in range(2, 11):
                num_str = f'0{num}' if num < 10 else str(num)
                Card.objects.get_or_create(
                    name=f'{num} of {suit_name}',
                    suit=suit_code,
                    number=num_str,
                    image=f'{prefix}{num_str}.jpg',
                    meaning_upright=f'Upright meanings related to {suit_theme} ({num})',
                    meaning_reversed=f'Reversed meanings related to {suit_theme} ({num})'
                )

            # Court cards
            for code, (rank, suffix, upright, reversed) in court_cards.items():
                Card.objects.get_or_create(
                    name=f'{rank} of {suit_name}',
                    suit=suit_code,
                    number=code,
                    image=f'{prefix}{suffix}.jpg',
                    meaning_upright=f'{upright} in {suit_theme}',
                    meaning_reversed=f'{reversed} in {suit_theme}'
                )

        self.stdout.write(self.style.SUCCESS('Successfully loaded card data')) 