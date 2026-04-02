"""Font management — pairing, loading, and variable weight support via Skia."""

import struct
from pathlib import Path

import skia

FONTS_DIR = Path(__file__).parent.parent / "fonts"

WGHT_TAG = struct.unpack(">I", b"wght")[0]
OPSZ_TAG = struct.unpack(">I", b"opsz")[0]


class FontMetrics:
    """Pre-computed metrics for Z3 constraint solving."""

    def __init__(self, char_width_ratio: float, line_height_ratio: float):
        self.char_width_ratio = char_width_ratio
        self.line_height_ratio = line_height_ratio

    def __repr__(self) -> str:
        return f"FontMetrics(cwr={self.char_width_ratio:.3f}, lhr={self.line_height_ratio:.3f})"


# Representative sample for measuring average character width
_METRIC_SAMPLE = "The Quick Brown Fox Jumps Over A Lazy Dog SPRING WOODWORKING WORKSHOP"


class FontFamily:
    """A loaded font family with variable weight support."""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self._base_typeface = skia.Typeface.MakeFromFile(str(path))
        if self._base_typeface is None:
            raise ValueError(f"Failed to load font: {path}")
        self._cache: dict[int, skia.Typeface] = {}
        self._metrics_cache: dict[int, FontMetrics] = {}

    def typeface(self, weight: int = 400) -> skia.Typeface:
        """Get a typeface at a specific weight. Cached."""
        if weight in self._cache:
            return self._cache[weight]

        coord = skia.FontArguments.VariationPosition.Coordinate(WGHT_TAG, float(weight))
        coords = skia.FontArguments.VariationPosition.Coordinates([coord])
        pos = skia.FontArguments.VariationPosition(coords)
        args = skia.FontArguments()
        args.setVariationDesignPosition(pos)
        tf = self._base_typeface.makeClone(args)
        if tf is None:
            tf = self._base_typeface
        self._cache[weight] = tf
        return tf

    def font(self, size: float, weight: int = 400) -> skia.Font:
        """Get a Skia Font at a specific size and weight."""
        tf = self.typeface(weight)
        f = skia.Font(tf, size)
        f.setSubpixel(True)
        f.setEdging(skia.Font.Edging.kSubpixelAntiAlias)
        return f

    def metrics(self, weight: int = 400) -> FontMetrics:
        """Pre-computed metrics for Z3 solving. Cached per weight."""
        if weight in self._metrics_cache:
            return self._metrics_cache[weight]

        ref_size = 100.0
        font = self.font(ref_size, weight)

        # Char width ratio: average advance per character / font size
        width = font.measureText(_METRIC_SAMPLE)
        cwr = width / (len(_METRIC_SAMPLE) * ref_size)

        # Line height ratio: (ascent + descent + leading) / font size
        m = font.getMetrics()
        lhr = (-m.fAscent + m.fDescent + m.fLeading) / ref_size

        metrics = FontMetrics(cwr, lhr)
        self._metrics_cache[weight] = metrics
        return metrics


def measure_text_block(
    text: str, font: skia.Font, max_width: float,
) -> tuple[float, float]:
    """Measure the bounding box of word-wrapped text.

    Returns (width, height) of the text block when wrapped to max_width.
    Uses the same word-wrap logic as the renderer.
    """
    words = text.split()
    if not words:
        return (0.0, 0.0)

    # Word-wrap
    lines: list[str] = []
    current_line = words[0]
    for word in words[1:]:
        test = current_line + " " + word
        if font.measureText(test) <= max_width:
            current_line = test
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)

    # Measure each line width
    max_line_w = max(font.measureText(line) for line in lines)

    # Compute height using visual bounds for tight measurement
    metrics = font.getMetrics()
    line_height = -metrics.fAscent + metrics.fDescent + metrics.fLeading
    blobs = [skia.TextBlob.MakeFromShapedText(line, font) for line in lines]
    blobs = [b for b in blobs if b is not None]

    if not blobs:
        return (max_line_w, line_height * len(lines))

    first_top = blobs[0].bounds().fTop
    last_bottom = blobs[-1].bounds().fBottom
    total_height = -first_top + (len(blobs) - 1) * line_height + last_bottom

    return (max_line_w, total_height)


class FontPairing:
    """A headline + body font combination."""

    # Element type -> (font role, weight used in rendering)
    ELEMENT_CONFIG = {
        "headline": ("headline", 700),
        "subhead":  ("body", 500),
        "body":     ("body", 400),
        "logo":     ("headline", 600),
    }

    def __init__(self, name: str, headline: FontFamily, body: FontFamily):
        self.name = name
        self.headline = headline
        self.body = body

    def font_for(self, role: str, size: float, weight: int = 400) -> skia.Font:
        """Get the appropriate font for a role (headline or body)."""
        if role in ("headline", "logo"):
            return self.headline.font(size, weight)
        return self.body.font(size, weight)

    def metrics_for_element(self, element_type: str) -> FontMetrics:
        """Get Z3-ready metrics for an element type (headline, subhead, body, logo)."""
        role, weight = self.ELEMENT_CONFIG.get(element_type, ("body", 400))
        if role == "headline":
            return self.headline.metrics(weight)
        return self.body.metrics(weight)

    def text_fits_zone(
        self, text: str, element_type: str, font_size: int,
        zone_width: float, zone_height: float, padding: float = 20,
    ) -> bool:
        """Check if text at a given font size fits within zone bounds."""
        role, weight = self.ELEMENT_CONFIG.get(element_type, ("body", 400))
        font = self.font_for(role, font_size, weight)
        usable_w = zone_width - padding
        usable_h = zone_height - padding
        w, h = measure_text_block(text, font, usable_w)
        return w <= usable_w and h <= usable_h


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_families: dict[str, FontFamily] = {}
_pairings: dict[str, FontPairing] = {}


def _load_family(name: str, filename: str) -> FontFamily:
    path = FONTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Font file not found: {path}")
    family = FontFamily(name, path)
    _families[name] = family
    return family


def _init():
    if _families:
        return

    playfair = _load_family("Playfair Display", "PlayfairDisplay.ttf")
    dm_serif = _load_family("DM Serif Display", "DMSerifDisplay-Regular.ttf")
    space_grotesk = _load_family("Space Grotesk", "SpaceGrotesk.ttf")
    inter = _load_family("Inter", "Inter.ttf")
    dm_sans = _load_family("DM Sans", "DMSans.ttf")
    source_sans = _load_family("Source Sans 3", "SourceSans3.ttf")

    _pairings["editorial"] = FontPairing("Editorial", playfair, inter)
    _pairings["modern"] = FontPairing("Modern", space_grotesk, dm_sans)
    _pairings["warm"] = FontPairing("Warm", dm_serif, source_sans)
    _pairings["clean"] = FontPairing("Clean", inter, dm_sans)


def get_pairing(name: str = "warm") -> FontPairing:
    """Get a font pairing by name."""
    _init()
    return _pairings.get(name, _pairings["warm"])


def list_pairings() -> list[str]:
    """List available pairing names."""
    _init()
    return list(_pairings.keys())
