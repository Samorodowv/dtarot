from pathlib import Path

from django.conf import settings


POSITION_NAMES = {
    0: "Текущая ситуация",
    1: "Препятствие",
    2: "Прошлое",
    3: "Будущее",
    4: "Возможный исход",
}

MAX_TELEGRAM_MESSAGE_LENGTH = 4000


def get_card_image_path(image_name):
    candidates = [
        Path(settings.BASE_DIR) / "tarot_cards" / image_name,
        Path(settings.BASE_DIR).parent / "tarot_cards" / image_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def build_cards_summary(positions):
    lines = []
    for position in positions:
        if isinstance(position, dict):
            position_index = position.get("position", 0)
            card_name = position.get("name", "")
            is_reversed = position.get("is_reversed", False)
            meaning = position.get("meaning", "")
        else:
            position_index = position.position
            card_name = position.card.name
            is_reversed = position.is_reversed
            meaning = position.card.meaning_reversed if position.is_reversed else position.card.meaning_upright

        position_name = POSITION_NAMES.get(position_index, f"Позиция {position_index + 1}")
        orientation = "перевёрнутая" if is_reversed else "прямая"
        lines.append(f"{position_name}: {card_name} ({orientation})\nЗначение: {meaning}")
    return "\n\n".join(lines)


def split_message(text, max_length=MAX_TELEGRAM_MESSAGE_LENGTH):
    if not text:
        return []
    if len(text) <= max_length:
        return [text]
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]
