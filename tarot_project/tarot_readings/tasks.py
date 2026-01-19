import asyncio
import io
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
import logging
import time
from .models import Reading, CardPosition, Card
from .gigachat_interpreter import TarotInterpreter
from .monitoring import MonitoringUtils
from .exceptions import (
    GigaChatException, GigaChatAuthException, GigaChatAPIException, 
    GigaChatTimeoutException
)
from .telegram_utils import build_cards_summary, get_card_image_path, split_message

try:
    from telegram import Bot, InputFile
    from telegram.error import TelegramError
except Exception:  # pragma: no cover - optional dependency at runtime
    Bot = None
    InputFile = None
    TelegramError = Exception

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency at runtime
    Image = None

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def interpret_reading(self, reading_id):
    """
    Async task to generate interpretation for a tarot reading
    """
    start_time = time.time()
    
    try:
        # Get reading and positions
        reading = Reading.objects.get(id=reading_id)
        positions = CardPosition.objects.filter(reading=reading).select_related('card').order_by('position')
        
        if not positions.exists():
            logger.error(f"No card positions found for reading {reading_id}")
            reading.interpretation = "Ошибка: карты для расклада не найдены."
            reading.save()
            MonitoringUtils.track_error("missing_positions", f"No positions for reading {reading_id}")
            return False
        
        # Generate interpretation
        interpreter = TarotInterpreter()
        interpretation = interpreter.interpret_reading(reading, positions)
        
        # Save interpretation
        reading.interpretation = interpretation
        reading.save()
        
        # Cache the result for quick access
        cache.set(f'reading_{reading_id}_status', 'completed', 300)
        
        # Track performance metrics
        duration = time.time() - start_time
        MonitoringUtils.track_interpretation_time(reading_id, duration)
        
        logger.info(f"Successfully generated interpretation for reading {reading_id}")
        return True
        
    except Reading.DoesNotExist:
        logger.error(f"Reading {reading_id} not found")
        return False
        
    except GigaChatAuthException as e:
        logger.error(f"GigaChat auth error for reading {reading_id}: {str(e)}")
        try:
            reading = Reading.objects.get(id=reading_id)
            # Provide a meaningful fallback interpretation
            reading.interpretation = f"""🔮 **Ваш расклад Таро**

💫 **Текущая ситуация**: Ваши карты указывают на период важных изменений. Энергии находятся в движении, и это время для принятия решений.

🌟 **Совет**: Доверьтесь своей интуиции и будьте открыты к новым возможностям. Карты говорят о том, что у вас есть все необходимые ресурсы для достижения целей.

🎯 **Прогноз**: Впереди вас ждут позитивные перемены. Оставайтесь сосредоточенными на своих желаниях и действуйте с уверенностью.

✨ Помните: карты - это инструмент самопознания. Их истинная сила заключается в том, как вы применяете полученную мудрость в своей жизни.

---
*Временно недоступна AI-интерпретация. Скоро сервис будет восстановлен.*"""
            reading.save()
        except:
            pass
        return False
        
    except GigaChatTimeoutException as e:
        logger.warning(f"GigaChat timeout for reading {reading_id}: {str(e)}")
        # Retry the task
        if self.request.retries < self.max_retries:
            cache.set(f'reading_{reading_id}_status', f'retrying_{self.request.retries + 1}', 300)
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        else:
            try:
                reading = Reading.objects.get(id=reading_id)
                reading.interpretation = "Извините, AI-сервис временно недоступен. Попробуйте создать новый расклад."
                reading.save()
            except:
                pass
            return False
            
    except GigaChatAPIException as e:
        logger.error(f"GigaChat API error for reading {reading_id}: {str(e)}")
        try:
            reading = Reading.objects.get(id=reading_id)
            reading.interpretation = "Возникла техническая проблема с интерпретацией. Карты выбраны правильно."
            reading.save()
        except:
            pass
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error in interpret_reading task: {str(e)}", exc_info=True)
        # Retry for unexpected errors
        if self.request.retries < self.max_retries:
            cache.set(f'reading_{reading_id}_status', f'error_retrying_{self.request.retries + 1}', 300)
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        else:
            try:
                reading = Reading.objects.get(id=reading_id)
                reading.interpretation = "Произошла неожиданная ошибка. Попробуйте создать новый расклад."
                reading.save()
            except:
                pass
            return False


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_telegram_reading(self, reading_id, chat_id):
    """
    Async task to send tarot cards and interpretation to Telegram.
    """
    start_time = time.time()
    token = _get_bot_token()
    if not token:
        logger.error("Telegram bot token not configured; aborting send.")
        return False

    try:
        reading = Reading.objects.get(id=reading_id)
        positions = list(
            CardPosition.objects.filter(reading=reading)
            .select_related('card')
            .order_by('position')
        )

        if not positions:
            logger.error(f"No card positions found for reading {reading_id}")
            _run_async(_send_plain_message(token, chat_id, "Ошибка: карты для расклада не найдены."))
            reading.interpretation = "Ошибка: карты для расклада не найдены."
            reading.save()
            MonitoringUtils.track_error("missing_positions", f"No positions for reading {reading_id}")
            return False

        card_payloads = []
        for position in positions:
            card_payloads.append({
                "position": position.position,
                "name": position.card.name,
                "image": position.card.image,
                "is_reversed": position.is_reversed,
                "meaning": position.card.meaning_reversed if position.is_reversed else position.card.meaning_upright,
            })

        _run_async(_send_cards_and_meanings(token, chat_id, reading_id, card_payloads))
        _run_async(_send_processing_notice(token, chat_id, reading_id))

        interpreter = TarotInterpreter()
        interpretation = interpreter.interpret_reading(reading, positions)

        reading.interpretation = interpretation
        reading.save()
        cache.set(f'reading_{reading_id}_status', 'completed', 300)

        duration = time.time() - start_time
        MonitoringUtils.track_interpretation_time(reading_id, duration)

        _run_async(_send_interpretation(token, chat_id, interpretation))
        logger.info(f"Successfully sent telegram interpretation for reading {reading_id}")
        return True

    except Reading.DoesNotExist:
        logger.error(f"Reading {reading_id} not found")
        _run_async(_send_plain_message(token, chat_id, "Расклад не найден. Попробуйте создать новый."))
        return False

    except GigaChatAuthException:
        fallback = (
            "🔮 Ваш расклад Таро\n\n"
            "💫 Текущая ситуация: период важных изменений. Энергии в движении.\n\n"
            "🌟 Совет: доверьтесь интуиции и будьте открыты новым возможностям.\n\n"
            "🎯 Прогноз: впереди позитивные перемены при сосредоточенности на целях.\n\n"
            "✨ Карты — инструмент самопознания. Используйте подсказки в жизни.\n\n"
            "AI-интерпретация временно недоступна. Скоро сервис восстановится."
        )
        try:
            reading = Reading.objects.get(id=reading_id)
            reading.interpretation = fallback
            reading.save()
        except Exception:
            pass
        _run_async(_send_interpretation(token, chat_id, fallback))
        return False

    except GigaChatTimeoutException as exc:
        logger.warning(f"GigaChat timeout for reading {reading_id}: {str(exc)}")
        if self.request.retries < self.max_retries:
            cache.set(f'reading_{reading_id}_status', f'retrying_{self.request.retries + 1}', 300)
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        try:
            reading = Reading.objects.get(id=reading_id)
            reading.interpretation = "Извините, AI-сервис временно недоступен. Попробуйте создать новый расклад."
            reading.save()
        except Exception:
            pass
        _run_async(_send_plain_message(token, chat_id, "AI-сервис временно недоступен. Попробуйте создать новый расклад."))
        return False

    except GigaChatAPIException as exc:
        logger.error(f"GigaChat API error for reading {reading_id}: {str(exc)}")
        try:
            reading = Reading.objects.get(id=reading_id)
            reading.interpretation = "Возникла техническая проблема с интерпретацией. Карты выбраны правильно."
            reading.save()
        except Exception:
            pass
        _run_async(_send_plain_message(token, chat_id, "Техническая проблема с интерпретацией. Карты выбраны правильно."))
        return False

    except Exception as exc:
        logger.error(f"Unexpected error in send_telegram_reading: {str(exc)}", exc_info=True)
        if self.request.retries < self.max_retries:
            cache.set(f'reading_{reading_id}_status', f'error_retrying_{self.request.retries + 1}', 300)
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        try:
            reading = Reading.objects.get(id=reading_id)
            reading.interpretation = "Произошла неожиданная ошибка. Попробуйте создать новый расклад."
            reading.save()
        except Exception:
            pass
        _run_async(_send_plain_message(token, chat_id, "Произошла ошибка. Попробуйте создать новый расклад."))
        return False

