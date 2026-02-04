import logging

from .models import InteractionLog

logger = logging.getLogger(__name__)


def log_interaction(
    source,
    direction,
    event_type,
    user_identifier="",
    content="",
    reading=None,
    metadata=None,
):
    try:
        InteractionLog.objects.create(
            source=source,
            direction=direction,
            event_type=event_type,
            user_identifier=user_identifier or "",
            content=content or "",
            reading=reading,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.warning("Failed to log interaction: %s", exc, exc_info=True)
