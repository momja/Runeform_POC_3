"""Template definitions — 7 templates across 3 archetype tags.

Each template defines named zones with pixel bounds on a 1080x1080 canvas.
Text zones include FontSizeRange for Z3 typography solving.
"""

from .models import ArchetypeTag, ElementType, FontSizeRange, Rect, Template, Zone

CANVAS_W = 1080
CANVAS_H = 1080
M = 60  # margin

# Font size ranges by hierarchy level
HEADLINE_FSR = FontSizeRange(min_size=90, max_size=160, step=2)
SUBHEAD_FSR = FontSizeRange(min_size=36, max_size=60, step=2)
BODY_FSR = FontSizeRange(min_size=27, max_size=33, step=2)
LOGO_FSR = FontSizeRange(min_size=27, max_size=33, step=2)

# ---------------------------------------------------------------------------
# single_event_hero — 3 templates (event with image)
# ---------------------------------------------------------------------------

HERO_LEFT_TEXT_RIGHT = Template(
    name="hero_left_text_right",
    label="Hero Left, Text Right",
    archetype=ArchetypeTag.SINGLE_EVENT_HERO,
    zones=[
        Zone(
            name="hero",
            bounds=Rect(x=M, y=M, width=460, height=960),
            visual_weight=1.0,
            allowed_elements=[ElementType.HERO],
        ),
        Zone(
            name="headline",
            bounds=Rect(x=560, y=M, width=460, height=440),
            visual_weight=0.9,
            allowed_elements=[ElementType.HEADLINE],
            font_size_range=HEADLINE_FSR,
        ),
        Zone(
            name="subhead",
            bounds=Rect(x=560, y=520, width=460, height=120),
            visual_weight=0.5,
            allowed_elements=[ElementType.SUBHEAD],
            font_size_range=SUBHEAD_FSR,
        ),
        Zone(
            name="body",
            bounds=Rect(x=560, y=660, width=460, height=200),
            visual_weight=0.4,
            allowed_elements=[ElementType.BODY],
            font_size_range=BODY_FSR,
        ),
        Zone(
            name="logo",
            bounds=Rect(x=560, y=880, width=140, height=140),
            visual_weight=0.3,
            allowed_elements=[ElementType.LOGO],
            font_size_range=LOGO_FSR,
        ),
    ],
)

HERO_FULL_OVERLAY = Template(
    name="hero_full_overlay",
    label="Full Hero with Text Overlay",
    archetype=ArchetypeTag.SINGLE_EVENT_HERO,
    zones=[
        Zone(
            name="hero",
            bounds=Rect(x=0, y=0, width=CANVAS_W, height=CANVAS_H),
            visual_weight=1.0,
            allowed_elements=[ElementType.HERO],
        ),
        Zone(
            name="headline",
            bounds=Rect(x=M, y=380, width=960, height=360),
            visual_weight=0.9,
            allowed_elements=[ElementType.HEADLINE],
            font_size_range=HEADLINE_FSR,
        ),
        Zone(
            name="subhead",
            bounds=Rect(x=M, y=760, width=700, height=120),
            visual_weight=0.5,
            allowed_elements=[ElementType.SUBHEAD],
            font_size_range=SUBHEAD_FSR,
        ),
        Zone(
            name="body",
            bounds=Rect(x=M, y=900, width=700, height=120),
            visual_weight=0.4,
            allowed_elements=[ElementType.BODY],
            font_size_range=BODY_FSR,
        ),
        Zone(
            name="logo",
            bounds=Rect(x=880, y=M, width=140, height=140),
            visual_weight=0.3,
            allowed_elements=[ElementType.LOGO],
            font_size_range=LOGO_FSR,
        ),
    ],
)

HERO_TOP_TEXT_BOTTOM = Template(
    name="hero_top_text_bottom",
    label="Hero Top, Text Bottom",
    archetype=ArchetypeTag.SINGLE_EVENT_HERO,
    zones=[
        Zone(
            name="hero",
            bounds=Rect(x=M, y=M, width=960, height=400),
            visual_weight=1.0,
            allowed_elements=[ElementType.HERO],
        ),
        Zone(
            name="headline",
            bounds=Rect(x=M, y=480, width=960, height=280),
            visual_weight=0.9,
            allowed_elements=[ElementType.HEADLINE],
            font_size_range=HEADLINE_FSR,
        ),
        Zone(
            name="subhead",
            bounds=Rect(x=M, y=780, width=700, height=100),
            visual_weight=0.5,
            allowed_elements=[ElementType.SUBHEAD],
            font_size_range=SUBHEAD_FSR,
        ),
        Zone(
            name="body",
            bounds=Rect(x=M, y=900, width=700, height=100),
            visual_weight=0.4,
            allowed_elements=[ElementType.BODY],
            font_size_range=BODY_FSR,
        ),
        Zone(
            name="logo",
            bounds=Rect(x=860, y=880, width=140, height=140),
            visual_weight=0.3,
            allowed_elements=[ElementType.LOGO],
            font_size_range=LOGO_FSR,
        ),
    ],
)

