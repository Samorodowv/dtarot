import logging

from .models import InteractionLog

logger = logging.getLogger(__name__)


def log_interaction(
    source,
    direction,
    event_type,
    interaction_id=None,
    user_identifier="",
    content="",
    reading=None,
    metadata=None,
):
    resolved_interaction_id = interaction_id or ""
    if not resolved_interaction_id and reading:
        resolved_interaction_id = f"reading:{reading.id}"
    if not resolved_interaction_id and metadata:
        reading_id = metadata.get("reading_id")
        if reading_id:
            resolved_interaction_id = f"reading:{reading_id}"
    if not resolved_interaction_id and user_identifier and user_identifier.startswith("reading:"):
        resolved_interaction_id = user_identifier

    try:
        InteractionLog.objects.create(
            source=source,
            direction=direction,
            event_type=event_type,
            interaction_id=resolved_interaction_id,
            user_identifier=user_identifier or "",
            content=content or "",
            reading=reading,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.warning("Failed to log interaction: %s", exc, exc_info=True)