@shared_task
def cleanup_old_readings():
    """
    Periodic task to clean up old readings (older than 30 days)
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    old_readings = Reading.objects.filter(created_at__lt=cutoff_date)
    count = old_readings.count()
    
    if count > 0:
        # Delete associated card positions first
        CardPosition.objects.filter(reading__in=old_readings).delete()
        old_readings.delete()
        logger.info(f"Cleaned up {count} old readings")
    
    return count

@shared_task
def cache_card_data():
    """
    Task to cache frequently accessed card data
    """
    try:
        # Cache all cards
        cards = list(Card.objects.all().values('id', 'name', 'suit', 'meaning_upright', 'meaning_reversed'))
        cache.set('all_cards', cards, 3600)  # Cache for 1 hour
        
        # Cache cards by suit
        for suit_choice in Card.SUIT_CHOICES:
            suit_code = suit_choice[0]
            suit_cards = [card for card in cards if card['suit'] == suit_code]
            cache.set(f'cards_suit_{suit_code}', suit_cards, 3600)
        
        logger.info(f"Cached {len(cards)} cards")
        return len(cards)
        
    except Exception as e:
        logger.error(f"Error caching card data: {str(e)}", exc_info=True)
        return 0


def _get_bot_token():
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token or Bot is None:
        return None
    return token


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError as exc:
        logger.error("Telegram async call failed: %s", exc, exc_info=True)
        return None


async def _send_plain_message(token, chat_id, text):
    async with Bot(token=token) as bot:
        await _safe_send_message(bot, chat_id, text)


async def _send_cards_and_meanings(token, chat_id, reading_id, card_payloads):
    cache_key = f"telegram_reading_{reading_id}_cards_sent"
    if cache.get(cache_key):
        return

    async with Bot(token=token) as bot:
        media_payloads = []
        for card_data in card_payloads:
            image_path = get_card_image_path(card_data.get("image"))
            if not image_path:
                logger.warning("Card image not found: %s", card_data.get("image"))
                continue

            orientation = "перевёрнутая" if card_data.get("is_reversed") else "прямая"
            caption = f"{card_data.get('name', '')} ({orientation})"
            media_payloads.append({
                "image_path": image_path,
                "is_reversed": card_data.get("is_reversed"),
                "caption": caption,
                "position": card_data.get("position", 0),
            })

        sent_media = False
        spread_media, spread_handle = _build_spread_media(media_payloads)
        if spread_media:
            try:
                await bot.send_photo(chat_id=chat_id, photo=spread_media, caption="Ваш расклад Таро")
                sent_media = True
            except TelegramError as exc:
                logger.error("Telegram spread send error: %s", exc)
            finally:
                try:
                    spread_handle.close()
                except Exception:
                    pass

        if not sent_media:
            for payload in media_payloads:
                media, handle = _build_card_media(payload["image_path"], payload["is_reversed"])
                if not media:
                    continue
                try:
                    await bot.send_photo(chat_id=chat_id, photo=media, caption=payload["caption"])
                except TelegramError as exc:
                    logger.error("Telegram photo send error: %s", exc)
                finally:
                    if handle:
                        try:
                            handle.close()
                        except Exception:
                            pass

        summary = build_cards_summary(card_payloads)
        for chunk in split_message(summary):
            await _safe_send_message(bot, chat_id, chunk)

    cache.set(cache_key, True, 3600)


async def _send_processing_notice(token, chat_id, reading_id):
    cache_key = f"telegram_reading_{reading_id}_processing_sent"
    if cache.get(cache_key):
        return
    await _send_plain_message(token, chat_id, "AI-мастер карт анализирует расклад, подождите немного.")
    cache.set(cache_key, True, 3600)


async def _send_interpretation(token, chat_id, interpretation):
    if not interpretation:
        return
    async with Bot(token=token) as bot:
        for chunk in split_message(interpretation):
            await _safe_send_message(bot, chat_id, chunk)


async def _safe_send_message(bot, chat_id, text):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except TelegramError as exc:
        logger.error(f"Telegram send error: {exc}")


def _build_card_media(image_path, is_reversed):
    if InputFile is None:
        return None, None

    if is_reversed and Image is None:
        logger.warning("Pillow unavailable; sending upright image for reversed card %s", image_path)

    if is_reversed and Image is not None:
        try:
            with Image.open(image_path) as img:
                rotated = img.transpose(Image.ROTATE_180)
                buffer = io.BytesIO()
                image_format = img.format or "JPEG"
                rotated.save(buffer, format=image_format)
                buffer.seek(0)
                rotated.close()
            return InputFile(buffer, filename=f"rev_{image_path.name}"), buffer
        except Exception as exc:
            logger.warning("Failed to rotate card image %s: %s", image_path, exc)

    try:
        handle = open(image_path, "rb")
    except OSError as exc:
        logger.warning("Failed to open card image %s: %s", image_path, exc)
        return None, None
    return InputFile(handle, filename=image_path.name), handle


def _build_spread_media(media_payloads):
    if InputFile is None or Image is None:
        return None, None

    position_grid = {
        0: (1, 1),  # center
        1: (0, 1),  # top
        2: (1, 0),  # left
        3: (1, 2),  # right
        4: (2, 1),  # bottom
    }

    base_size = None
    placed_images = {}
    open_images = []
    resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS

    try:
        for payload in media_payloads:
            position = payload.get("position")
            if position not in position_grid:
                continue

            image_path = payload.get("image_path")
            if not image_path:
                continue

            img = Image.open(image_path)
            if img.mode != "RGB":
                converted = img.convert("RGB")
                img.close()
                img = converted

            if payload.get("is_reversed"):
                rotated = img.transpose(Image.ROTATE_180)
                img.close()
                img = rotated

            if base_size is None:
                base_size = img.size
            elif img.size != base_size:
                resized = img.resize(base_size, resample=resample)
                img.close()
                img = resized

            placed_images[position] = img
            open_images.append(img)

        if not placed_images or base_size is None:
            return None, None

        card_width, card_height = base_size
        gap = 20
        margin = 20
        canvas_width = (card_width * 3) + (gap * 2) + (margin * 2)
        canvas_height = (card_height * 3) + (gap * 2) + (margin * 2)
        canvas = Image.new("RGB", (canvas_width, canvas_height), (18, 18, 18))

        for position, img in placed_images.items():
            row, col = position_grid[position]
            x = margin + (col * (card_width + gap))
            y = margin + (row * (card_height + gap))
            canvas.paste(img, (x, y))

        buffer = io.BytesIO()
        canvas.save(buffer, format="JPEG", quality=85, optimize=True)
        buffer.seek(0)
        canvas.close()
        return InputFile(buffer, filename="tarot-spread.jpg"), buffer
    except Exception as exc:
        logger.warning("Failed to build tarot spread image: %s", exc)
        return None, None
    finally:
        for img in open_images:
            try:
                img.close()
            except Exception:
                pass
