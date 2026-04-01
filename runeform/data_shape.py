"""Data shape analysis — infer content type and density from event data.

Rule-based classifier (no LLM). Content type drives template filtering
via archetype tags. Content density informs typography solving.
"""

from .models import ContentDensity, ContentType, DataShape, EventData


def analyze_data_shape(event: EventData, has_image: bool) -> DataShape:
    """Infer content type and density from event data."""

    has_date_or_time = bool(event.date or event.time)

    if has_date_or_time and has_image:
        content_type = ContentType.SINGLE_EVENT_HERO
    elif has_date_or_time:
        content_type = ContentType.SINGLE_EVENT_TEXT
    else:
        content_type = ContentType.TEXT_ANNOUNCEMENT

    title_words = len(event.title.split())
    if title_words <= 3:
        title_length = "short"
    elif title_words <= 7:
        title_length = "medium"
    else:
        title_length = "long"

    has_subtitle = bool(event.date or event.time or event.location)
    has_body = bool(event.description)

    field_count = sum(1 for f in [
        event.title, event.date, event.time,
        event.location, event.description, event.category,
    ] if f)

    density = ContentDensity(
        title_length=title_length,
        has_subtitle=has_subtitle,
        has_body=has_body,
        has_image=has_image,
        field_count=field_count,
    )

    return DataShape(content_type=content_type, density=density)
