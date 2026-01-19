from django.db import models

class Card(models.Model):
    SUITS = [
        ('MA', 'Старшие арканы'),
        ('CU', 'Кубки'),
        ('PE', 'Пентакли'),
        ('SW', 'Мечи'),
        ('WA', 'Жезлы'),
    ]

    name = models.CharField(max_length=100, verbose_name='Название на русском')
    english_name = models.CharField(max_length=100, verbose_name='Название на английском', null=True, blank=True)
    suit = models.CharField(max_length=2, choices=SUITS)
    number = models.CharField(max_length=2)
    image = models.CharField(max_length=20)
    meaning_upright = models.TextField()
    meaning_reversed = models.TextField()

    def __str__(self):
        return f"{self.get_suit_display()} - {self.name}"

class Reading(models.Model):
    GENDER_CHOICES = [
        ('М', 'Мужской'),
        ('Ж', 'Женский'),
    ]
    
    created_at = models.DateTimeField(auto_now_add=True)
    user_age = models.IntegerField(null=False)
    user_gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    question = models.TextField(null=True, blank=True)
    interpretation = models.TextField(null=True, blank=True)
    cards = models.ManyToManyField(Card, through='CardPosition')
    
    def __str__(self):
        return f"Расклад для {self.get_user_gender_display()}, {self.user_age} лет - {self.created_at}"

class CardPosition(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    reading = models.ForeignKey(Reading, on_delete=models.CASCADE)
    position = models.IntegerField()
    is_reversed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['position'] 