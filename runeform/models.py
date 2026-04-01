from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class Rect(BaseModel):
    x: float
    y: float
    width: float
    height: float


class ElementType(str, Enum):
    HERO = "hero"
    HEADLINE = "headline"
    SUBHEAD = "subhead"
    BODY = "body"
    LOGO = "logo"


class ArchetypeTag(str, Enum):
    """Content type tags — the bridge between data shape and templates."""
    SINGLE_EVENT_HERO = "single_event_hero"
    SINGLE_EVENT_TEXT = "single_event_text"
    TEXT_ANNOUNCEMENT = "text_announcement"


class FontSizeRange(BaseModel):
    """Acceptable font size range for a text zone."""
    min_size: int = 12
    max_size: int = 72
    step: int = 2


class Zone(BaseModel):
    name: str
    bounds: Rect
    visual_weight: float = 1.0
    allowed_elements: list[ElementType]
    font_size_range: FontSizeRange | None = None  # None for image zones


class Template(BaseModel):
    """The core primitive. A specific spatial arrangement of zones."""
    name: str
    label: str
    archetype: ArchetypeTag
    zones: list[Zone]
    family: str = "default"


class ContentType(str, Enum):
    """Inferred from input data during data shape analysis."""
    SINGLE_EVENT_HERO = "single_event_hero"
    SINGLE_EVENT_TEXT = "single_event_text"
    TEXT_ANNOUNCEMENT = "text_announcement"


class ContentDensity(BaseModel):
    """Quantified density signals for typography solving."""
    title_length: Literal["short", "medium", "long"]
    has_subtitle: bool
    has_body: bool
    has_image: bool
    field_count: int


class DataShape(BaseModel):
    """Result of data shape analysis."""
    content_type: ContentType
    density: ContentDensity


class EventData(BaseModel):
    title: str
    date: str | None = None
    time: str | None = None
    location: str | None = None
    description: str | None = None
    category: str | None = None
    image_path: Path | None = None


class PhotoCandidate(BaseModel):
    asset_id: str
    score: float
    label: str
    path: Path | None = None


class ContentItem(BaseModel):
    element_type: ElementType
    text: str | None = None
    photo: PhotoCandidate | None = None
    color: tuple[int, int, int] = (100, 100, 100)


class SolvedTypography(BaseModel):
    """Z3-solved font sizes for text zones in a template."""
    font_sizes: dict[str, int]  # zone_name -> solved font size
    satisfiable: bool
    solve_time_ms: float = 0.0


class Placement(BaseModel):
    zone: Zone
    content: ContentItem
    solved_font_size: int | None = None


class ComposedLayout(BaseModel):
    template: Template
    placements: list[Placement]
    typography: SolvedTypography
    heuristic_score: float = 0.0


class BrandKit(BaseModel):
    """Brand identity for a venue."""
    name: str
    address: str = ""
    description: str = ""  # influences aesthetic choices
    colors: list[str] = []  # hex colors, e.g. ["#2D5A3D", "#F4A261"]
    logo_filename: str | None = None  # filename within the brand kit

    @property
    def primary_color(self) -> tuple[int, int, int] | None:
        """First color as RGB tuple."""
        if self.colors:
            return _hex_to_rgb(self.colors[0])
        return None

    @property
    def secondary_color(self) -> tuple[int, int, int] | None:
        """Second color as RGB tuple."""
        if len(self.colors) > 1:
            return _hex_to_rgb(self.colors[1])
        return None

    @property
    def accent_color(self) -> tuple[int, int, int] | None:
        """Third color as RGB tuple."""
        if len(self.colors) > 2:
            return _hex_to_rgb(self.colors[2])
        return None


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert '#RRGGBB' to (r, g, b)."""
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


class GenerationResult(BaseModel):
    layouts: list[ComposedLayout]
    rendered_paths: list[Path]
    best_index: int
    reasoning: str
    data_shape: DataShape
    templates_considered: int
    templates_after_filter: int
    templates_after_z3: int
