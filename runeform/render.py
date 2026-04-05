"""Render composed layouts to PNG images using Skia (HarfBuzz text shaping).

Uses Z3-solved font sizes directly — no bisection loop needed.
Font pairings provide distinct headline + body typefaces.
"""

from io import BytesIO
from pathlib import Path

import skia
from PIL import Image

from .fonts import FontPairing, get_pairing
from .models import BrandKit, ComposedLayout, ElementType
from .templates import CANVAS_H, CANVAS_W

DEFAULT_BACKGROUND = (248, 244, 238, 255)
GRID_COLOR = (235, 231, 225, 255)

# Element type -> (font role, weight)
_ELEMENT_FONT_CONFIG = {
    ElementType.HEADLINE: ("headline", 700),
    ElementType.SUBHEAD:  ("body", 500),
    ElementType.BODY:     ("body", 400),
    ElementType.LOGO:     ("headline", 600),
    ElementType.HERO:     ("body", 700),
}


def _rgba(color: tuple, alpha: int = 255) -> skia.Color4f:
    """Convert (r,g,b) or (r,g,b,a) tuple to skia Color4f."""
    r, g, b = color[0], color[1], color[2]
    a = color[3] if len(color) > 3 else alpha
    return skia.Color4f(r / 255, g / 255, b / 255, a / 255)


def _wrap_text(text: str, font: skia.Font, max_width: float) -> list[str]:
    """Word-wrap text so each line fits within max_width pixels."""
    words = text.split()
    if not words:
        return [text]
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
    return lines


def _draw_text_in_zone(
    canvas: skia.Canvas,
    text: str,
    bounds: tuple[float, float, float, float],
    font_size: int,
    color: tuple = (255, 255, 255),
    pairing: FontPairing | None = None,
    element_type: ElementType = ElementType.BODY,
):
    """Draw HarfBuzz-shaped text centered in a zone, word-wrapped."""
    x1, y1, x2, y2 = bounds
    max_w = x2 - x1 - 20

    role, weight = _ELEMENT_FONT_CONFIG.get(element_type, ("body", 400))
    if pairing:
        font = pairing.font_for(role, font_size, weight)
    else:
        font = get_pairing().font_for(role, font_size, weight)

    lines = _wrap_text(text, font, max_w)
    metrics = font.getMetrics()
    line_height = -metrics.fAscent + metrics.fDescent + metrics.fLeading

    # Build blobs and compute visual bounding box for the whole text block
    blobs: list[tuple[skia.TextBlob, float]] = []  # (blob, line_w)
    for line in lines:
        blob = skia.TextBlob.MakeFromShapedText(line, font)
        if blob is not None:
            blobs.append((blob, font.measureText(line)))

    if not blobs:
        return

    # Visual top/bottom: use bounds of first and last blob for tight centering
    first_top = blobs[0][0].bounds().fTop
    last_bottom = blobs[-1][0].bounds().fBottom
    visual_height = -first_top + (len(blobs) - 1) * line_height + last_bottom

    # Place first baseline so the visual block is centered in the zone
    zone_h = y2 - y1
    first_baseline = y1 + (zone_h - visual_height) / 2 - first_top

    paint = skia.Paint()
    paint.setAntiAlias(True)
    paint.setColor4f(_rgba(color))

    for i, (blob, line_w) in enumerate(blobs):
        lx = x1 + (x2 - x1 - line_w) / 2
        ly = first_baseline + i * line_height
        canvas.drawTextBlob(blob, lx, ly, paint)


def _open_image(path: Path) -> Image.Image:
    """Open an image file, converting SVG to PNG in memory via Skia."""
    if path.suffix.lower() == ".svg":
        svg_data = path.read_bytes()
        stream = skia.MemoryStream(svg_data)
        dom = skia.SVGDOM.MakeFromStream(stream)
        if dom is None:
            raise ValueError(f"Failed to parse SVG: {path}")
        container_size = dom.containerSize()
        w = int(container_size.width()) or 1080
        h = int(container_size.height()) or 1080
        surface = skia.Surface(w, h)
        canvas = surface.getCanvas()
        canvas.clear(skia.ColorTRANSPARENT)
        dom.render(canvas)
        sk_image = surface.makeImageSnapshot()
        png_bytes = sk_image.encodeToData(skia.kPNG)
        return Image.open(BytesIO(bytes(png_bytes)))
    return Image.open(path)


def _pil_to_skia(img: Image.Image) -> skia.Image:
    """Convert a PIL Image to a Skia Image."""
    rgba = img.convert("RGBA")
    return skia.Image.frombytes(
        rgba.tobytes(), (rgba.width, rgba.height), skia.kRGBA_8888_ColorType,
    )


def _paste_image(
    canvas: skia.Canvas,
    img: Image.Image,
    x: int, y: int, w: int, h: int,
    fit: str = "fill",
):
    """Draw a PIL image into a rectangle on the Skia canvas.

    fit="fill": scale-to-fill + center-crop (for hero images)
    fit="contain": fit inside preserving aspect ratio (for logos)
    """
    if fit == "fill":
        scale = max(w / img.width, h / img.height)
        scaled_w = int(img.width * scale)
        scaled_h = int(img.height * scale)
        img = img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        crop_x = (scaled_w - w) // 2
        crop_y = (scaled_h - h) // 2
        img = img.crop((crop_x, crop_y, crop_x + w, crop_y + h))
        sk_img = _pil_to_skia(img)
        canvas.drawImage(sk_img, x, y)
    else:  # contain
        img.thumbnail((w, h), Image.Resampling.LANCZOS)
        px = x + (w - img.width) // 2
        py = y + (h - img.height) // 2
        sk_img = _pil_to_skia(img)
        canvas.drawImage(sk_img, px, py)


