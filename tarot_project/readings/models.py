from django.db import models

class Card(models.Model):
    SUITS = [
        ('MA', 'Major Arcana'),
        ('CU', 'Cups'),
        ('PE', 'Pentacles'),
        ('SW', 'Swords'),
        ('WA', 'Wands'),
    ]

    name = models.CharField(max_length=100)
    suit = models.CharField(max_length=2, choices=SUITS)
    number = models.CharField(max_length=2)  # Using CharField to accommodate "AC", "KI", etc.
    image = models.CharField(max_length=20)  # For storing image filename (e.g., "ar00.jpg")
    meaning_upright = models.TextField()
    meaning_reversed = models.TextField()

    def __str__(self):
        return f"{self.get_suit_display()} - {self.name}"

class Reading(models.Model):
    READING_TYPES = [
        ('1', 'Single Card'),
        ('3', 'Three Card'),
        ('5', 'Five Card Cross'),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    reading_type = models.CharField(max_length=1, choices=READING_TYPES)
    cards = models.ManyToManyField(Card, through='CardPosition')
    
class CardPosition(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    reading = models.ForeignKey(Reading, on_delete=models.CASCADE)
    position = models.IntegerField()
    is_reversed = models.BooleanField(default=False) 