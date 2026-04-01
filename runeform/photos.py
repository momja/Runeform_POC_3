"""Mocked photo library — stands in for Immich + CLIP retrieval.

Generates colored placeholder PNGs and returns them as candidates.
"""

from pathlib import Path

from PIL import Image, ImageDraw

from .models import PhotoCandidate

SAMPLE_DIR = Path(__file__).parent.parent / "sample_photos"


def _ensure_sample_photos() -> list[Path]:
    """Generate placeholder photos if they don't exist."""
    SAMPLE_DIR.mkdir(exist_ok=True)

    samples = [
        ("workshop_woodworking", (62, 100, 58), "Woodworking\nWorkshop"),
        ("maker_electronics", (45, 72, 110), "Electronics\nLab"),
        ("studio_yoga", (130, 90, 60), "Yoga\nStudio"),
        ("community_event", (100, 55, 90), "Community\nGathering"),
        ("outdoor_nature", (50, 110, 70), "Outdoor\nSession"),
        ("art_painting", (120, 75, 45), "Art\nClass"),
    ]

    paths = []
    for name, color, label in samples:
        path = SAMPLE_DIR / f"{name}.png"
        if not path.exists():
            img = Image.new("RGB", (800, 800), color)
            draw = ImageDraw.Draw(img)
            for i in range(5):
                inset = 40 + i * 60
                lighter = tuple(min(255, c + 15 * (i + 1)) for c in color)
                draw.rectangle(
                    [inset, inset, 800 - inset, 800 - inset],
                    outline=lighter, width=3,
                )
            draw.multiline_text(
                (400, 400), label,
                fill=(255, 255, 255, 200), anchor="mm", align="center",
            )
            draw.text((20, 20), f"[mock] {name}", fill=(255, 255, 255, 128))
            img.save(path)
        paths.append(path)
    return paths


def retrieve_photos(event_description: str, top_k: int = 3) -> list[PhotoCandidate]:
    """Mock CLIP retrieval — returns placeholder photo candidates."""
    paths = _ensure_sample_photos()

    keywords = set(event_description.lower().split())
    candidates = []
    for path in paths:
        stem_words = set(path.stem.lower().split("_"))
        overlap = len(keywords & stem_words)
        score = 0.5 + overlap * 0.15
        candidates.append(PhotoCandidate(
            asset_id=path.stem,
            score=min(score, 1.0),
            label=path.stem.replace("_", " ").title(),
            path=path,
        ))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_k]