def render_layout(
    layout: ComposedLayout,
    index: int,
    output_dir: Path,
    brand: BrandKit | None = None,
    pairing: FontPairing | None = None,
) -> Path:
    bg = brand.accent_color if brand and brand.accent_color else DEFAULT_BACKGROUND[:3]
    if pairing is None:
        pairing = get_pairing()

    surface = skia.Surface(CANVAS_W, CANVAS_H)
    canvas = surface.getCanvas()
    canvas.clear(skia.Color(*bg))

    # Subtle grid
    grid_paint = skia.Paint()
    grid_paint.setColor4f(_rgba(GRID_COLOR))
    grid_paint.setStrokeWidth(1)
    for x in range(0, CANVAS_W, 108):
        canvas.drawLine(x, 0, x, CANVAS_H, grid_paint)
    for y in range(0, CANVAS_H, 108):
        canvas.drawLine(0, y, CANVAS_W, y, grid_paint)

    for placement in layout.placements:
        b = placement.zone.bounds
        x1, y1 = int(b.x), int(b.y)
        x2, y2 = int(b.x + b.width), int(b.y + b.height)
        zone_w, zone_h = x2 - x1, y2 - y1

        has_photo = (
            placement.content.photo
            and placement.content.photo.path
            and placement.content.photo.path.exists()
        )

        if has_photo and placement.content.element_type == ElementType.HERO:
            photo = _open_image(placement.content.photo.path)
            _paste_image(canvas, photo, x1, y1, zone_w, zone_h, fit="fill")

        elif has_photo and placement.content.element_type == ElementType.LOGO:
            photo = _open_image(placement.content.photo.path)
            _paste_image(canvas, photo, x1, y1, zone_w, zone_h, fit="contain")

        elif placement.content.element_type == ElementType.HERO:
            rect_paint = skia.Paint()
            rect_paint.setColor4f(_rgba(placement.content.color))
            canvas.drawRect(skia.Rect.MakeXYWH(x1, y1, zone_w, zone_h), rect_paint)
            _draw_text_in_zone(
                canvas, "HERO IMAGE", (x1, y1, x2, y2), 24,
                color=(255, 255, 255), pairing=pairing,
                element_type=ElementType.HERO,
            )

        elif placement.content.element_type == ElementType.HEADLINE:
            rect_paint = skia.Paint()
            rect_paint.setColor4f(_rgba(placement.content.color))
            canvas.drawRect(skia.Rect.MakeXYWH(x1, y1, zone_w, zone_h), rect_paint)
            text = placement.content.text or "HEADLINE"
            font_size = placement.solved_font_size or 40
            _draw_text_in_zone(
                canvas, text, (x1, y1, x2, y2), font_size,
                color=(255, 255, 255), pairing=pairing,
                element_type=ElementType.HEADLINE,
            )

        elif placement.content.element_type == ElementType.SUBHEAD:
            rect_paint = skia.Paint()
            rect_paint.setColor4f(_rgba(placement.content.color))
            canvas.drawRect(skia.Rect.MakeXYWH(x1, y1, zone_w, zone_h), rect_paint)
            text = placement.content.text or "SUBHEAD"
            font_size = placement.solved_font_size or 24
            _draw_text_in_zone(
                canvas, text, (x1, y1, x2, y2), font_size,
                color=(255, 255, 255), pairing=pairing,
                element_type=ElementType.SUBHEAD,
            )

        elif placement.content.element_type == ElementType.BODY:
            rect_paint = skia.Paint()
            rect_paint.setColor4f(_rgba((240, 236, 230)))
            canvas.drawRect(skia.Rect.MakeXYWH(x1, y1, zone_w, zone_h), rect_paint)
            text = placement.content.text or "Event details here"
            font_size = placement.solved_font_size or 16
            _draw_text_in_zone(
                canvas, text, (x1, y1, x2, y2), font_size,
                color=(60, 60, 60), pairing=pairing,
                element_type=ElementType.BODY,
            )

        elif placement.content.element_type == ElementType.LOGO:
            rect_paint = skia.Paint()
            rect_paint.setColor4f(_rgba(placement.content.color))
            canvas.drawRect(skia.Rect.MakeXYWH(x1, y1, zone_w, zone_h), rect_paint)
            text = placement.content.text or "LOGO"
            font_size = placement.solved_font_size or 18
            _draw_text_in_zone(
                canvas, text, (x1, y1, x2, y2), font_size,
                color=(255, 255, 255), pairing=pairing,
                element_type=ElementType.LOGO,
            )

    # Label with template name, typography, and score
    typo_str = " ".join(f"{k}={v}" for k, v in layout.typography.font_sizes.items())
    label = f"#{index} {layout.template.label} | {typo_str} | score: {layout.heuristic_score:.2f}"
    label_font = pairing.body.font(12, 400)
    label_paint = skia.Paint()
    label_paint.setColor4f(_rgba((120, 120, 120)))
    label_paint.setAntiAlias(True)
    blob = skia.TextBlob.MakeFromShapedText(label, label_font)
    if blob:
        canvas.drawTextBlob(blob, 12, 20, label_paint)

    # Save as PNG
    image = surface.makeImageSnapshot()
    path = output_dir / f"layout_{index:02d}.png"
    image.save(str(path), skia.kPNG)
    return path


def render_all(
    layouts: list[ComposedLayout],
    output_dir: Path,
    brand: BrandKit | None = None,
    pairing: FontPairing | None = None,
) -> list[Path]:
    output_dir.mkdir(exist_ok=True)
    paths = []
    for i, layout in enumerate(layouts, 1):
        path = render_layout(layout, i, output_dir, brand=brand, pairing=pairing)
        paths.append(path)
    return paths
