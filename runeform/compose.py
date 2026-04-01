"""Template filtering and content-to-zone assignment."""

from pathlib import Path

from .models import (
    ArchetypeTag,
    BrandKit,
    ComposedLayout,
    ContentItem,
    ContentType,
    DataShape,
    ElementType,
    PhotoCandidate,
    Placement,
    SolvedTypography,
    Template,
)

# Map content types to archetype tags for filtering
_TAG_MAP: dict[ContentType, ArchetypeTag] = {
    ContentType.SINGLE_EVENT_HERO: ArchetypeTag.SINGLE_EVENT_HERO,
    ContentType.SINGLE_EVENT_TEXT: ArchetypeTag.SINGLE_EVENT_TEXT,
    ContentType.TEXT_ANNOUNCEMENT: ArchetypeTag.TEXT_ANNOUNCEMENT,
}


def filter_templates(
    templates: list[Template],
    data_shape: DataShape,
) -> list[Template]:
    """Filter templates by archetype tag matching content type."""
    target_tag = _TAG_MAP[data_shape.content_type]
    return [t for t in templates if t.archetype == target_tag]


def build_content_items(
    title: str,
    subtitle: str | None = None,
    body: str | None = None,
    photo: PhotoCandidate | None = None,
    brand: BrandKit | None = None,
) -> list[ContentItem]:
    """Build content items from event data, using brand colors if available."""
    headline_color = brand.primary_color if brand and brand.primary_color else (210, 70, 70)
    subhead_color = brand.secondary_color if brand and brand.secondary_color else (180, 120, 50)
    logo_color = brand.primary_color if brand and brand.primary_color else (60, 110, 200)
    body_color = brand.secondary_color if brand and brand.secondary_color else (100, 100, 100)

    # Use brand logo if available
    logo_photo = None
    logo_text = brand.name if brand else "LOGO"
    if brand and brand.logo_filename:
        from .brand import BRAND_DIR
        logo_path = BRAND_DIR / brand.logo_filename
        if logo_path.exists():
            logo_photo = PhotoCandidate(
                asset_id="brand_logo",
                score=1.0,
                label="Brand Logo",
                path=logo_path,
            )

    items = [
        ContentItem(
            element_type=ElementType.HEADLINE,
            text=title.upper(),
            color=headline_color,
        ),
    ]

    if logo_photo:
        items.append(ContentItem(
            element_type=ElementType.LOGO,
            photo=logo_photo,
            color=logo_color,
        ))
    else:
        items.append(ContentItem(
            element_type=ElementType.LOGO,
            text=logo_text,
            color=logo_color,
        ))

    if subtitle:
        items.append(ContentItem(
            element_type=ElementType.SUBHEAD,
            text=subtitle,
            color=subhead_color,
        ))

    if body:
        items.append(ContentItem(
            element_type=ElementType.BODY,
            text=body,
            color=body_color,
        ))

    if photo:
        items.append(ContentItem(
            element_type=ElementType.HERO,
            photo=photo,
            color=(80, 160, 90),
        ))

    return items


def build_content_by_zone(
    template: Template,
    content_items: list[ContentItem],
) -> dict[str, ContentItem]:
    """Map content items to zone names by matching element types."""
    content_by_type: dict[ElementType, ContentItem] = {}
    for item in content_items:
        content_by_type[item.element_type] = item

    result: dict[str, ContentItem] = {}
    for zone in template.zones:
        for allowed in zone.allowed_elements:
            if allowed in content_by_type:
                result[zone.name] = content_by_type[allowed]
                break

    return result


def compose(
    template: Template,
    content_items: list[ContentItem],
    typography: SolvedTypography,
) -> ComposedLayout:
    """Place content items into template zones with solved font sizes."""
    content_by_zone = build_content_by_zone(template, content_items)

    placements = []
    for zone in template.zones:
        if zone.name in content_by_zone:
            placements.append(Placement(
                zone=zone,
                content=content_by_zone[zone.name],
                solved_font_size=typography.font_sizes.get(zone.name),
            ))

    return ComposedLayout(
        template=template,
        placements=placements,
        typography=typography,
    )
