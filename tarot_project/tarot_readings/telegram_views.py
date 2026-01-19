import json
import logging

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .telegram_bot import handle_telegram_update


logger = logging.getLogger(__name__)


@csrf_exempt
def telegram_webhook(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")

    if not getattr(settings, "TELEGRAM_BOT_TOKEN", ""):
        return JsonResponse({"status": "disabled"}, status=503)

    secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
    if secret:
        provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if provided != secret:
            logger.warning("Telegram webhook secret mismatch.")
            return HttpResponseForbidden("Forbidden")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    try:
        handle_telegram_update(payload)
    except Exception as exc:
        logger.error("Failed to handle telegram update: %s", exc, exc_info=True)

    return JsonResponse({"status": "ok"})