# ---------------------------------------------------------------------------
# single_event_text — 2 templates (event without image)
# ---------------------------------------------------------------------------

TEXT_CENTERED_STACK = Template(
    name="text_centered_stack",
    label="Centered Text Stack",
    archetype=ArchetypeTag.SINGLE_EVENT_TEXT,
    zones=[
        Zone(
            name="logo",
            bounds=Rect(x=440, y=M, width=200, height=120),
            visual_weight=0.3,
            allowed_elements=[ElementType.LOGO],
            font_size_range=LOGO_FSR,
        ),
        Zone(
            name="headline",
            bounds=Rect(x=M, y=200, width=960, height=400),
            visual_weight=0.9,
            allowed_elements=[ElementType.HEADLINE],
            font_size_range=HEADLINE_FSR,
        ),
        Zone(
            name="subhead",
            bounds=Rect(x=100, y=620, width=880, height=120),
            visual_weight=0.5,
            allowed_elements=[ElementType.SUBHEAD],
            font_size_range=SUBHEAD_FSR,
        ),
        Zone(
            name="body",
            bounds=Rect(x=100, y=760, width=880, height=220),
            visual_weight=0.4,
            allowed_elements=[ElementType.BODY],
            font_size_range=BODY_FSR,
        ),
    ],
)

TEXT_BOLD_TITLE = Template(
    name="text_bold_title",
    label="Bold Title Left, Details Right",
    archetype=ArchetypeTag.SINGLE_EVENT_TEXT,
    zones=[
        Zone(
            name="headline",
            bounds=Rect(x=M, y=M, width=620, height=560),
            visual_weight=0.9,
            allowed_elements=[ElementType.HEADLINE],
            font_size_range=HEADLINE_FSR,
        ),
        Zone(
            name="subhead",
            bounds=Rect(x=M, y=640, width=620, height=120),
            visual_weight=0.5,
            allowed_elements=[ElementType.SUBHEAD],
            font_size_range=SUBHEAD_FSR,
        ),
        Zone(
            name="body",
            bounds=Rect(x=720, y=M, width=300, height=600),
            visual_weight=0.4,
            allowed_elements=[ElementType.BODY],
            font_size_range=BODY_FSR,
        ),
        Zone(
            name="logo",
            bounds=Rect(x=720, y=860, width=160, height=140),
            visual_weight=0.3,
            allowed_elements=[ElementType.LOGO],
            font_size_range=LOGO_FSR,
        ),
    ],
)

# ---------------------------------------------------------------------------
# text_announcement — 2 templates (no event, no image)
# ---------------------------------------------------------------------------

ANNOUNCEMENT_CENTERED = Template(
    name="announcement_centered",
    label="Centered Announcement",
    archetype=ArchetypeTag.TEXT_ANNOUNCEMENT,
    zones=[
        Zone(
            name="headline",
            bounds=Rect(x=M, y=100, width=960, height=480),
            visual_weight=0.9,
            allowed_elements=[ElementType.HEADLINE],
            font_size_range=HEADLINE_FSR,
        ),
        Zone(
            name="body",
            bounds=Rect(x=100, y=620, width=880, height=260),
            visual_weight=0.5,
            allowed_elements=[ElementType.BODY],
            font_size_range=BODY_FSR,
        ),
        Zone(
            name="logo",
            bounds=Rect(x=440, y=910, width=200, height=120),
            visual_weight=0.3,
            allowed_elements=[ElementType.LOGO],
            font_size_range=LOGO_FSR,
        ),
    ],
)

ANNOUNCEMENT_SPLIT = Template(
    name="announcement_split",
    label="Split Announcement",
    archetype=ArchetypeTag.TEXT_ANNOUNCEMENT,
    zones=[
        Zone(
            name="headline",
            bounds=Rect(x=M, y=M, width=960, height=520),
            visual_weight=0.9,
            allowed_elements=[ElementType.HEADLINE],
            font_size_range=HEADLINE_FSR,
        ),
        Zone(
            name="body",
            bounds=Rect(x=M, y=600, width=700, height=320),
            visual_weight=0.5,
            allowed_elements=[ElementType.BODY],
            font_size_range=BODY_FSR,
        ),
        Zone(
            name="logo",
            bounds=Rect(x=800, y=820, width=200, height=160),
            visual_weight=0.3,
            allowed_elements=[ElementType.LOGO],
            font_size_range=LOGO_FSR,
        ),
    ],
)

# All templates
ALL_TEMPLATES: list[Template] = [
    HERO_LEFT_TEXT_RIGHT,
    HERO_FULL_OVERLAY,
    HERO_TOP_TEXT_BOTTOM,
    TEXT_CENTERED_STACK,
    TEXT_BOLD_TITLE,
    ANNOUNCEMENT_CENTERED,
    ANNOUNCEMENT_SPLIT,
]
