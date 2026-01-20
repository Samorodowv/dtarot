import asyncio
import logging
import random

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update

from .exceptions import InsufficientCardsException
from .models import CardPosition, Reading, TelegramUserProfile
from .monitoring import MonitoringUtils
from .services import CardService, RateLimitService, ReadingService


logger = logging.getLogger(__name__)

STATE_TTL_SECONDS = 86400
STATE_AWAITING_AGE = "awaiting_age"
STATE_AWAITING_GENDER = "awaiting_gender"
STATE_AWAITING_QUESTION = "awaiting_question"
STATE_RATE_LIMITED = "rate_limited"


def handle_telegram_update(payload):
    token = _get_bot_token()
    if not token:
        logger.warning("Telegram bot token is not configured; update ignored.")
        return

    coro = _handle_telegram_update_async(payload, token)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
    else:
        loop.create_task(coro)


async def _handle_telegram_update_async(payload, token):
    async with Bot(token=token) as bot:
        update = Update.de_json(payload, bot)
        if update.message:
            await _handle_message(update.message, bot)
            return
        if update.callback_query:
            await _handle_callback_query(update.callback_query, bot)


def _get_bot_token():
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    return token or None


async def _handle_message(message, bot):
    if not message or not message.chat or not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    text = (message.text or "").strip()

    if not text:
        await bot.send_message(chat_id=chat_id, text="Пожалуйста, отправьте текстовое сообщение.")
        return

    if text.startswith(("/start", "/reading", "/new")):
        await _start_reading_flow(user_id, chat_id, message.from_user, bot)
        return

    if text.startswith("/promo"):
        await _handle_promo_command(user_id, chat_id, text, message.from_user, bot)
        return

    if text.startswith("/help"):
        await _send_help(chat_id, bot)
        return

    if text.startswith("/cancel"):
        _clear_state(user_id)
        _clear_data(user_id)
        await bot.send_message(chat_id=chat_id, text="Диалог сброшен. Отправьте /start для нового расклада.")
        return

    state = _get_state(user_id)
    if state == STATE_AWAITING_AGE:
        await _handle_age_input(user_id, chat_id, text, bot)
        return
    if state == STATE_AWAITING_GENDER:
        await _handle_gender_text(user_id, chat_id, text, bot)
        return
    if state == STATE_AWAITING_QUESTION:
        await _handle_question_input(user_id, chat_id, text, bot)
        return

    await _send_help(chat_id, bot)


async def _handle_callback_query(callback_query, bot):
    if not callback_query or not callback_query.from_user or not callback_query.message:
        return

    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    data = callback_query.data or ""

    if data.startswith("gender:"):
        gender = data.split(":", 1)[1]
        if gender not in {"М", "Ж"}:
            await bot.answer_callback_query(callback_query.id, text="Неизвестный вариант.")
            return

        _update_data(user_id, user_gender=gender)
        await sync_to_async(_upsert_profile, thread_sensitive=True)(user_id, user_gender=gender)
        _set_state(user_id, STATE_AWAITING_QUESTION)
        await bot.answer_callback_query(callback_query.id)
        await bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=callback_query.message.message_id,
            reply_markup=None,
        )
        await _prompt_question(user_id, chat_id, bot)
        return

    await bot.answer_callback_query(callback_query.id)


async def _send_help(chat_id, bot):
    await bot.send_message(
        chat_id=chat_id,
        text=(
            "Доступные команды:\n"
            "/start — начать новый расклад\n"
            "/promo <код> — применить промокод\n"
            "/cancel — сбросить текущий диалог"
        ),
    )


