from django.core.cache import cache
from django.db import models, transaction

GENDER_CHOICES = [
    ('М', 'Мужской'),
    ('Ж', 'Женский'),
]

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
    GENDER_CHOICES = GENDER_CHOICES

    created_at = models.DateTimeField(auto_now_add=True)
    user_age = models.IntegerField(null=False)
    user_gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    question = models.TextField(null=True, blank=True)
    interpretation = models.TextField(null=True, blank=True)
    cards = models.ManyToManyField(Card, through='CardPosition')
    
    def __str__(self):
        return f"Расклад для {self.get_user_gender_display()}, {self.user_age} лет - {self.created_at}"


class TelegramUserProfile(models.Model):
    telegram_user_id = models.BigIntegerField(unique=True)
    chat_id = models.BigIntegerField(null=True, blank=True)
    username = models.CharField(max_length=150, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    user_age = models.IntegerField(null=True, blank=True)
    user_gender = models.CharField(max_length=20, choices=GENDER_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Telegram user {self.telegram_user_id}"


class PromptConfig(models.Model):
    name = models.CharField(max_length=120, default="Основной промпт")
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Промпт"
        verbose_name_plural = "Промпты"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.is_active:
                PromptConfig.objects.exclude(pk=self.pk).update(is_active=False)
        self.__class__.clear_cache()

    @classmethod
    def get_active_prompt(cls, default=""):
        cached = cache.get(cls._cache_key())
        if cached:
            return cached
        prompt = cls.objects.filter(is_active=True).order_by("-updated_at").first()
        content = prompt.content if prompt and prompt.content else default
        cache.set(cls._cache_key(), content, 300)
        return content

    @classmethod
    def clear_cache(cls):
        cache.delete(cls._cache_key())

    @staticmethod
    def _cache_key():
        return "tarot_prompt_active_v1"


class InteractionRetentionConfig(models.Model):
    retention_days = models.PositiveIntegerField(default=365)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Хранение истории"
        verbose_name_plural = "Хранение истории"

    def __str__(self):
        status = "включено" if self.is_enabled else "выключено"
        return f"{self.retention_days} дней ({status})"

    @classmethod
    def get_retention_days(cls):
        config = cls.objects.order_by("-updated_at").first()
        if not config:
            return 365
        if not config.is_enabled:
            return None
        return config.retention_days


class InteractionLog(models.Model):
    SOURCE_WEB = "web"
    SOURCE_TELEGRAM = "telegram"
    SOURCE_CHOICES = [
        (SOURCE_WEB, "Web"),
        (SOURCE_TELEGRAM, "Telegram"),
    ]

    DIRECTION_IN = "in"
    DIRECTION_OUT = "out"
    DIRECTION_SYSTEM = "system"
    DIRECTION_CHOICES = [
        (DIRECTION_IN, "Входящее"),
        (DIRECTION_OUT, "Исходящее"),
        (DIRECTION_SYSTEM, "Системное"),
    ]

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    event_type = models.CharField(max_length=64)
    user_identifier = models.CharField(max_length=128, blank=True)
    content = models.TextField(blank=True)
    metadata = models.JSONField(blank=True, null=True)
    reading = models.ForeignKey(Reading, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source", "created_at"]),
            models.Index(fields=["user_identifier"]),
        ]

    def __str__(self):
        return f"{self.source}:{self.direction}:{self.event_type}"

class CardPosition(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    reading = models.ForeignKey(Reading, on_delete=models.CASCADE)
    position = models.IntegerField()
    is_reversed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['position'] 
