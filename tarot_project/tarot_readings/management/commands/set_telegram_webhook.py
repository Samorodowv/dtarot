import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

try:
    from telegram import Bot
    from telegram.error import TelegramError
except Exception:  # pragma: no cover - optional dependency at runtime
    Bot = None
    TelegramError = Exception


class Command(BaseCommand):
    help = "Configure Telegram webhook for the tarot bot"

    def add_arguments(self, parser):
        parser.add_argument("--url", help="Webhook URL to register")
        parser.add_argument("--secret", help="Webhook secret token")
        parser.add_argument(
            "--drop-pending",
            action="store_true",
            help="Drop pending updates when setting webhook",
        )

    def handle(self, *args, **options):
        if Bot is None:
            raise CommandError("python-telegram-bot is not installed.")

        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise CommandError("TELEGRAM_BOT_TOKEN is not configured.")

        url = options["url"] or getattr(settings, "TELEGRAM_WEBHOOK_URL", "")
        if not url:
            raise CommandError("Webhook URL is required. Use --url or TELEGRAM_WEBHOOK_URL.")

        secret = options["secret"] or getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or None
        drop_pending = options["drop_pending"]

        try:
            result = asyncio.run(
                _set_webhook(token, url, secret, drop_pending)
            )
        except TelegramError as exc:
            raise CommandError(f"Telegram API error: {exc}")

        if not result:
            raise CommandError("Telegram webhook setup failed.")

        self.stdout.write(self.style.SUCCESS(f"Webhook set to {url}"))


async def _set_webhook(token, url, secret, drop_pending):
    async with Bot(token=token) as bot:
        return await bot.set_webhook(
            url=url,
            secret_token=secret,
            drop_pending_updates=drop_pending,
        )