async def _start_reading_flow(user_id, chat_id, user, bot):
    session_key = _session_key(user_id)
    can_create, time_left = RateLimitService.can_create_reading(session_key)
    if not can_create:
        _set_state(user_id, STATE_RATE_LIMITED)
        _clear_data(user_id)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "Следующий расклад будет доступен через "
                f"{_format_time_left(time_left)}.\n"
                "Можно использовать промокод: отправьте /promo <код>."
            ),
        )
        return

    profile = await sync_to_async(_upsert_profile, thread_sensitive=True)(
        user_id,
        chat_id=chat_id,
        username=_normalize_user_field(getattr(user, "username", None)),
        first_name=_normalize_user_field(getattr(user, "first_name", None)),
        last_name=_normalize_user_field(getattr(user, "last_name", None)),
    )

    _clear_data(user_id)
    if profile.user_age is not None:
        _update_data(user_id, user_age=profile.user_age)
    if profile.user_gender:
        _update_data(user_id, user_gender=profile.user_gender)

    if profile.user_age is not None and profile.user_gender:
        _set_state(user_id, STATE_AWAITING_QUESTION)
        await _prompt_question(user_id, chat_id, bot)
        return

    if profile.user_age is not None:
        _set_state(user_id, STATE_AWAITING_GENDER)
        await bot.send_message(chat_id=chat_id, text="Выберите пол:", reply_markup=_gender_keyboard())
        return

    _set_state(user_id, STATE_AWAITING_AGE)
    await bot.send_message(chat_id=chat_id, text="Сколько вам лет?")


async def _handle_promo_command(user_id, chat_id, text, user, bot):
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await bot.send_message(chat_id=chat_id, text="Введите промокод: /promo <код>.")
        return

    promo_code = parts[1].strip()
    if RateLimitService.apply_promo_code(_session_key(user_id), promo_code):
        await bot.send_message(chat_id=chat_id, text="Промокод применен. Можно начинать расклад.")
        if _get_state(user_id) == STATE_RATE_LIMITED:
            await _start_reading_flow(user_id, chat_id, user, bot)
    else:
        await bot.send_message(chat_id=chat_id, text="Неверный промокод.")


async def _handle_age_input(user_id, chat_id, text, bot):
    try:
        age = int(text)
    except ValueError:
        await bot.send_message(chat_id=chat_id, text="Введите возраст числом (от 18 до 100).")
        return

    if age < 18 or age > 100:
        await bot.send_message(chat_id=chat_id, text="Возраст должен быть от 18 до 100 лет.")
        return

    _update_data(user_id, user_age=age)
    await sync_to_async(_upsert_profile, thread_sensitive=True)(user_id, user_age=age)
    _set_state(user_id, STATE_AWAITING_GENDER)
    await bot.send_message(chat_id=chat_id, text="Выберите пол:", reply_markup=_gender_keyboard())


async def _handle_gender_text(user_id, chat_id, text, bot):
    gender = _parse_gender(text)
    if not gender:
        await bot.send_message(chat_id=chat_id, text="Пожалуйста, выберите пол кнопкой ниже.")
        await bot.send_message(chat_id=chat_id, text="Выберите пол:", reply_markup=_gender_keyboard())
        return

    _update_data(user_id, user_gender=gender)
    await sync_to_async(_upsert_profile, thread_sensitive=True)(user_id, user_gender=gender)
    _set_state(user_id, STATE_AWAITING_QUESTION)
    await _prompt_question(user_id, chat_id, bot)


async def _prompt_question(user_id, chat_id, bot):
    session_key = _session_key(user_id)
    promo_applied = RateLimitService.is_promo_applied(session_key)
    if promo_applied:
        await bot.send_message(
            chat_id=chat_id,
            text="Напишите ваш вопрос или отправьте /skip для общего расклада.",
        )
    else:
        await bot.send_message(chat_id=chat_id, text="Напишите ваш вопрос к картам.")


async def _handle_question_input(user_id, chat_id, text, bot):
    session_key = _session_key(user_id)
    promo_applied = RateLimitService.is_promo_applied(session_key)

    if text.startswith("/skip"):
        if not promo_applied:
            await bot.send_message(chat_id=chat_id, text="Без промокода вопрос обязателен.")
            return
        question = ""
    else:
        question = text

    if not question.strip() and not promo_applied:
        await bot.send_message(chat_id=chat_id, text="Пожалуйста, введите вопрос.")
        return

    can_create, time_left = RateLimitService.can_create_reading(session_key)
    if not can_create:
        _set_state(user_id, STATE_RATE_LIMITED)
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "Вы недавно делали расклад. Следующий будет доступен через "
                f"{_format_time_left(time_left)}."
            ),
        )
        return

    data = _get_data(user_id)
    user_age = data.get("user_age")
    user_gender = data.get("user_gender")
    if user_age is None or user_gender is None:
        profile = await sync_to_async(_get_profile, thread_sensitive=True)(user_id)
        if profile and profile.user_age is not None and profile.user_gender:
            _update_data(user_id, user_age=profile.user_age, user_gender=profile.user_gender)
            user_age = profile.user_age
            user_gender = profile.user_gender
    if user_age is None or user_gender is None:
        _set_state(user_id, STATE_AWAITING_AGE)
        await bot.send_message(chat_id=chat_id, text="Начнем сначала. Сколько вам лет?")
        return

    try:
        reading, _positions = await sync_to_async(_create_reading, thread_sensitive=True)(
            user_age,
            user_gender,
            question,
            session_key,
        )
    except InsufficientCardsException:
        await bot.send_message(
            chat_id=chat_id,
            text="В базе данных недостаточно карт для расклада. Попробуйте позже.",
        )
        _clear_state(user_id)
        _clear_data(user_id)
        return
    except Exception as exc:
        logger.error("Failed to create telegram reading: %s", exc, exc_info=True)
        await bot.send_message(
            chat_id=chat_id,
            text="Произошла ошибка при создании расклада. Попробуйте позже.",
        )
        _clear_state(user_id)
        _clear_data(user_id)
        return

    _clear_state(user_id)
    _clear_data(user_id)
    await bot.send_message(
        chat_id=chat_id,
        text="Карты выбраны. Сейчас отправлю изображения и значения, затем интерпретацию.",
    )

    from .tasks import send_telegram_reading

    send_telegram_reading.delay(reading.id, chat_id)


def _create_reading(user_age, user_gender, question, session_key):
    with transaction.atomic():
        reading = Reading.objects.create(
            user_age=user_age,
            user_gender=user_gender,
            question=question,
        )

        if not reading.question or not reading.question.strip():
            reading.question = "Общий расклад на ближайшее будущее"
            reading.save(update_fields=["question"])

        MonitoringUtils.track_reading_creation()

        cards = CardService.get_all_cards()
        if len(cards) < 5:
            raise InsufficientCardsException(
                f"Insufficient cards in database: {len(cards)} available, 5 required"
            )

        selected_cards = random.sample(cards, 5)
        positions = []
        for position_index, card in enumerate(selected_cards):
            card_position = CardPosition.objects.create(
                reading=reading,
                card=card,
                position=position_index,
                is_reversed=random.choice([True, False]),
            )
            positions.append(card_position)

        RateLimitService.record_reading(session_key)
        ReadingService.set_reading_status(reading.id, "processing")

    return reading, positions


def _normalize_user_field(value):
    return value if value else None


def _get_profile(user_id):
    return TelegramUserProfile.objects.filter(telegram_user_id=user_id).first()


def _upsert_profile(user_id, **updates):
    profile, _ = TelegramUserProfile.objects.get_or_create(telegram_user_id=user_id)
    updated = False
    for field, value in updates.items():
        if value is None:
            continue
        if getattr(profile, field) != value:
            setattr(profile, field, value)
            updated = True
    if updated:
        profile.save()
    return profile


def _gender_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Мужской", callback_data="gender:М"),
                InlineKeyboardButton("Женский", callback_data="gender:Ж"),
            ]
        ]
    )


def _parse_gender(text):
    normalized = text.strip().lower()
    if normalized in {"м", "муж", "мужской", "male"}:
        return "М"
    if normalized in {"ж", "жен", "женский", "female"}:
        return "Ж"
    return None


def _format_time_left(time_left):
    if not time_left:
        return "00:00"
    total_seconds = int(time_left.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def _session_key(user_id):
    return f"telegram_{user_id}"


def _state_key(user_id):
    return f"telegram_state_{user_id}"


def _data_key(user_id):
    return f"telegram_data_{user_id}"


def _get_state(user_id):
    return cache.get(_state_key(user_id))


def _set_state(user_id, state):
    cache.set(_state_key(user_id), state, STATE_TTL_SECONDS)


def _clear_state(user_id):
    cache.delete(_state_key(user_id))


def _get_data(user_id):
    return cache.get(_data_key(user_id), {}) or {}


def _update_data(user_id, **updates):
    data = _get_data(user_id)
    data.update(updates)
    cache.set(_data_key(user_id), data, STATE_TTL_SECONDS)
    return data


def _clear_data(user_id):
    cache.delete(_data_key(user_id))
